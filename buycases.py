import asyncio
import json
import time

import config
import csgotm
import steam
from steam import SteamBot
from steampy.models import GameOptions

app_storage = {}
gotchaSC = SteamBot(config.gotchaLog)
# assholeSC = SteamBot(config.assholeLog)
# zybinsteam1 = SteamBot(config.zybinsteam1)
# zybinsteam2 = SteamBot(config.zybinsteam2)

async def get_tm_cases_info(client):
    with open('result.json', 'wt') as f:
        result = {}
        for case in config.containers:
            url = f'https://market.csgo.com/api/v2/get-list-items-info?key={client.tmApiKey}&list_hash_name[]={case}&' \
                  f'list_hash_name[]={case}'
            try:
                async with app_storage['session'].get(url=url) as response:
                    answer = await response.json(content_type=None)

                    if answer["success"]:
                        # print(answer)
                        if type(answer['data']) is not list:
                            print(case)
                            # print(answer)
                            result[case] = answer['data'][case]['average'] - 0.005
                            # json.dump(answer, f, indent=4)
                            # f.write('\n')
                        else:
                            print(case)
            except Exception as ex:
                print(f'Exeption {ex} in get_tm_cases_info')
            await asyncio.sleep(1)
        return result


async def get_cases_ratio(steamCasesInfo: dict, tmCasesInfo: dict) -> dict:
    result = {}
    ratio: float
    for key in steamCasesInfo.keys():
        ratio = round(steamCasesInfo[key] / tmCasesInfo[key], 3)

        if ratio >= config.minCaseBuyingPrice:
            result[key] = [tmCasesInfo[key], ratio, steamCasesInfo[key]]
        else:
            result[key] = [steamCasesInfo[key] / config.minCaseBuyingPrice, ratio, steamCasesInfo[key]]
    return result


async def create_case_buy_orders(client: SteamBot, cases: dict):
    # result = {}
    # for case in config.containers:
    with open('result.json', 'wt') as f:
        for key in cases.keys():
            url = f'https://market.csgo.com/api/v2/set-order?key={client.tmApiKey}' \
                  f'&market_hash_name={key}' \
                  f'&count=1&price=100'
            try:
                async with app_storage['session'].get(url=url) as response:
                    print(await response.text())
                    answer = await response.json(content_type=None)

                    json.dump(answer, f, indent=4)
                    f.write('\n')

            except Exception as ex:
                print(f'Exeption {ex} in get_tm_cases_info')
            await asyncio.sleep(0.33)


async def buy_cases(client: SteamBot):
    try:
        tmCasesInfo = await get_tm_cases_info(client)
        steamCasesInfo = await steam.get_steam_cases_info(tmCasesInfo.keys())
        print('success')
        casesRatio = await get_cases_ratio(steamCasesInfo, tmCasesInfo)
        print(casesRatio)
        # TODO fill database
        await create_case_buy_orders(client=client, cases=casesRatio)
    except Exception as ex:
        print(f'Error in create_buy_case_orders:\n\t{ex}')


if __name__ == '__main__':
    print(time.strftime('%X'))
    asyncio.run(buy_cases(gotchaSC))
    print(time.strftime('%X'))
