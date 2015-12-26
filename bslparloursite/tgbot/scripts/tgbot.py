# import logging
# logging.basicConfig(level=logging.DEBUG)

import asyncio
import telepot
from telepot.async.delegate import create_open
from telepot.delegate import per_chat_id

from tgbot.charles import Charles

import myconf


def run():
    bot = telepot.async.DelegatorBot(
        myconf.telegram_bot_key,
        [
            (per_chat_id(), create_open(
                Charles,
                timeout=72*3600)),
        ])

    loop = asyncio.get_event_loop()
    loop.create_task(bot.messageLoop())
    loop.run_forever()

if __name__ == "__main__":
    run()
