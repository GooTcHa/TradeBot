from aiogram import Bot
from aiogram.enums import ParseMode

import config

bot = Bot(config.TG_TOKEN, parse_mode=ParseMode.HTML)


async def send_message(text: str) -> None:
    await bot.send_message(chat_id=config.tg_account_id, text=text)
