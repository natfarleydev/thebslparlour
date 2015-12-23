import asyncio
import telepot
from telepot.async.delegate import create_open
from telepot.delegate import per_chat_id

import myconf

if __name__ == "__main__":
    # Configuration
    bot = telepot.async.DelegatorBot(
        config["telegram_bot_id"],
        [
            (per_chat_id(), create_open(
                # My bot,
                timeout=72*3600)),
        ])

    loop = asyncio.get_event_loop()
    loop.create_task(bot.messageLoop())
    loop.run_forever()
