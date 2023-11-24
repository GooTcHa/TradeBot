import asyncio
import datetime
import json
import time

import bs4
import os
from steampy.models import Currency
from steampy.client import SteamClient
from steampy.utils import GameOptions
import pickle
import config
import db


async def get_steam_cases_info(cases) -> dict:
    result = {}
    while True:
        with open('steam_cases_ratio.json', 'r') as f:
            saved_data = json.load(f)
        if saved_data['date'] < time.time() - 45_000:
            await asyncio.sleep(3_600)
        else:
            break
    for case in cases:
        result[case] = saved_data['cases_ratio'][case] - 0.005
    return result


class SteamBot:
    def __init__(self, accountDetails):
        self.steam_client: SteamClient
        self.accountDetails = accountDetails
        self.login = accountDetails['login']
        self.password = accountDetails['password']
        self.steamApiKey = accountDetails['steamApiKey']
        self.tmApiKey = accountDetails['tmApiKey']
        self.maFile = accountDetails['maFile']
        self.steamSession = accountDetails['steamSession']
        if os.path.isfile(accountDetails['steamSession']):
            print("Using previous session")
            with open(accountDetails['steamSession'], 'rb') as f:
                self.steam_client = pickle.load(f)
                print(self.steam_client.is_session_alive())
                if not self.steam_client.is_session_alive():
                    print('Resinging in...')
                    self.steam_client = SteamClient(accountDetails['steamApiKey'])
                    self.steam_client.login(accountDetails['login'], accountDetails['password'],
                                            accountDetails['maFile'])  # авторизируемся в аккаунте
                    print("Saving session")
                    with open(accountDetails['steamSession'], 'wb') as f:
                        pickle.dump(self.steam_client, f)

        else:
            print("You not authorized, trying to login into Steam")
            print("Signing in steam account")
            self.steam_client = SteamClient(accountDetails['steamApiKey'])
            self.steam_client.login(accountDetails['login'], accountDetails['password'],
                                    accountDetails['maFile'])  # авторизируемся в аккаунте
            print("Saving session")
            with open(accountDetails['steamSession'], 'wb') as f:
                pickle.dump(self.steam_client, f)
        if config.proxis[self.login].get('http') is not None:
            self.steam_client.set_proxies(config.proxis[self.login])

    async def get_steam_items_to_buy_info(self, items: dict, items_to_buy: dict):
        response: json
        tDate: datetime.date
        price: float
        ratio = config.ratioForSkinsToBy
        for item in items.keys():
            print(item)
            try:
                response = self.steam_client.market.fetch_price(item, GameOptions.CS)
                if response['success']:
                    if response.get('median_price') is not None:
                        price = float(response['median_price'].split(' ')[0].strip('$'))
                    else:
                        price = float(response['lowest_price'].split(' ')[0].strip('$'))
                    if price <= items[item]:
                        items_to_buy['ratio']['positive_ratio'][item] = price * 0.98
                    elif price * ratio <= items[item]:
                        items_to_buy['ratio']['average_ratio'][item] = price * 0.97
                    else:
                        items_to_buy['ratio']['negative_ratio'][item] = items[item] * 0.95
            except Exception as ex:
                print(f'Exeption {ex} in get_steam_cases_info')
            await asyncio.sleep(6)

    async def accept_trades(self, trades):

        steam_trades = self.steam_client.get_trade_offers()['response']['trade_offers_received']
        if len(steam_trades) != 0:
            await asyncio.sleep(5)
            for trade in trades:
                for steam_trade in steam_trades:
                    if int(trade['bot_id']) == steam_trade['accountid_other']:
                        try:
                            self.steam_client.accept_trade_offer(trade['trade_id'])
                            await asyncio.sleep(2)
                        except Exception as ex:
                            print(f'Failed accepting trades {time.time()} -> {ex}')
        print('trades were accepted')

    async def get_steam_listings(self):
        return self.steam_client.market.get_my_market_listings()

    async def create_buy_orders(self, balance):
        while True:
            with open('items_to_buy.json') as f:
                items = json.load(f)
            if items['date'] > time.time() - 45_000:
                break
            else:
                await asyncio.sleep(3_600)
        price: int
        for key in items['ratio'].keys():
            for item in items['ratio'][key].keys():
                count = await db.get_bought_item_count(item)
                if count < 5:
                    try:
                        price = int(round(items['ratio'][key][item], 2) * 100)
                        balance -= price * 5
                        if balance < 0:
                            break
                        self.steam_client.market.create_buy_order(market_name=item,
                                                                  price_single_item=str(price),
                                                                  quantity=5 - count,
                                                                  game=GameOptions.CS,
                                                                  currency=Currency.USD)
                    except Exception as ex:
                        print(ex)
                    await asyncio.sleep(1)

    async def get_balance(self):
        return float(self.steam_client.get_wallet_balance())

    async def get_max_steam_cases_price(self):
        priceHistory = []
        response: json
        data_to_save = {'date': time.time(),
                        'cases_ratio': {}}
        date = datetime.date.today() - datetime.timedelta(days=1)
        for case in config.containers:
            print('case')
            try:
                response = self.steam_client.market.fetch_price_history(case, GameOptions.CS)
                if response['success']:
                    prices = reversed(response['prices'][-50:])
                    for price in prices:
                        arr = price[0].split(' ')
                        tDate = datetime.date(int(arr[2]), config.month[arr[0]], int(arr[1]))
                        if tDate >= date:
                            priceHistory.append(price[1])
                max_price = max(priceHistory)
                data_to_save['cases_ratio'][case] = max_price
                priceHistory.clear()
                await asyncio.sleep(3.1)
            except Exception as ex:
                print(f'Exeption {ex} in get_steam_cases_info')
        with open('steam_cases_ratio.json', 'wt') as f:
            json.dump(data_to_save, f, indent=4)
        return data_to_save

    async def sell_cases_from_inventory(self):
        items = self.steam_client.get_my_inventory(game=GameOptions.CS)
        if len(items.keys()) != 0:
            while True:
                with open('steam_cases_ratio.json') as f:
                    prices = json.load(f)
                if prices['date'] < time.time() - 45_000:
                    await asyncio.sleep(3600)
                else:
                    break
            for item in items.keys():
                if items[item]['market_hash_name'] in config.containers:
                    self.steam_client.market.create_sell_order(assetid=item, game=GameOptions.CS,
                                                               money_to_receive=str(
                                                                   int(prices['cases_ratio']
                                                                       [items[item]['market_hash_name']] * 87)))
                    await asyncio.sleep(2)

    async def change_case_listings(self, listings: dict):
        while True:
            with open('steam_cases_ratio.json', 'r') as f:
                prices = json.load(f)
            if prices['date'] < time.time() - 86_400:
                await asyncio.sleep(3_600)
            else:
                break
        for listing in listings.keys():
            date = listings[listing]['created_on'].split(' ')
            if len(date) == 2:
                cmp_date = datetime.date(year=datetime.date.today().year, month=config.month[date[1]],
                                         day=int(date[0]))
            else:
                cmp_date = datetime.date(year=datetime.date.today().year - 1, month=config.month[date[1]],
                                         day=int(date[0]))
            time_delta = datetime.timedelta(days=1)
            if cmp_date <= datetime.date.today() - time_delta:
                if listings[listing]['description']['market_hash_name'] in config.containers:
                    self.steam_client.market.cancel_sell_order(sell_listing_id=listings[listing]['listing_id'])
                    await asyncio.sleep(3)
                    self.steam_client.market.create_sell_order(assetid=listings[listing]['description']['id'],
                                                               game=GameOptions.CS,
                                                               money_to_receive=str(int(prices['cases_ratio']
                                                                                        [listings[listing]
                                                                   ['description']['market_hash_name']] * 87.5)))
                else:
                    self.steam_client.market.cancel_sell_order(sell_listing_id=listings[listing]['listing_id'])
                await asyncio.sleep(3)

    async def get_inventory(self):
        items = self.steam_client.get_my_inventory(game=GameOptions.CS)
        with open('result.json', 'wt') as f:
            json.dump(items, f, indent=4)

    async def get_completed_steam_buy_orders(self) -> json:
        url = 'https://steamcommunity.com/market/myhistory?count=50'
        response = self.steam_client.session.get(url)
        state: str
        return response.json()

    async def check_deals(self):
        response = await self.get_completed_steam_buy_orders()
        response_soup = bs4.BeautifulSoup(response['results_html'], "html.parser")
        history = response_soup.find_all('div', class_='market_listing_row market_recent_listing_row')
        items = response['assets']['730']['2']
        # with open('info.json', 'wt') as f:
        #     json.dump(items, f, indent=4)
        # return None
        with open('latest_steam_deals/___stewart___.txt', 'r') as f:
            latest_deal = f.readline().strip('\n')
        keys_list = list(items.keys())
        j = 0
        for i in range(len(keys_list)):
            if keys_list[i] == latest_deal:
                with open('latest_steam_deals/___stewart___.txt', 'w') as f:
                    f.write(keys_list[0])
                break
            state = history[j].find('div', class_='market_listing_left_cell market_listing_gainorloss').text.strip()
            while history[j].find('span', class_='market_listing_game_name').text != 'Counter-Strike 2' and (
                    state == '' or state == ' '):
                j += 1
                state = history[j].find('div', class_='market_listing_left_cell market_listing_gainorloss').text.strip()
            price = float(
                history[j].find('span', class_='market_listing_price').text.strip().strip('+- $USD\n').replace(',',
                                                                                                               '.'))
            j += 1
            if state == '+':
                await db.add_bought_item(self.login, items[keys_list[i]]['market_hash_name'], price)
            else:
                await db.add_sale_info(self.login, items[keys_list[i]]['market_hash_name'], price)

    async def delete_buy_orders(self, orders):
        for order in orders:
            self.steam_client.market.cancel_buy_order(order)
            await asyncio.sleep(1)
