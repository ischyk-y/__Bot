import logging
import asyncio

from aiogram import Bot, Dispatcher

from handlers import chat_join_request

from database.database import Database
from database.redis_database import RedisDatabase

dp = Dispatcher()

db = Database()
redis_db = RedisDatabase()


async def bot(token) -> None:
    bot = Bot(token=token)

    dp.include_routers(chat_join_request.router)

    await dp.start_polling(bot)


async def main() -> None:
    tasks = [
        asyncio.create_task(bot(token)) for token in ['5879332067:AAEUJTNg0m9m5nj766cxH89bdAiJ8xnLPio']
    ]
    await asyncio.gather(*tasks)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
