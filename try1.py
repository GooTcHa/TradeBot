import asyncio
import datetime
import json
import time
from operator import itemgetter
from sys import argv
import requests
#
# u='https://steamcommunity.com/market/itemordershistogram?country=BY&language=russian&currency=1&item_nameid=480085569&two_factor=0'
# url = 'https://steamcommunity.com/market/itemordershistogram?country=BY&language=russian&currency=1&item_nameid=R8 Revolver | Fade (Field-Tested)&two_factor=0'
# with requests.get(u) as result:
#     print(result.text)
import db

month = {
    'Jan': 1,
    'Feb': 2,
    'Mar': 3,
    'Apr': 4,
    'May': 5,
    'Jun': 6,
    'Jul': 7,
    'Aug': 8,
    'Sep': 9,
    'Oct': 10,
    'Dec': 12
}
d = {'1': ['asd', 4],
     '2': ['fgh', 5],
     '3': ['jkl', 3]
}

a = [{'a': 3}, {'a': 2}]
b = [3, 1]
#
# a.sort(key=itemgetter('a'))
# print(a)

# i = 0
# for i in range(i, 15):
#     i -= 1
#     print(i)


async def a1():
    while True:
        print(1)
        await asyncio.sleep(0.1)


async def a2():
    while True:
        print(2)
        time.sleep(1)
            # await asyncio.sleep(0.1)


async def main():
    tasks = [
        asyncio.create_task(a1()),
        asyncio.create_task(a2())
    ]
    await asyncio.gather(*tasks)

# asyncio.run(main())
#
# s = ','
# s = s.replace(',', '.')
# print(s)
name = argv[1]
print(name)