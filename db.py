import asyncio
import sqlite3

import aiosqlite
import time


#
# con = sqlite3.connect('db_tables/db.db')
#
# cur = con.cursor()
#
# cur.execute("CREATE TABLE bought_items("
#             "name TEXT,"
#             "account TEXT,"
#             "price REAL,"
#             "time INT);")
# #
# cur.execute("CREATE TABLE history("
#             "name TEXT,"
#             "account TEXT,"
#             "buy_price REAL,"
#             "sell_price REAL,"
#             "time INT);")
#
# con.close()


async def delete_all_from_bought_items():
    async with aiosqlite.connect('db_tables/db.db') as db:
        await db.execute("""DELETE FROM bought_items;""")
        await db.commit()


async def get_bought_items():
    async with aiosqlite.connect('db_tables/db.db') as db:
        async with db.execute("SELECT * FROM bought_items") as cur:
            print(await cur.fetchall())


async def get_items():
    async with aiosqlite.connect('db_tables/db.db') as db:
        async with db.execute("SELECT * FROM bought_items;") as cur:
            print(await cur.fetchall())


async def add_bought_item(account: str, market_hash_name: str, price: float):
    async with aiosqlite.connect('db_tables/db.db') as db:
        await db.execute('INSERT INTO bought_items VALUES("{0}", "{1}", {2}, {3});'.format(
            market_hash_name, account, price, time.time()))
        await db.commit()


async def add_sale_info(account, market_hash_name: str, received: float) -> None:
    async with aiosqlite.connect('db_tables/db.db') as db:
        async with db.execute('SELECT * FROM bought_items WHERE account="{0}" AND name="{1}" '
                              'AND time=(SELECT min(time) FROM bought_items);'.format(account, market_hash_name)) as cur:
            item = await cur.fetchone()
        if item is not None:
            await db.execute('DELETE FROM bought_items WHERE account="{0}" AND name="{1}" '
                             'AND time={2};'.format(account, market_hash_name, item[3]))
            await db.execute('INSERT INTO history VALUES("{0}", "{1}", {2}, {3}, {4});'.format(
                item[0], item[1], item[2], received, time.time()
            ))
            await db.commit()


async def get_bought_item_count(market_hash_name: str) -> int:
    async with aiosqlite.connect('db_tables/db.db') as db:
        async with db.execute('SELECT COUNT(*) FROM bought_items WHERE name="{0}" AND '
                              'time<{1};'.format(market_hash_name, time.time() - 172_800)) as cur:
            return (await cur.fetchone())[0]


async def get_bought_item_price(account: str, market_name: str) -> float:
    async with aiosqlite.connect('db_tables/db.db') as db:
        async with db.execute('SELECT * FROM bought_items WHERE name="{0}" AND account="{1}" AND '
                              'time<(SELECT min(time) FROM bought_items);'.format(market_name, account)) as cur:
            item = await cur.fetchone()
            if item is not None:
                return item[2]
            else:
                return 0.0

# print(asyncio.run(get_bought_item_count('Glock-18 | Reactor (Field-Tested)')))
