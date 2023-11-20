import asyncio
import datetime
import json
import time
from typing import List, Any

from aiohttp import ClientSession

import config
import csgotm
import db
import steam
from steam import SteamBot
from steampy.models import GameOptions

from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

app_storage = {}
gotchaSC = SteamBot(config.gotchaLog)


# assholeSC = SteamBot(config.assholeLog)
# zybinsteam1 = SteamBot(config.zybinsteam1)
# zybinsteam2 = SteamBot(config.zybinsteam2)


async def get_tm_items_ratio(client, items):
    arr = []
    urlA: str
    uraB: str
    for item in items:
        urlA = f'https://market.csgo.com/api/v2/get-list-items-info?key={client.tmApiKey}&' \
               f'list_hash_name[]={item}&list_hash_name[]={item}'
        urlB = f'https://market.csgo.com/api/v2/search-item-by-hash-name-specific?' \
               f'key={client.tmApiKey}&hash_name={item}'
        b = True
        while b:
            try:
                async with app_storage['session'].get(url=urlA) as response:
                    answer = await response.json(content_type=None)
                    # print(await response.text())
                    if answer["success"]:
                        for order in answer['orders']:
                            arr.append(order['hash_name'])
                        b = False
            except Exception as ex:
                print(f'Error in getting buy case orders: {ex}')
                await asyncio.sleep(3)
        print(arr)
    return arr


async def get_buy_orders(client):
    arr = []
    url = f'https://market.csgo.com/api/v2/get-orders?key={client.tmApiKey}&page=0'
    b = True
    while b:
        try:
            async with app_storage['session'].get(url=url) as response:
                answer = await response.json(content_type=None)
                # print(await response.text())
                with open('info.json', 'wt') as f:
                    json.dump(answer, f, indent=4)
                if answer["success"]:
                    for order in answer['orders']:
                        arr.append(order['hash_name'])
                    b = False
        except Exception as ex:
            print(f'Error in getting buy case orders: {ex}')
            await asyncio.sleep(3)
    print(arr)
    return arr


async def delete_buy_orders(client, names):
    b: bool
    for name in names:
        url = f'https://market.csgo.com/api/v2/set-order?key={client.tmApiKey}' \
              f'&market_hash_name={name}' \
              f'&count=0&price=0'
        b = True
        while b:
            try:
                async with app_storage['session'].get(url=url) as response:
                    answer = await response.json(content_type=None)
                    if answer['success']:
                        b = False
            except Exception as ex:
                await asyncio.sleep(2)
        await asyncio.sleep(1)
    print('deleted')


async def get_tm_cases_info(client):
    result = {}
    b: bool
    print('Start getting tm cases info...')
    for case in config.containers:
        url = f'https://market.csgo.com/api/v2/get-list-items-info?key={client.tmApiKey}&list_hash_name[]={case}&' \
              f'list_hash_name[]={case}'
        b = True
        while b:
            try:
                async with app_storage['session'].get(url=url) as response:
                    answer = await response.json(content_type=None)
                    if answer["success"]:
                        if type(answer['data']) is not list:
                            # print(case)
                            result[case] = answer['data'][case]['average'] - 0.015
                        b = False
            except Exception as ex:
                print(f'Error getting tm case info: {ex}')
                await asyncio.sleep(3)
        await asyncio.sleep(1)
    print('Tm cases info was given')
    return result


async def get_cases_ratio(steamCasesInfo: dict, tmCasesInfo: dict) -> dict:
    result = {}
    ratio: float
    for key in steamCasesInfo.keys():
        ratio = round(steamCasesInfo[key] / tmCasesInfo[key], 3)

        if ratio >= config.minCaseBuyingPrice:
            result[key] = [tmCasesInfo[key], ratio, steamCasesInfo[key]]
        else:
            result[key] = [steamCasesInfo[key] / config.minCaseBuyingPrice, config.minCaseBuyingPrice,
                           steamCasesInfo[key]]
    return result


