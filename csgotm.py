import asyncio
import json
import time
import logging

from selenium import webdriver
from selenium.common import TimeoutException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import calculations
import config
import db
import steam
from steam import SteamBot

app_storage = {}
# logging.basicConfig(level=logging.INFO, filename="logs/csgotm.log", filemode="w",
#                     format="%(asctime)s %(levelname)s %(message)s")


async def get_balance(client: SteamBot):
    url = f'https://market.csgo.com/api/v2/get-money?key={client.tmApiKey}'
    while True:
        async with app_storage['session'].get(url=url, proxy=app_storage['proxy']) as response:
            if response.status == 200:
                answer = await response.json()
                if answer["success"]:
                    return answer['money']
                await asyncio.sleep(10)


async def delete_buy_orders(client: SteamBot):
    for case in config.containers:
        # url = f'https://market.csgo.com/api/v2/buy?key={client.tmApiKey}&hash_name={case}' \
        #       f'&price=0'
        url = f'https://market.csgo.com/api/v2/set-order?key={client.tmApiKey}' \
              f'&market_hash_name={case}' \
              f'&count=0'
        while True:
            async with app_storage['session'].get(url=url, proxy=app_storage['proxy']) as response:
                if response.status == 200:
                    answer = await response.json()
                    break
            await asyncio.sleep(1)


async def get_popular_tm_items():
    print('Start getting tm items to buy...')
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-blink-features=AutomationControlled")
    with webdriver.Chrome(options=options) as driver:
        urls = [
            'https://market.csgo.com/en/?sort=profit&order=asc&priceMin=5&priceMax=30&rarity=Restricted&rarity=Covert&type=Pistol&type=Rifle&type=Sniper%20Rifle&type=SMG&type=Machinegun&type=Shotgun',
            'https://market.csgo.com/en/?priceMin=5&priceMax=30&rarity=Restricted&rarity=Covert&type=Pistol&type=Rifle&type=Sniper%20Rifle&type=SMG&type=Machinegun&type=Shotgun',
            'https://market.csgo.com/en/?sort=offers&order=desc&priceMin=5&priceMax=30&rarity=Restricted&rarity=Covert&type=Pistol&type=Rifle&type=Sniper%20Rifle&type=SMG&type=Machinegun&type=Shotgun'
        ]
        for url in urls:
            driver.get(url)
            driver.maximize_window()
            v: str
            items = []
            for i in range(30):
                try:
                    elements = WebDriverWait(driver, 1000).until(
                        EC.presence_of_all_elements_located((By.CLASS_NAME, "item-info-block"))
                    )
                    for e in elements:
                        try:
                            items.append(e.text.split('\n')[-1].split('(')[0])
                        except Exception as ex:
                            continue
                    actions = ActionChains(driver)
                    actions.move_to_element(elements[-1])
                    actions.perform()
                except TimeoutException:
                    pass
        print('Finish getting items')
        return list(set(items))


async def get_items_to_buy(client: SteamBot):
    items = await get_popular_tm_items()
    item_name: str
    items_to_check = {}
    items_to_buy = {
        'date': 0,
        'ratio':
            {
                'positive_ratio': {},
                'average_ratio': {},
                'negative_ratio': {}
            }
    }
    url = f'https://market.csgo.com/api/v2/get-list-items-info?key={client.tmApiKey}'
    print(f'Start getting items to buy in steam {time.time()}')
    for item_name in items:
        items_request = url
        for quality in config.quality:
            items_request += f'&list_hash_name[]={item_name + quality}'
        while True:
            async with app_storage['session'].get(url=items_request) as response:
                if response.status == 200:
                    answer = await response.json()
                    cmpTime = int(time.time()) - 87_000
                    if answer['success'] and type(answer['data']) is dict:
                        for item in answer['data'].keys():
                            if 4.0 < answer['data'][item]['average'] < 29.0:
                                c = 0
                                s = 0
                                for deal in answer['data'][item]['history']:
                                    if deal[0] >= cmpTime:
                                        c += 1
                                        s += deal[1]
                                    else:
                                        break
                                if c >= 10:
                                    items_to_check[item] = min(s / c, answer['data'][item]['average'])
                        await client.get_steam_items_to_buy_info(items_to_check, items_to_buy)
                        items_to_check = {}
                    break
                else:
                    await asyncio.sleep(1.5)
        await asyncio.sleep(2)
    with open('items_to_buy.json', 'wt') as f:
        items_to_buy['date'] = int(time.time())
        json.dump(items_to_buy, f, indent=4)
    print(f'Items to buy in steam were gained')


