import datetime
import time
import asyncio
from aiohttp import ClientSession
import logging

import config
import csgotm
from steam import SteamBot

app_storage = {}
gotchaSC = SteamBot(config.logInfoList['zybinsteam2'])
logging.basicConfig(level=logging.INFO, filename="logs/bot.log", filemode="w",
                    format="%(asctime)s %(levelname)s %(message)s")


#Checking in/outcoming trades
#Approximate time 3s.
async def check_trades(client: SteamBot):
    print('check_trades')
    logging.info(f'Check trades of {client.login} lunched')
    while True:
        trades = await csgotm.get_trades(client)
        if trades['success']:
            await client.accept_trades(trades['trades'])
            client.steam_client.commit_confirmation_list()
        await asyncio.sleep(30)


#Getting steam balance and creating buy orders if balance > 20$
#Approximately 110s
async def check_steam_balance(client: SteamBot):
    print('check_steam_balance')
    while True:
        listings = (await client.get_steam_listings())['buy_orders']
        await client.delete_buy_orders(listings.keys())
        balance = await client.get_balance()
        if balance > 20:
            await client.create_buy_orders(balance * 1000)
        await asyncio.sleep(43200)

#Check tm balance and create cases buy order on tm
#~170s.
async def check_tm_balance(client) -> None:
    print('check_tm_balance')
    while True:
        balance = await csgotm.get_balance(client)
        if balance >= 5:
            await csgotm.buy_cases(client)
        await asyncio.sleep(3_600)


#Find cases and sell them
#Approximately 10s
async def check_cases_in_steam_inventory(client):
    print('check_cases_in_steam_inventory')
    while True:
        await client.sell_cases_from_inventory()
        await asyncio.sleep(3_600)


#Create sell orders on tm
#~
async def check_items_to_sell_on_tm(client: SteamBot):
    print('check_items_to_sell_on_tm')
    while True:
        t = time.time()
        await csgotm.create_new_listings_on_tm(client)
        print(time.time() - t)
        await asyncio.sleep(86_400)


async def check_steam_listings(client: SteamBot):
    print('check_steam_listings')
    cmp_date: datetime.date
    while True:
        listings = (await client.get_steam_listings())['sell_listings']
        if len(listings.keys()):
            await client.change_case_listings(listings=listings)
        await asyncio.sleep(86_400)


async def check_tm_listings(client: SteamBot):
    while True:
        # await csgotm.get_history(client)
        await csgotm.check_listings(client)
        break
        await asyncio.sleep(14_400)


async def check_steam_deals(client: SteamBot):
    print('check_steam_deals')
    while True:
        await client.check_deals()
        break
        await asyncio.sleep(3600)


async def check_tm_deals(client: SteamBot):
    print('check_tm_deals')
    while True:
        await csgotm.check_deals(client)
        break
        await asyncio.sleep(600)


async def ping_pong(client: SteamBot) -> None:
    print('ping_pong')
    url = f'https://market.csgo.com/api/v2/ping?key={client.tmApiKey}'
    while True:
        while True:
            async with app_storage['session'].get(url=url) as response:
                if response.status == 200:
                    answer = await response.json()
                    if answer["success"]:
                        break
                await asyncio.sleep(3)
        await asyncio.sleep(150)


async def main():
    app_storage['session'] = ClientSession()
    csgotm.app_storage['session'] = app_storage['session']
    async with app_storage['session']:
        tasks = []
        # tasks = [asyncio.create_task(ping_pong(client=gotchaSC)),
        #          asyncio.create_task(check_trades(client=gotchaSC)),
        #          asyncio.create_task(check_tm_balance(client=gotchaSC)),
        #          asyncio.create_task(check_steam_balance(client=gotchaSC)),
        #          asyncio.create_task(check_steam_listings(client=gotchaSC)),
        #          asyncio.create_task(check_items_to_sell_on_tm(client=gotchaSC)),
        #          asyncio.create_task(get_items_to_buy_in_steam(client=gotchaSC)),
        #          asyncio.create_task(check_cases_in_steam_inventory(client=gotchaSC))]
        # tasks.append(asyncio.create_task(check_trades(client=gotchaSC)))
        # tasks.append(asyncio.create_task(get_items_to_buy_in_steam(client=gotchaSC)))
        tasks.append(asyncio.create_task(check_items_to_sell_on_tm(client=gotchaSC)))

        await asyncio.gather(*tasks)


if __name__ == '__main__':
    print(time.strftime('%X'))
    asyncio.run(main())
    print(time.strftime('%X'))