async def create_case_buy_orders(client: SteamBot, cases: dict):
    b: bool
    for key in cases.keys():
        url = f'https://market.csgo.com/api/v2/set-order?key={client.tmApiKey}' \
              f'&market_hash_name={key}' \
              f'&count=100&price={int(cases.get(key)[0] * 1000)}'
        b = True
        while b:
            try:
                async with app_storage['session'].get(url=url) as response:
                    answer = await response.json(content_type=None)
                    if answer['success']:
                        b = False

            except Exception as ex:
                print(f'Error in creating buy case order: {ex}')
                await asyncio.sleep(3)
        await asyncio.sleep(1)


async def buy_cases(client: SteamBot):
    try:
        tmCasesInfo = await get_tm_cases_info(client)
        steamCasesInfo = await steam.get_steam_cases_info(tmCasesInfo.keys())
        print('success')
        casesRatio = await get_cases_ratio(steamCasesInfo, tmCasesInfo)
        print(len(casesRatio.keys()))
        # TODO fill database
        await create_case_buy_orders(client=client, cases=casesRatio)
    except Exception as ex:
        print(f'Error in create_buy_case_orders:\n\t{ex}')


async def check_tm_balance(client) -> None:
    url = f'https://market.csgo.com/api/v2/get-money?key={client.tmApiKey}'
    while True:
        try:
            async with app_storage['session'].get(url=url) as response:
                answer = await response.json(content_type=None)
                if answer["success"]:
                    if answer["money"] >= 5:
                        await buy_cases(client)
                        # await check_tm_items(client)
                        # await get_buy_orders(client)
                        # await check_trade_offers(client)
                        await asyncio.sleep(3600)
            await asyncio.sleep(10)
        except Exception as ex:
            print(f'Error in check_tm_balance:\n\t{ex}')


async def check_steam_balance(client: SteamBot):
    while True:
        listings = (await client.get_steam_listings())['buy_orders']
        if len(listings) != 0:
            await client.delete_buy_orders(listings.keys())
        balance = await client.get_balance()
        if balance > 20:
            await client.create_buy_orders(balance * 1000)
        await asyncio.sleep(43200)


async def get_trades_to_send(client):
    url = f'https://market.csgo.com/api/v2/trade-request-give-p2p-all?key={client.tmApiKey}'
    b = True
    result = []
    a: bool
    while b:
        try:
            async with app_storage['session'].get(url=url) as response:
                answer = await response.json()
                print(answer)
                if answer['success']:
                    for trade in answer['offers']:
                        url = f'https://market.csgo.com/api/v2/trade-request-take?key={client.tmApiKey}&bot={trade["partner"]}'
                        a = True
                        while a:
                            try:
                                async with app_storage['session'].get(url=url) as response:
                                    a2 = await response.json()
                                    a = False
                                    print(a2)
                                    if a2['success']:
                                        if a2['trade']:
                                            result.append(a2['trade'])
                            except Exception as ex:
                                print(f'Error in getting trades to send info: {ex}')
                                await asyncio.sleep(3)

                b = False
        except Exception as ex:
            print(f'Error in getting trades to send: {ex}')
            await asyncio.sleep(3)


