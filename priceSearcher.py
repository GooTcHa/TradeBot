import json
import time
import asyncio
from aiohttp import ClientSession

import config
import csgotm
from steam import SteamBot

app_storage = {}
bot = SteamBot(config.gotchaLog)


async def get_items_to_buy_in_steam(client: SteamBot):
    print('get_items_to_buy_in_steam')
    while True:
        with open('items_to_buy.json', 'r') as f:
            items = json.load(f)
        if items['date'] < int(time.time()) - 87_000:
            await csgotm.get_items_to_buy(client)
        break
            # await asyncio.sleep(86_400)
        # else:
        #     await asyncio.sleep(3_600)


async def get_steam_cases_price(client: SteamBot) -> None:
    print('get_steam_cases_price')
    while True:
        with open('steam_cases_ratio.json', 'r') as f:
            items = json.load(f)
        if items['date'] < int(time.time()) - 21_500:
            await client.get_max_steam_cases_price()
        break
            # await asyncio.sleep(21_600)
        # else:
        #     await asyncio.sleep(3_600)


async def main():
    app_storage['session'] = ClientSession()
    csgotm.app_storage['session'] = app_storage['session']
    while True:
        await get_items_to_buy_in_steam(bot)
        await get_steam_cases_price(bot)
        await asyncio.sleep(82_000)


if __name__ == '__main__':
    asyncio.run(main())
