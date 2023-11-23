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