async def check_trade_offers(client) -> None:
    url = f'https://market.csgo.com/api/v2/trades?key={client.tmApiKey}&extended=1'
    b: bool
    print('Start checking trades...')
    while True:
        print('Start new search...')
        b = True
        items_to_sell = []
        while b:
            try:
                async with app_storage['session'].get(url=url) as response:
                    if response.status == 200:
                        b = False
                        if (await response.json())["success"]:
                            tm_trades = (await response.json())['trades']
                            print(tm_trades)
                            steam_trades = client.steam_client.get_trade_offers()['response']['trade_offers_received']
                            print(steam_trades)
                            await asyncio.sleep(3)
                            if len(steam_trades) != 0:
                                for tm_trade in tm_trades:
                                    print(tm_trade)
                                    for steam_trade in steam_trades:
                                        if int(tm_trade['bot_id']) == steam_trade['accountid_other'] and tm_trade['secret'] == steam_trade['message'].split(' ')[0]:
                                            client.steam_client.accept_trade_offer(steam_trade['tradeofferid'])
                                            if tm_trade['dir'] == 'out':
                                                inventory = client.steam_client.get_my_inventory(game=GameOptions.CS)
                                                item_id = 0
                                                for key in tm_trade['list_item_id'].keys():
                                                    market_hash_name = steam_trade['items_to_receive'][tm_trade['list_item_id'][key]['assetid']]['market_hash_name']
                                                    for item in inventory.keys():
                                                        if inventory[item]['market_hash_name'] == market_hash_name and inventory[item]['instanceid'] == tm_trade['list_item_id'][key]['instanceid']:
                                                            items_to_sell.append({'assetid': key,
                                                                            'market_hash_name': market_hash_name})
                                                            break
                                await asyncio.sleep(3)
                                await client.sell_items_by_id(items=items_to_sell)
            except Exception as ex:
                print(f'Error in getting trades: {ex}')
                await asyncio.sleep(3)
        await asyncio.sleep(60)
    print('Checking trades finished')


async def check_tm_items(client):
    arr = []
    url = f'https://market.csgo.com/api/v2/items?key={client.tmApiKey}'
    b = True
    print('Start checking tm items...')
    with open('result.json', 'wt') as f:
        while b:
            try:
                async with app_storage['session'].get(url=url) as response:
                    answer = await response.json(content_type=None)
                    if answer["success"]:
                        json.dump(answer, f, indent=4)
                    # for item in answer['items']:
                    #     arr.append(order['hash_name'])
                    # b = False
                    b = False
            except Exception as ex:
                print(f'Error in checking tm items: {ex}')
                await asyncio.sleep(3)
    print('Checking tm items finished!')
    return arr


async def ping_pong(tmApiKey: str) -> None:
    url = f'https://market.csgo.com/api/v2/ping?key={tmApiKey}'
    while True:
        async with app_storage['session'].get(url=url) as response:
            answer = await response.json(content_type=None)
            if answer["success"]:
                print('Sales are on!')
        await asyncio.sleep(5)


async def go_offline(tmApiKey: str) -> None:
    url = f'https://market.csgo.com/api/v2/go-offline?key={tmApiKey}'
    async with app_storage['session'].get(url=url) as response:
        answer = await response.json(content_type=None)
        if answer["success"]:
            print('You are offline!')


async def doT():
    while True:
        print(1)
        await asyncio.sleep(3)


async def get_items_to_buy_in_steam(client):
    items = (await csgotm.get_popular_tm_items())
    print(len(items))
    result = {}
    b: bool
    url: str
    print('Start getting tm cases info...')
    for item in items:
        url = f'https://market.csgo.com/api/v2/get-list-items-info?key={client.tmApiKey}&list_hash_name[]={item}&' \
              f'list_hash_name[]={item}'
        b = True
        while b:
            try:
                async with app_storage['session'].get(url=url) as response:
                    # print(response.status)
                    answer = await response.json(content_type=None)
                    if answer["success"]:
                        if type(answer['data']) is not list:
                            # print(answer)
                            result[item] = [answer['data'][item]['average']]
                        b = False
            except Exception as ex:
                # print(f'Error getting tm case info: {ex}')
                await asyncio.sleep(3)
        await asyncio.sleep(1)
        # print(result)
    print('Tm cases info was given')
    print(len(result))
    # print(result, sep='\n')
    res = await client.get_steam_items_to_buy_info(items=result)
    print(len(res))
    buyList = {}
    secondList = {}
    thirdList = {}
    # print(res)
    for key in res.keys():
        if res[key][0] >= res[key][1]:
            buyList[key] = res[key]
        elif res[key][0] >= res[key][1] * 0.95:
            secondList[key] = res[key]
        elif res[key][0] >= res[key][1] * 0.9:
            thirdList[key] = res[key]
    print(len(buyList))
    print(len(secondList))
    print(len(thirdList))
    await db.save_prices(buyList, secondList, thirdList)


