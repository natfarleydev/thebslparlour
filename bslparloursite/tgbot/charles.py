import asyncio
import random
import telepot
from telepot.namedtuple import ReplyKeyboardMarkup
import dropbox
import tempfile
import shutil
import myconf
import os
import hashlib
import logging
import subprocess
import io
import pathlib
import psutil
from moviepy.editor import VideoFileClip
import datetime

from django.core.exceptions import MultipleObjectsReturned

import vimeo
from sizefield.utils import parse_size

from tgbot.models import RequestedSign, TelegramGif
from dictionary.models import BSLEntry
from videolibrary.models import SourceVideo
from bslbot.models import BSLDictionaryTweet

logging.basicConfig(level=logging.DEBUG)

async def upload_to_dropbox(file_object, file_name, directory="/bslparlour/videos/tg_uploads/"):
    """A simple function to upload a thing to dropbox."""
    dbox_client = dropbox.client.DropboxClient(myconf.dbox_master_key)
    logging.info("Uploading to dropbox...")
    retval = dbox_client.put_file(
        os.path.join(directory, file_name), file_object)
    logging.info("Uploaded to dropbox.")
    return retval

async def upload_to_vimeo(file_name):
    logging.info("Uploading to vimeo...")
    v = vimeo.VimeoClient(
        token=myconf.vimeo_access_token,
        key=myconf.vimeo_client_identifier,
        secret=myconf.vimeo_client_secret
        )
    logging.info("Uploaded to vimeo.")
    return v.upload(file_name)


async def sha224_of_file(f):
    """Return the sha224 of a file."""
    file_hash = hashlib.sha224()
    BUFSIZE = 65536
    buf = f.read(BUFSIZE)
    while len(buf) > 0:
        file_hash.update(buf)
        buf = f.read(BUFSIZE)

    return file_hash


# TODO put these up top
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
from telepot.namedtuple import InlineQueryResultArticle, InlineQueryResultPhoto, InputTextMessageContent, InlineQueryResultCachedGif

