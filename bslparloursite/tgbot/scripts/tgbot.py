# import logging
# logging.basicConfig(level=logging.DEBUG)

import asyncio
import os
import telepot
from telepot.async.delegate import per_chat_id, create_open

from tgbot.charles import Charles

import myconf


def run():
    if os.path.exists("tgbot.lock"):
        print("raising exception")
        raise Exception("Lockfile still present.")

    try:
        lockfile = open("tgbot.lock", "w+")
        lockfile.write("")
        bot = telepot.async.DelegatorBot(
            myconf.telegram_bot_key,
            [
                (per_chat_id(), create_open(
                    Charles,
                    timeout=360)),
            ])

        loop = asyncio.get_event_loop()
        loop.create_task(bot.message_loop())
        loop.run_forever()
    finally:
        lockfile.close()
        os.remove("tgbot.lock")

if __name__ == "__main__":
    run()
