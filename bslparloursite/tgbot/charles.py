import asyncio
import telepot

from tgbot.models import RequestedSign

class Charles(telepot.helper.ChatHandler):
    def __init__(self, seed_tuple, timeout):
        super(Charles, self).__init__(seed_tuple, timeout)

    @asyncio.coroutine
    def on_message(self, msg):
        if msg['text'] == "/sign":
            yield from self.request_sign(msg)
        elif msg['text'] == "/listsigns":
            yield from self.list_signs(msg)
   
    @asyncio.coroutine
    def list_signs(self, msg):
        yield from self.sender.sendMessage(
            "\n".join(
                [str(x) for x in RequestedSign.objects.all()]))

    @asyncio.coroutine
    def request_info(self, prompt, timeout=30):
        yield from self.sender.sendMessage(prompt)
        l = self._bot.create_listener()
        l.set_options(timeout=timeout)
        l.capture(chat__id=self.chat_id)
        retmsg = yield from l.wait()

        return retmsg['text']

    @asyncio.coroutine
    def request_sign(self, msg):
        # TODO make a table in the Django way for the signs left to sign
        try:
            gloss = yield from self.request_info(
                "Which sign would you like to video later?")
            description = yield from self.request_info(
                "Description?")
            rs = RequestedSign.objects.create(
                gloss=gloss,
                description=description,)
        except telepot.helper.WaitTooLong as e:
            yield from self.sender.sendMessage("Request cancelled.")

        yield from self.sender.sendMessage("Sign request logged.")
