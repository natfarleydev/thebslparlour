import asyncio
import telepot

class Charles(telepot.helper.ChatHandler):
    def __init__(self, seed_tuple, timeout):
        super(Charles, self).__init__(seed_tuple, timeout)

    @asyncio.coroutine
    def on_message(self, msg):
        if msg['text'] == "/tosign":
            yield from to_sign(msg)
        yield from self.sender.sendMessage(msg['text'])

    @asyncio.coroutine
    def to_sign(self, msg):
        # TODO make a table in the Django way for the signs left to sign
        pass