class Charles(telepot.async.SpeakerBot):
    def __init__(self, *args, **kwargs):
        super(Charles, self).__init__(*args, **kwargs)
        self.counter = 0
        self._answerer = telepot.async.helper.Answerer(self)


    def on_inline_query(self, msg):
        def compute():
            query_id, from_id, query_string = telepot.glance(msg, flavor='inline_query')
            if query_string == "":
                return []

            bsl_entries = BSLEntry.objects.filter(gloss__regex=query_string.upper())
            if not bsl_entries:
                return []

            entries = []
            for i, bsl_entry in enumerate(bsl_entries):
                try:
                    tg_gif = TelegramGif.objects.get(
                        source_video=bsl_entry.source_videos.first())
                    entries.append(InlineQueryResultCachedGif(
                        id=str(i),
                        gif_file_id=tg_gif.file_id,
                        title=bsl_entry.gloss,
                        caption=bsl_entry.gloss
                    ))
                except TelegramGif.DoesNotExist:
                    pass        # TODO make this meaningful like creating one or sth
                if i == 30: break

            return entries

        self._answerer.answer(msg, compute)

    def on_chosen_inline_result(self, *args, **kwargs):
        """Dummy function, used monitoring chosen results. """
        return

    async def on_chat_message(self, msg):

        self.mic.send(msg)

        if "text" not in msg:
            return

        if msg["text"] == "/requestsign" or msg['text'] == "/tosign":
            await self.request_sign(msg)
        elif msg["text"] == "/counter":
            await self.sendMessage(str(self.counter))
        elif msg["text"] == "/listsigns":
            await self.list_signs(msg)
        elif "/signwhat" in msg["text"]:
            await self.sign_what(msg)
        # elif msg["text"] == "/uploadsign":
        elif "/uploadsign" in msg["text"]:
            await self.upload_sign(msg)
        elif msg["text"] == "/ramusage":
            await self.current_ram_use()
        elif msg["text"] == "/fillcache":
            for source_video in SourceVideo.objects.all():
                await self.send_source_video_as_gif(source_video)

    async def current_ram_use(self):
        content_type, chat_type, chat_id = telepot.glance(msg)
        """Returns the current memory use as a string."""
        memory = psutil.virtual_memory()
        await self.sendMessage(
            chat_id,
            "{}% used; {} MiB used; {} MiB free.".format(
                memory.percent,
                int(memory.used/1024/1024),
                int(memory.free/1024/1024)))

    async def fetch_video_from_user(self, video_json, video_file):
        assert False, "Function needs updating to SpeakerBot"
        retval = await self._bot.downloadFile(video_json["video"]["file_id"], video_file)
        return retval

    async def format_gloss(self, text):
        """Attempts to reformat text into a gloss format.

        (e.g. don't know -> DON'T-KNOW).

        """

        gloss = text.upper().replace(" ", "-")
        logging.debug("Gloss formatted from "+text+" to "+gloss+".")
        return gloss


    async def ask_for_gloss(self, should_confirm=True):
        """Asks for a gloss from a user.

        Attempts to format input from the user (e.g. don't know ->
        DON'T-KNOW). By default, confirms input from user.

        """

        assert False, "Function needs updating to SpeakerBot"
        logging.debug("Entering loop in ask_for_gloss.")
        while True:
            gloss_msg = await self.request_info(
                "Please enter a gloss for this sign.")
            gloss = await self.format_gloss(gloss_msg['text'])

            if should_confirm:
                reply_keyboard = ReplyKeyboardMarkup(keyboard=[["Yes", "No"]], one_time_keyboard=True)
                confirm_gloss_msg = await self.request_info(gloss+"\nIs this alright?",
                    reply_markup=reply_keyboard)

            else:
                # If no need to confirm, break immediately after defining.
                break

            if confirm_gloss_msg["text"] == "Yes":
                await self.sendMessage("Gloss "+gloss+" accepted.")
                break

        return gloss

    async def send_bsl_entry(self, bsl_entry):
        """Formats a given BSLEntry and then sends it to the user.

        TODO get this function to send a video or animated gif of sign
        (probably animated gif since this plays better and probably
        has better compression to the end user by default).

        """
        assert False, "Maybe this function needs deleting?"
        # TODO get this to send a video
        ret_str = bsl_entry.gloss+" "+str(bsl_entry.gloss_index)
        return ret_str

    async def create_or_append_to_bsl_entry(self, source_video, gloss=None, bsl_entry=None):
        """Creates or appends the given source video to a BSLEntry.

        If gloss is None, this function fetches the gloss from the
        user, otherwise it uses the gloss provided.

        If bsl_entry is None, this function attempts to make smart
        choices about whether to add to an existing entry or create a
        new one (mostly by asking the user). If there are no matching
        BSLentrys, it creates a new one immediately.

        """
        assert False, "Function needs updating to SpeakerBot"


        if gloss == None:
            gloss = await self.ask_for_gloss()
        elif isinstance(gloss, str):
            gloss = await self.format_gloss(gloss)
        else:
            assert False, "gloss keyword argument must be str or None."

        # if bsl_entry is yet to be defined, the program makes an
        # educated guess by consulting the user or creating an entry.
        if bsl_entry == None:
            bsl_entries_with_gloss = BSLEntry.objects.filter(gloss=gloss)
            if len(bsl_entries_with_gloss) == 0:
                bsl_entry = BSLEntry.objects.create(
                    gloss=gloss,
                    gloss_index=1
                )
            else:
                for i in bsl_entries_with_gloss:
                    self.send_bsl_entry(i)
                reply_keyboard = ReplyKeyboardMarkup(
                    keyboard=[[i.gloss+" "+str(i.gloss_index)] for i in bsl_entries_with_gloss]+[["Add new"]])
                bsl_entry_to_add_to = self.request_info(
                    "Which BSLEntry should this be added to (if any)?",
                    reply_markup=reply_keyboard)
                if bsl_entry_to_add_to == "Add new":
                    next_gloss_index = max([x.gloss_index for x in bsl_entries_with_gloss])+1
                    bsl_entry = BSLEntry.objects.create(
                        gloss=gloss,
                        gloss_index=next_gloss_index
                    )

        bsl_entry.source_videos.add(source_video)
        return bsl_entry

    async def create_source_video_from_msg(self, video_json):
        """Creates source video given an uploaded video from Telegram.

        Returns SourceVideo.

        This function automatically uploads the telegram video to
        Dropbox and Vimeo, calculates the hash of the file and
        generally fills in all details needed for a SourceVideo entry.

        """
        assert False, "Function needs updating to SpeakerBot"

        prefix = datetime.datetime.strftime(
            datetime.datetime.now(),
            "%Y%m%d%H%M%S",
        )
        with tempfile.NamedTemporaryFile(prefix=prefix, suffix=".mp4") as f:
            try:
                await self.fetch_video_from_user(video_json, f.file)
            except KeyError:
                await self.sendMessage("Sorry, I must recieve a file.")
                return

            reply_keyboard = ReplyKeyboardMarkup(keyboard=[["Yes", "No"]], one_time_keyboard=True)
            confirm_gloss_msg = await self.request_info("Is this alright?",
                reply_markup=reply_keyboard)
            if confirm_gloss_msg['text'] == "No":
                raise Exception("TODO replace this with proper flow control!!")

            await self.sendMessage("Processing video...")

            f.seek(0)
            dropbox_json = await upload_to_dropbox(f.file, f.name.split("/")[-1])

            vimeo_uri = await upload_to_vimeo(f.name)

            f.seek(0)
            file_hash = await sha224_of_file(f)


            source_video = SourceVideo.objects.create(
                sha224=file_hash.hexdigest(),
                filename=f.name.split("/")[-1],
                dropbox_directory="/bslparlour/videos/tg_uploads",
                mime_type=dropbox_json["mime_type"],
                size=parse_size(dropbox_json["size"]),
                vimeo_uri=int(vimeo_uri.split("/")[-1]),
            )

        await self.sendMessage(
            "Added to Dropbox, Vimeo, and SourceVideo table")

        return source_video


    async def create_bsl_dictionary_tweet(self, bsl_entry):
        """Creates an automatic entry in the BSLDictionaryTweet table."""
        assert False, "Function needs updating to SpeakerBot"

        logging.debug("Entering tweet into database.")
        tweet = BSLDictionaryTweet.objects.create(
            tweet = "This sign could be glossed "+bsl_entry.gloss+".",
            suggested_tweet = "This sign could be glossed "+bsl_entry.gloss+".",
            bsl_entry=bsl_entry,
            last_tweeted=datetime.datetime(1970,1,1),
        )
        return tweet


    async def upload_sign(self, msg):
        assert False, "Function needs updating to SpeakerBot"
        video_json = await self.request_info("Send your video!")
        source_video = await self.create_source_video_from_msg(video_json)

        # create_or_append_to_bsl_entry asks for a gloss if none is provided
        bsl_entry = await self.create_or_append_to_bsl_entry(source_video)
        tweet_entry = await self.create_bsl_dictionary_tweet(bsl_entry)

        await self.sendMessage("Tweet, BSLEntry, SourceVideo entered! Happy learning!")


    async def send_source_video_as_gif(self, chat_id, source_video):
        """Send a source_video as a gif.

        If possible, uses TelegramGif entry to use cached gif rather than
        create and send a new one.

        """
        await self.sendChatAction(chat_id, 'upload_video')

        try:
            # If there is a gif on record, send that one.
            tg_gif = TelegramGif.objects.get(source_video=source_video)
            await self.sendDocument(chat_id, tg_gif.file_id)
            return
        except TelegramGif.DoesNotExist:
            # Carry on with the rest of the function
            pass

        # Get the video file, make it a gif and send it
        dbox_client = dropbox.client.DropboxClient(myconf.dbox_master_key)
        temp_dir = tempfile.mkdtemp()
        try:
            f, metadata = dbox_client.get_file_and_metadata(
                os.path.join(
                    source_video.dropbox_directory,
                    source_video.filename))
            video_path = pathlib.Path(
                    os.path.expanduser( "~/dropbox"+metadata['path']))
            if video_path.is_file():
                print("Using cached file")
            else:
                print("Getting file")
                # Get the directory
                video_dir = pathlib.Path("/".join(str(video_path).split('/')[:-1]))
                try:
                    video_dir.mkdir(parents=True)
                except FileExistsError:
                    pass

                # Putting file into RAM
                dbox_file = io.BytesIO(f.read())
                # Writing file
                with video_path.open("wb") as out:
                    out.write(dbox_file.read())

            video_filename = os.path.basename(str(video_path))
            temp_gif_path = os.path.join(temp_dir, video_filename)+".gif"
            subprocess.check_call(
                    ["ffmpeg",
                    "-i",
                    str(video_path),
                    "-vf",
                    "scale=450:-1",
                    # "scale=250:-1",
                    temp_gif_path,])
            # Sending file
            tg_message = await self.sendDocument(
                chat_id,
                open(temp_gif_path, "rb"))
            TelegramGif.objects.create(file_id=tg_message['document']['file_id'], source_video=source_video)

        except Exception as e:
            # TODO something clever
            await self.sendMessage(
                chat_id,
                "Sorry, something went wrong with sending a video.")
            raise(e)
        finally:
            shutil.rmtree(temp_dir)

    async def sign_what(self, msg):
        content_type, chat_type, chat_id = telepot.glance(msg)
        a = await self.request_info(
            chat_id,
            "What would you like to know the sign for?")
        a = a["text"]
        try:
            logging.debug("Attempting to get single entry.")
            bsl_entry = BSLEntry.objects.get(gloss=a.upper())
        except:
            logging.debug("Failed to get single entry.")
            logging.debug("Attempting to get similar matches.")
            bsl_entries = BSLEntry.objects.filter(gloss__contains=a.upper())
            try:
                bsl_entry = bsl_entries[0]
            except IndexError:
                await self.sendMessage(
                        "I'm sorry, I don't have one on file for that.")
                return
        await self.sendMessage(
            chat_id,
            "I have something on record for "+bsl_entry.gloss+". One moment..")
        source_video = bsl_entry.source_videos.all()[0]

        await self.sendChatAction(chat_id, 'upload_video')

        await self.send_source_video_as_gif(chat_id, source_video)


    async def list_signs(self, msg):
        await self.sendMessage(
            "\n".join(
                [str(x) for x in RequestedSign.objects.all()]))

    async def request_info(self, chat_id, prompt, timeout=30, **kwargs):
        logging.debug("kwargs for request_info: "+str(kwargs))
        await self.sendMessage(chat_id, prompt, **kwargs)
        logging.info("Message sent: "+prompt)
        listener = self.create_listener()
        # l.set_options(timeout=timeout)
        listener.capture(chat__id=chat_id)
        retmsg = await listener.wait()

        return retmsg

    async def request_sign(self, msg):
        try:
            short_description = await self.request_info(
                "Which sign would you like to video later?")
            short_description = short_description['text']
            description = await self.request_info(
                "Description?")
            description = description['text']
            rs = RequestedSign.objects.create(
                short_description=short_description,
                description=description,)
        except telepot.helper.WaitTooLong:
            await self.sendMessage("Request cancelled.")

        await self.sendMessage("Sign request logged.")