#Getting all unfinished trades from tm
async def get_trades(client: SteamBot):
    url = f'https://market.csgo.com/api/v2/trades?key={client.tmApiKey}&extended=1'
    while True:
        try:
            async with app_storage['session'].get(url=url, proxy=app_storage['proxy']) as response:
                if response.status == 200:
                    return await response.json()
                await asyncio.sleep(3)
        except Exception as ex:
            logging.error(f'Error while getting trades of {client.login}: ', exc_info=True)
            await asyncio.sleep(3)


async def get_tm_cases_info(client):
    result = {}
    for case in config.containers:
        url = f'https://market.csgo.com/api/v2/get-list-items-info?key={client.tmApiKey}&list_hash_name[]={case}'
        while True:
            try:
                async with app_storage['session'].get(url=url, proxy=app_storage['proxy']) as response:
                    if response.status == 200:
                        answer = await response.json()
                        if answer["success"]:
                            if type(answer['data']) is not list:
                                average_price = answer['data'][case]['average'] - 0.015
                            break
                    await asyncio.sleep(2)
            except Exception as ex:
                print(f'Error getting tm case info: {ex}')
                await asyncio.sleep(1)
        await asyncio.sleep(1)
        url = f'https://market.csgo.com/api/v2/search-item-by-hash-name-specific?key={client.tmApiKey}&hash_name={case}'
        while True:
            try:
                async with app_storage['session'].get(url=url, proxy=app_storage['proxy']) as response:
                    if response.status == 200:
                        answer = await response.json()
                        if answer["success"]:
                            if len(answer['data']):
                                min_price = answer['data'][0]['price'] / 1000
                                result[case] = min(average_price, min_price)
                            break
                    await asyncio.sleep(2)
            except Exception as ex:
                print(f'Error getting tm case info: {ex}')
                await asyncio.sleep(1)
        await asyncio.sleep(1)
    return result


async def create_case_buy_orders(client: SteamBot, cases: dict):
    b: bool
    for key in cases.keys():
        url = f'https://market.csgo.com/api/v2/set-order?key={client.tmApiKey}' \
              f'&market_hash_name={key}' \
              f'&count=100&price={int(cases.get(key)[0] * 1000)}'
        while True:
            try:
                async with app_storage['session'].get(url=url, proxy=app_storage['proxy']) as response:
                    if response.status == 200:
                        answer = await response.json(content_type=None)
                        if answer['success']:
                            break
            except Exception as ex:
                print(f'Error in creating buy case order: {ex}')
            await asyncio.sleep(1)
        await asyncio.sleep(1)


async def buy_cases(client: SteamBot):
    try:
        tmCasesInfo = await get_tm_cases_info(client)
        steamCasesInfo = await steam.get_steam_cases_info(tmCasesInfo.keys())
        casesRatio = await calculations.get_cases_ratio(steamCasesInfo, tmCasesInfo)
        await create_case_buy_orders(client=client, cases=casesRatio)
    except Exception as ex:
        print(f'Error in create_buy_case_orders:\n\t{ex}')


async def create_listings_by_list(client: SteamBot, items: list):
    for item in items:
        min_price = await get_min_item_bid_price(client, item['market_hash_name'])
        buy_price = await db.get_bought_item_price(client.login, item['market_hash_name'])
        min_acceptable_price = int(buy_price * config.ratioForSkinsToBy * 1000)
        # print(f'{item["market_hash_name"]} --> {min_price} --> {buy_price} --> {min_acceptable_price}')
        if min_price >= min_acceptable_price:
            await set_item_listing_price(client, item['id'], min_price - 1)
        else:
            await set_item_listing_price(client, item['id'], int(min_acceptable_price))


async def update_inventory(client: SteamBot) -> bool:
    url = f'https://market.csgo.com/api/v2/update-inventory?key={client.tmApiKey}'
    while True:
        async with app_storage['session'].get(url=url, proxy=app_storage['proxy']) as response:
            if response.status == 200:
                if (await response.json())["success"]:
                    return True
            await asyncio.sleep(1)


