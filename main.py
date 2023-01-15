#!/bin/python3.11


import sys


from wiki_game import *
from argparse import ArgumentParser
from loguru import logger as Logger


def filterNoDebug(record):
    return record['level'].name != 'DEBUG'


if __name__ == '__main__':
    argumentParser = ArgumentParser(
        prog = 'WikiGame',
        description = 'Let\'s play WikiGame!'
    )

    argumentParser.add_argument('-s', '--start', help='Start page name')
    argumentParser.add_argument('-e', '--end', help='End page name')
    argumentParser.add_argument('-dep', '--depth', help='Search depth', type=int)
    argumentParser.add_argument('--gametype', choices=['dumb', 'async'], default='dumb')
    argumentParser.add_argument('--debug', help='Enable debug info', action='store_true')

    args = argumentParser.parse_args()

    if not args.debug:
        Logger.remove(0)
        Logger.add(sys.stderr, level='INFO')


    wikiGame = None
    if args.gametype == 'dumb':
        wikiGame = WikiGameDumb()
    elif args.gametype == 'async':
        wikiGame = WikiGameAsync()
    
    path = wikiGame.play(args.start, args.end, args.depth)

    print(path)
