import asyncio
import aiohttp
import time

from wiki_parser import *
from loguru import logger as Logger
from aiolimiter import AsyncLimiter


class WikiGame:
    def play(self, startPageName: str, endPageName: str) -> list[str]:
        raise NotImplementedError


class WikiGameDumb(WikiGame):
    class Node:
        def __init__(self, pageName: str, depth: int, pred=None):
            self.pred = pred
            self.pageName = pageName
            self.depth = depth

    def __init__(self):
        self.wikiParser = WikiParserDumb()

    def play(self, startPageName: str, endPageName: str, maxDepth: int = None) -> list[str]:
        Logger.info(
            f"Started playing\n\t" +
            f"Start page: '{startPageName}'\n\t" +
            f"End page: '{endPageName}'\n\t" +
            f"Max depth: {maxDepth}"
        )
        # Implementation is BFS

        startNode = self.Node(startPageName, 0)
        visitedPages = set(startPageName)
        nodesQueue = [startNode]

        while len(nodesQueue) != 0:
            curNode = nodesQueue.pop(0)
            Logger.debug(
                f"\n\tParsing '{curNode.pageName}'\n\t" +
                f"Depth: {curNode.depth}\n\t" +
                f"Queue size: {len(nodesQueue)}"
            )
            Logger.debug(f"Pred: {curNode.pred.pageName if curNode.pred is not None else curNode.pred}")
            links = self.wikiParser.getLinks(curNode.pageName)
            for link in links:
                if link == endPageName:
                    Logger.success("Path found!")
                    linkNode = self.Node(link, curNode.depth + 1, curNode)
                    return self._getPath(linkNode)

                if (link not in visitedPages) and (maxDepth is None or curNode.depth + 1 < maxDepth):
                    visitedPages.add(link)
                    linkNode = self.Node(link, curNode.depth + 1, curNode)
                    nodesQueue.append(linkNode)

        Logger.error("Path not found, depth limit reached :(")
        return []

    def _getPath(self, node: Node) -> list[str]:
        path = []

        curNode = node
        while curNode.pred is not None:
            path.append(curNode.pageName)
            curNode = curNode.pred

        path.append(curNode.pageName)
        path.reverse()

        Logger.success("Path is:\n\t" + " -> ".join([f"'{p}'" for p in path]))

        return path


class WikiGameAsync(WikiGame):
    URL = 'https://en.wikipedia.org/w/api.php'
    REQ_N = 50

    class Node:
        def __init__(self, pageName: str, depth: int, pred=None):
            self.pred = pred
            self.pageName = pageName
            self.depth = depth

    def __init__(self):
        self.ioloop = asyncio.get_event_loop()
        self.visitedPages = set()

    async def _makeRequest(self, page: str, predNode: Node):
        params = {
            'action': 'query',
            'titles': page,
            'format': 'json',
            'prop': 'links',
            'pllimit': 'max'
        }
        nd = self.Node(
            page,
            0 if predNode is None else predNode.depth + 1,
            predNode
        )
        Logger.debug(f"Making request for page '{page}', depth = {nd.depth}")
        async with self.limiter:
            return (await self.session.get(self.URL, params=params), nd)

    @staticmethod
    async def _getTasksLinks(responses):
        texts = []
        for (resp, node) in responses:
            try:
                rj = await resp.json()
                texts.append((rj, node))
            except:
                print(await resp.text())
                raise
        # [(await resp.json(), node) for (resp, node) in responses]

        text_list = []
        for (json, node) in texts:
            try:
                recTitles = list(json['query']['pages'].values())[0]['links']
                text_list.append((recTitles, node))
            except KeyError:
                # This is needed for links that have no existing page
                continue

        links = [
            (rec['title'], node)
            for (recTitles, node) in text_list
            for rec in recTitles
            if ':' not in rec['title']
        ]

        return links

    async def _play(self, startPage: str) -> Node:
        self.limiter = AsyncLimiter(150, 1)
        finalNode = None

        self.visitedPages.add(startPage)
        tasks = [
            asyncio.create_task(
                self._makeRequest(startPage, None)
            )
        ]

        startTime = time.time()
        parsedLen = 0

        linksQueue = []

        while True:
            done, pending = await asyncio.wait(
                tasks,
                return_when=asyncio.FIRST_COMPLETED
            )

            newLinks = await self._getTasksLinks(
                [task.result() for task in done]
            )
            linksQueue.extend(newLinks)

            # newLinks = linksQueue[:self.REQ_N]
            # linksQueue = linksQueue[self.REQ_N:]

            parsedLen += len(done)

            rps = round(parsedLen / (time.time() - startTime), 2)
            Logger.info(f'RPS: {rps}')

            # await asyncio.sleep(1)
            newTasks = []
            for (page, node) in newLinks:
                # Logger.debug(f"Got new page '{page}'")
                if page == self.endPageName:
                    finalNode = self.Node(page, node.depth + 1, node)
                    return finalNode

                if page not in self.visitedPages and node.depth < self.maxDepth:
                    self.visitedPages.add(page)
                    newTasks.append(
                        asyncio.create_task(
                            self._makeRequest(page, node)
                        )
                    )

            pending = list(pending)
            pending.extend(newTasks)

            if len(pending) == 0:
                break

            tasks = pending

        return finalNode

    def play(self, startPageName: str, endPageName: str, maxDepth: int = None) -> list[str]:
        self.session = aiohttp.ClientSession()

        Logger.info(
            f"Started playing\n\t" +
            f"Start page: '{startPageName}'\n\t" +
            f"End page: '{endPageName}'\n\t" +
            f"Max depth: {maxDepth}"
        )

        self.maxDepth = maxDepth
        self.endPageName = endPageName

        start_timestamp = time.time()

        nd = self.ioloop.run_until_complete(self._play(startPageName))

        task_time = round(time.time() - start_timestamp, 2)
        rps = round(len(self.visitedPages) / task_time, 1)
        Logger.info(f"RPS: {rps}")
        Logger.info(f"Parsed pages: {len(self.visitedPages)}")

        self.ioloop.stop()

        if nd is None:
            Logger.error("Path not found, depth limit reached :(")
            return []

        Logger.success("Path found!")
        return self._getPath(nd)

    def _getPath(self, node: Node) -> list[str]:
        path = []

        curNode = node
        while curNode.pred is not None:
            path.append(curNode.pageName)
            curNode = curNode.pred

        path.append(curNode.pageName)
        path.reverse()

        Logger.success("Path is:\n\t" + " -> ".join([f"'{p}'" for p in path]))

        return path
