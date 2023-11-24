import json
import time
import asyncio
from aiohttp import ClientSession
from sys import argv

import config
import csgotm
from steam import SteamBot

app_storage = {}
login = argv[1]
client = SteamBot(config.logInfoList[login])


async def get_items_to_buy_in_steam():
    print('get_items_to_buy_in_steam')
    while True:
        with open('items_to_buy.json', 'r') as f:
            items = json.load(f)
        if items['date'] < int(time.time()) - 43_500:
            await csgotm.get_items_to_buy(client)
            await asyncio.sleep(44_000)
        else:
            await asyncio.sleep(3_600)


async def get_steam_cases_price() -> None:
    print('get_steam_cases_price')
    while True:
        with open('steam_cases_ratio.json', 'r') as f:
            items = json.load(f)
        if items['date'] < int(time.time()) - 43_500:
            print('start')
            t = time.time()
            await client.get_max_steam_cases_price()
            print(f'finish {time.time() - t}')
        # break
            await asyncio.sleep(44_000)
        else:
            await asyncio.sleep(3_600)


async def main():
    app_storage['session'] = ClientSession()
    csgotm.app_storage['session'] = app_storage['session']
    tasks = [
        asyncio.create_task(get_items_to_buy_in_steam()),
        asyncio.create_task(get_steam_cases_price())
    ]
    await asyncio.gather(*tasks)


if __name__ == '__main__':
    asyncio.run(main())
