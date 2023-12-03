import datetime
import time

import config


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


async def get_average_item_tm_price(history) -> float:
    day = int(time.time()) - 87_000
    week = int(time.time()) - 348_000
    week_s = 0
    day_s = 0
    day_c = 0
    week_c = 0
    for deal in history:
        if deal[0] >= day:
            day_c += 1
            week_c += 1
            week_s += deal[1]
            day_s += deal[1]
        elif deal[0] >= week:
            week_c += 1
            week_s += deal[1]
        else:
            break
    return (day_s / day_c + week_s / week_c) / 2.0


async def get_average_item_steam_price(prices) -> float:
    day = datetime.date.today() - datetime.timedelta(days=1)
    week = datetime.date.today() - datetime.timedelta(days=4)
    day_s = 0
    week_s = 0
    day_t = 0
    week_t = 0
    for price in prices:
        arr = price[0].split(' ')
        tDate = datetime.date(int(arr[2]), config.month[arr[0]], int(arr[1]))
        if tDate >= day:
            day_s += price[1]
            week_s += price[1]
            day_t += 1
            week_t += 1
        elif tDate >= week:
            week_s += price[1]
            week_t += 1
        else:
            break
    return day_s * 0.6 / day_t + week_s * 0.4 / week_t


async def find_unique_items(items, listed_items):
    listed_items_names = [item['market_hash_name'] for item in listed_items]
    answer = []
    for item in items:
        if item['market_hash_name'] not in listed_items_names:
            answer.append(item)
            listed_items_names.append(item['market_hash_name'])
    return answer
    # for item in items:
    #     if item['market_hash_name'] not in unique_items:
    #         unique_items.append(item)
    # return unique_items


async def find_listed_items(items: list):
    result = []
    if items is not None and len(items):
        for item in items:
            if int(item['status']) == 1:
                result.append(item)
    return result
