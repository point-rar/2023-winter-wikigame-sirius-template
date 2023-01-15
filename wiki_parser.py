import requests

from bs4 import BeautifulSoup
from loguru import logger as Logger


class WikiParser:
    URL = 'https://en.wikipedia.org/w/api.php'
    
    def getLinks(self, pageName: str) -> set[str]:
        raise NotImplementedError


class WikiParserDumb(WikiParser):
    def __init__(self):
        self.session = requests.Session()


    def _getPage(self, pageName: str) -> str:
        params = {
            'action': 'parse',
            'page': pageName,
            'format': 'json'
        }
        req = self.session.get(url=self.URL, params=params)
        data = req.json()

        return data['parse']['text']['*']


    def getLinks(self, pageName: str) -> set[str]:
        # Logger.info(f"Parsing links from '{pageName}'")
        page = self._getPage(pageName)
        soup = BeautifulSoup(page, 'html.parser')
        links = soup.find_all('a', href=lambda x: x and x.startswith('/wiki/'), class_=False)
        titles = set()
        
        for link in links:
            title = link.attrs['title']
            # Beginnings to avoid
            # Help: Wikipedia: Special: Category: Template: User talk:
            if ':' not in title:
                titles.add(title)

        return titles