async def get_items_to_sell_on_tm(client) -> list[Any]:
    url = f'https://market.csgo.com/api/v2/update-inventory?key={client.tmApiKey}'
    b = True
    while b:
        try:
            async with app_storage['session'].get(url=url) as response:
                if response.status == 200:
                    b = not (await response.json())['success']
        except Exception as ex:
            print(ex)
            await asyncio.sleep(1)
            continue
    url = f'https://market.csgo.com/api/v2/my-inventory?key={client.tmApiKey}'
    b = True
    while b:
        try:
            async with app_storage['session'].get(url=url) as response:
                print(response.status)
                if response.status == 200:
                    b = False
                    answer = await response.json(content_type=None)
                    result = []
                    for item in answer['items']:
                        if item['market_price'] > 4.0:
                            result.append(item)
                    # with open('result.json', 'wt') as f:
                    #     json.dump(result, f, indent=4)
                    return result
                else:
                    await asyncio.sleep(1)
        except Exception as ex:
            print(ex)
            await asyncio.sleep(1)
            continue


async def get_item_prices_to_sell_on_tm(client, items: list):
    url: str
    print(1)
    for item in items:
        url = f'https://market.csgo.com/api/v2/search-item-by-hash-name-specific?key={client.tmApiKey}&hash_name={item["market_hash_name"]}'
        b = True

        while b:
            try:
                async with app_storage['session'].get(url=url) as response:
                    # print(response.status)
                    if response.status == 200:
                        b = False
                        item['lowest_tm_price'] = (await response.json())['data'][0]['price']
                        # print(await response.json())
                    else:
                        await asyncio.sleep(1)
            except Exception as ex:
                print(ex)
                await asyncio.sleep(1)
                continue


async def sell_tm_items(client, items):
    url: str
    # TODO db
    for item in items:
        if item['tm_status']:
            url = f'https://market.csgo.com/api/v2/add-to-sale?key={client.tmApiKey}&id={item["id"]}&' \
                  f'price={item["lowest_tm_price"] - 1}&cur=USD'
            b = True
            while b:
                async with app_storage['session'].get(url=url) as response:
                    if response.status == 200 and (await response.json())['success']:
                        b = False
                    await asyncio.sleep(1)
            await asyncio.sleep(1)
        else:
            ans = client.steam_client.market.create_sell_order(assetid=str(item['id']), game=GameOptions.CS,
                                                               money_to_receive=str(item['lowest_steam_price'] / 10))
            await asyncio.sleep(3.1)
            print(ans)


async def check_items_to_sell_on_tm(client: SteamBot):
    items = await get_items_to_sell_on_tm(client)
    await client.get_items_info_to_sell_on_tm(items)
    await get_item_prices_to_sell_on_tm(client, items)
    for item in items:
        item['tm_status'] = True if item['lowest_steam_price'] * 0.87 * 0.93 <= item[
            'lowest_tm_price'] * 0.95 else False
    await sell_tm_items(client, items)


async def main():
    app_storage['session'] = ClientSession()
    async with app_storage['session']:
        tasks = []
        tasks.append(asyncio.create_task(ping_pong(gotchaSC.tmApiKey)))
        await asyncio.gather(*tasks)
        # with open('result.json', 'wt') as f:
        #     json.dump(gotchaSC.steam_client.get_my_inventory(GameOptions.CS), f, indent=4)


if __name__ == '__main__':
    print(time.strftime('%X'))
    asyncio.run(main())
    print(time.strftime('%X'))