async def get_unlisted_items(client: SteamBot):
    url = f'https://market.csgo.com/api/v2/my-inventory?key={client.tmApiKey}'
    items = []
    while True:
        async with app_storage['session'].get(url=url, proxy=app_storage['proxy']) as response:
            if response.status == 200:
                answer = await response.json()
                if answer["success"]:
                    for i in answer['items']:
                        if i['market_price'] > 4.0:
                            items.append(i)
                break
        await asyncio.sleep(1)
    return items


async def get_listed_items(client: SteamBot):
    while True:
        url = f'https://market.csgo.com/api/v2/items?key={client.tmApiKey}'
        async with app_storage['session'].get(url=url, proxy=app_storage['proxy']) as response:
            if response.status == 200:
                answer = await response.json()
                if answer["success"]:
                    return await calculations.find_listed_items(answer['items'])
        await asyncio.sleep(1)


async def get_min_item_bid_price(client: SteamBot, market_name: str):
    url = f'https://market.csgo.com/api/v2/search-item-by-hash-name-specific?key={client.tmApiKey}&' \
          f'hash_name={market_name}'
    while True:
        async with app_storage['session'].get(url=url, proxy=app_storage['proxy']) as response:
            if response.status == 200:
                answer = await response.json()
                if answer["success"]:
                    return answer['data'][0]['price']
            await asyncio.sleep(1)


async def set_item_listing_price(client: SteamBot, item_id: str, price: int):
    url = f'https://market.csgo.com/api/v2/add-to-sale?key={client.tmApiKey}&id={item_id}&price={price - 1}&cur=USD'
    while True:
        async with app_storage['session'].get(url=url, proxy=app_storage['proxy']) as response:
            if response.status == 200:
                answer = await response.json()
                if answer["success"]:
                    break
        await asyncio.sleep(1)


async def create_new_listings_on_tm(client: SteamBot):
    if await update_inventory(client):
        items = await get_unlisted_items(client)
        # print(items)
        listed_items = await get_listed_items(client)
        items_to_buy = await calculations.find_unique_items(items=items, listed_items=listed_items)
        await create_listings_by_list(client=client, items=items_to_buy)


async def check_listings(client: SteamBot):
    items_to_check = await get_listed_items(client)
    for item in items_to_check:
        price = await get_min_item_bid_price(client, item["market_hash_name"])
        buy_price = await db.get_bought_item_price(client.login, item["market_hash_name"])
        if price != item['price']:
            if price < int(item['price']):
                if price < int(buy_price * 1000 * config.ratioForSkinsToBy):
                    price = 1
                await set_item_listing_price(client, item["item_id"], price)


async def get_history(client: SteamBot) -> list:
    while True:
        url = f'https://market.csgo.com/api/v2/history?key={client.tmApiKey}'
        async with app_storage['session'].get(url=url, proxy=app_storage['proxy']) as response:
            if response.status == 200:
                answer = await response.json()
                if answer["success"]:
                    history = []
                    for deal in answer['data']:
                        if deal['stage'] == '2':
                            history.append(deal)
                    return history


async def check_deals(client: SteamBot) -> None:
    history = await get_history(client)
    # with open('info.json', 'wt') as f:
    #     json.dump(history, f, indent= 4)
    # return None
    with open(f'latest_tm_deals/{client.login}.txt', 'r') as f:
        last_deal = f.readline().strip('\n')
    if last_deal != history[0]['item_id']:
        for deal in history:
            if last_deal == deal['item_id']:
                last_deal = history[0]['item_id']
                with open(f'latest_tm_deals/{client.login}.txt', 'wt') as f:
                    f.write(last_deal)
                break
            if deal['event'] == 'buy':
                await db.add_bought_item(client.login, deal['market_hash_name'], int(deal['paid']) / 1000.0)
            else:
                await db.add_sale_info(client.login, deal['market_hash_name'], int(deal['received']) / 1000.0)


async def ping_pong(client: SteamBot) -> None:
    url = f'https://market.csgo.com/api/v2/ping?key={client.tmApiKey}'
    while True:
        logging.info(f'ping of {client.login}')
        while True:
            try:
                async with app_storage['session'].get(url=url, proxy=app_storage['proxy']) as response:
                    if response.status == 200:
                        answer = await response.json()
                        if answer["success"]:
                            break
                    await asyncio.sleep(3)
            except Exception as ex:
                pass