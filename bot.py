import datetime
import time
import asyncio
from aiohttp import ClientSession
import logging
from sys import argv

import config
import csgotm
from steam import SteamBot
from tgBot import send_message

app_storage = {}
login = argv[1]
client = SteamBot(config.logInfoList[login])
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


#Checking in/outcoming trades
#Approximate time 3s.
async def check_trades():
    logging.info(f'check_trades of {client.login} lunched')
    while True:
        logging.info(f'Start checking trades of {client.login}')
        trades = await csgotm.get_trades(client)
        if trades['success']:
            await client.accept_trades(trades['trades'])
            client.steam_client.commit_confirmation_list()
        logging.info(f'Trades of {client.login} was taken')
        await asyncio.sleep(60)


#Getting steam balance and creating buy orders if balance > 20$
#Approximately 110s
async def check_steam_balance():
    logging.info(f'check_steam_balance of {client.login} lunched')
    while True:
        logging.info(f'Start getting balance of {client.login}')
        listings = (await client.get_steam_listings())['buy_orders']
        await client.delete_buy_orders(listings.keys())
        balance = await client.get_balance()
        if balance > 20:
            await client.create_buy_orders(balance * 1000)
        logging.info(f'Balance of {client.login} was got')
        await asyncio.sleep(86_400)


#Check tm balance and create cases buy order on tm
#~170s.
async def check_tm_balance() -> None:
    logging.info(f'check_tm_balance of {client.login} lunched')
    while True:
        logging.info(f'Getting tm balance of {client.login}')
        balance = await csgotm.get_balance(client)
        if balance >= 4:
            await csgotm.buy_cases(client)
        #TODO delete sell orders
        logging.info(f'Tm balance of {client.login} was got')
        await asyncio.sleep(3_600)


#Find cases and sell them
#Approximately 10s
async def check_cases_in_steam_inventory():
    logging.info(f'check_cases_in_steam_inventory of {client.login} lunched')
    while True:
        logging.info(f'Start checking cases in inventory of {client.login}')
        await client.sell_cases_from_inventory()
        logging.info(f'Cases in inventory of {client.login} was checked')
        await asyncio.sleep(3_600)


#Create sell orders on tm
#~15s
async def check_items_to_sell_on_tm():
    logging.info(f'check_items_to_sell_on_tm of {client.login} lunched')
    while True:
        logging.info(f'Start checking items of {client.login} to sell on tm')
        await csgotm.create_new_listings_on_tm(client)
        logging.info(f'Finish checking items of {client.login} to sell on tm')
        await asyncio.sleep(7_200)


#Check if sell price is close to current
#~20s
async def check_steam_listings():
    logging.info(f'check_steam_listings of {client.login} lunched')
    while True:
        logging.info(f'Start checking steam listings of {client.login}')
        cmp_date: datetime.date
        listings = (await client.get_steam_listings())['sell_listings']
        if len(listings.keys()):
            await client.change_case_listings(listings=listings)
        logging.info(f'Finish checking steam listings of {client.login}')
        await asyncio.sleep(86_400)


#Check selling items
#~10
async def check_tm_listings():
    logging.info(f'check_tm_listings of {client.login} lunched')
    while True:
        logging.info(f'Start checking tm listings of {client.login}')
        await csgotm.get_history(client)
        await csgotm.check_listings(client)
        logging.info(f'Finish checking tm listings of {client.login}')
        await asyncio.sleep(14_400)


#Get deals first on tm then on steam
#~10s
async def check_deals():
    logging.info(f'check_deals of {client.login} lunched')
    while True:
        logging.info(f'Start checking deals of {client.login}')
        await csgotm.check_deals(client)
        await client.check_deals()
        logging.info(f'Finish checking deals of {client.login}')
        await asyncio.sleep(3_600)


async def turn_on_sellings() -> None:
    logging.info(f'ping_pong of {client.login} lunched')
    await csgotm.ping_pong(client)
    await asyncio.sleep(150)


async def check_session():
    while True:
        if not await client.check_session():
            await client.update_session()
        await asyncio.sleep(86_000)


async def main():
    app_storage['session'] = ClientSession()
    csgotm.app_storage['session'] = app_storage['session']
    csgotm.app_storage['proxy'] = config.proxis[login]['http']
    async with app_storage['session']:
        tasks = [asyncio.create_task(turn_on_sellings()),
                 asyncio.create_task(check_trades()),
                 asyncio.create_task(check_cases_in_steam_inventory()),
                 asyncio.create_task(check_items_to_sell_on_tm()),
                 asyncio.create_task(check_tm_balance()),
                 asyncio.create_task(check_steam_balance()),
                 asyncio.create_task(check_tm_listings()),
                 asyncio.create_task(check_steam_listings()),
                 asyncio.create_task(check_deals()),
                 asyncio.create_task(check_session())]
        await send_message(f'Account {login} is running!')
        try:
            await asyncio.gather(*tasks)
        finally:
            await send_message(f'Account {login} stopped...')


if __name__ == '__main__':
    print(time.strftime('%X'))
    asyncio.run(main())
    print(time.strftime('%X'))
