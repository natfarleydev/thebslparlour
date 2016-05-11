import asyncio
import random
import telepot
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
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


@asyncio.coroutine
def sha224_of_file(f):
    """Return the sha224 of a file."""
    file_hash = hashlib.sha224()
    BUFSIZE = 65536
    buf = f.read(BUFSIZE)
    while len(buf) > 0:
        file_hash.update(buf)
        buf = f.read(BUFSIZE)

    return file_hash



class Charles(telepot.async.helper.ChatHandler):
    def __init__(self, seed_tuple, timeout):
        super(Charles, self).__init__(seed_tuple, timeout)
        self.counter = 0

    async def on_chat_message(self, msg):
        try:
            if msg["text"] == "/requestsign" or msg['text'] == "/tosign":
                await self.request_sign(msg)
            elif msg["text"] == "/counter":
                await self.sender.sendMessage(str(self.counter))
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
                    try:
                        #self.sender.sendDocument(TelegramGif.objects.get(source_video=source_video))
                        TelegramGif.objects.get(source_video=source_video)
                    except TelegramGif.DoesNotExist:
                        dbox_client = dropbox.client.DropboxClient(myconf.dbox_master_key)
                        temp_dir = tempfile.mkdtemp()
                        try:
                            f, metadata = dbox_client.get_file_and_metadata(
                                os.path.join(
                                    source_video.dropbox_directory,
                                    source_video.filename))
                            print("Got video path")
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

                                print("Putting file into RAM")
                                dbox_file = io.BytesIO(f.read())
                                print("Writing file")
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
                            print("Sending file")
                            tg_message = await self.sender.sendDocument(
                                open(temp_gif_path, "rb"))
                            print("File sent")
                            # There is a bizzarre delay if a message is not sent immediately
                            # after the document where the document does not show up until
                            # after the user sends a message. Sending a message fixes this
                            # problem.
                            #await self.sender.sendMessage(bsl_entry.gloss)
                            # await self.sender.sendMessage(str(tg_message))
                            TelegramGif.objects.create(file_id=tg_message['document']['file_id'], source_video=source_video)

                        except dropbox.rest.ErrorResponse:
                            await self.sender.sendMessage(
                                "A record exists, but I can't find the file. Tell @nasfarley88 what you were looking for.")
                        except Exception as e:
                            # TODO something clever
                            await self.sender.sendMessage(
                                    "Sorry, something went wrong.")
                            raise(e)
                        finally:
                            shutil.rmtree(temp_dir)

        except KeyError:
            # If there is no "text", just carry on.
            pass

    async def current_ram_use(self):
        """Returns the current memory use as a string."""
        memory = psutil.virtual_memory()
        await self.sender.sendMessage(
                "{}% used; {} MiB used; {} MiB free.".format(
                    memory.percent,
                    int(memory.used/1024/1024),
                    int(memory.free/1024/1024)))

    async def fetch_video_from_user(self, video_json, video_file):
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

        logging.debug("Entering loop in ask_for_gloss.")
        while True:
            gloss_msg = await self.request_info(
                "Please enter a gloss for this sign.")
            gloss = await self.format_gloss(gloss_msg['text'])

            if should_confirm:
                reply_keyboard = {"keyboard": [["Yes", "No"]]}
                confirm_gloss_msg = await self.request_info(gloss+"\nIs this alright?",
                    reply_markup=reply_keyboard)

            else:
                # If no need to confirm, break immediately after defining.
                break

            if confirm_gloss_msg["text"] == "Yes":
                await self.sender.sendMessage("Gloss "+gloss+" accepted.", reply_markup={"hide_keyboard": True})
                break

        return gloss

    async def send_bsl_entry(self, bsl_entry):
        """Formats a given BSLEntry and then sends it to the user.

        TODO get this function to send a video or animated gif of sign
        (probably animated gif since this plays better and probably
        has better compression to the end user by default).

        """
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
                reply_keyboard = [[i.gloss+" "+str(i.gloss_index)] for i in bsl_entries_with_gloss]
                reply_keyboard.append(["Add new"])
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

        prefix = datetime.datetime.strftime(
            datetime.datetime.now(),
            "%Y%m%d%H%M%S",
        )
        with tempfile.NamedTemporaryFile(prefix=prefix, suffix=".mp4") as f:
            try:
                await self.fetch_video_from_user(video_json, f.file)
            except KeyError:
                await self.sender.sendMessage("Sorry, I must recieve a file.")
                return

            reply_keyboard = {"keyboard": [["Yes", "No"]]}
            confirm_gloss_msg = await self.request_info("Is this alright?",
                reply_markup=reply_keyboard)
            if confirm_gloss_msg['text'] == "No":
                raise Exception("TODO replace this with proper flow control!!")

            await self.sender.sendMessage("Processing video...")

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

        await self.sender.sendMessage(
            "Added to Dropbox, Vimeo, and SourceVideo table")

        return source_video


    async def create_bsl_dictionary_tweet(self, bsl_entry):
        """Creates an automatic entry in the BSLDictionaryTweet table."""

        logging.debug("Entering tweet into database.")
        tweet = BSLDictionaryTweet.objects.create(
            tweet = "This sign could be glossed "+bsl_entry.gloss+".",
            suggested_tweet = "This sign could be glossed "+bsl_entry.gloss+".",
            bsl_entry=bsl_entry,
            last_tweeted=datetime.datetime(1970,1,1),
        )
        return tweet


    async def upload_sign(self, msg):
        video_json = await self.request_info("Send your video!")
        source_video = await self.create_source_video_from_msg(video_json)

        # create_or_append_to_bsl_entry asks for a gloss if none is provided
        bsl_entry = await self.create_or_append_to_bsl_entry(source_video)
        tweet_entry = await self.create_bsl_dictionary_tweet(bsl_entry)

        await self.sender.sendMessage("Tweet, BSLEntry, SourceVideo entered! Happy learning!")

#         gloss = await self.request_info("What's the gloss for this sign?")
#         gloss = gloss.upper()
#         try:
#             gloss_index = max(
#                 [x.gloss_index for x in BSLEntry.objects.filter(gloss=gloss)]
#             ) + 1
#         except ValueError:
#             gloss_index = 1
#
#         if gloss_index != 1:
#             await self.sender.sendMessage("Multiple signs for this gloss detected. You may need to merge some later.")
#             for tmp_bsl_entry in BSLEntry.objects.filter(gloss=gloss):
#                 with tempfile.NamedTemporaryFile() as f:
#                     tmp_source_video = tmp_bsl_entry.source_videos[-1]
#                     dbox_file, metadata = dbox_client.get_file_and_metadata(
#                         os.path.join(
#                             tmp_source_video.dropbox_directory,
#                             tmp_source_video.filename))
#                     f.write(dbox_file.read())
#                     f.seek(0)
#                     await self.sender.sendVideo(f)
#
#         bsl_entry = BSLEntry.objects.create(
#             gloss=gloss,
#             gloss_index=gloss_index,
#         )
#         bsl_entry.source_videos.add(source_video)
#
        # tweet_entry =           # blah blah



    # TODO there is probably a leak in this function, the tg bot was taking up a lot of RAM after a while. This should be checked!
    async def sign_what(self, msg):
        a = await self.request_info(
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
                await self.sender.sendMessage(
                        "I'm sorry, I don't have one on file for that.")
                return
        await self.sender.sendMessage(
                "I have something on record for "+bsl_entry.gloss+". One moment..")
        source_video = bsl_entry.source_videos.all()[0]

        await self._bot.sendChatAction(self.chat_id, 'upload_video')

        try:
            tg_gif = TelegramGif.objects.get(source_video=source_video)
            ret_msg = await self.sender.sendDocument(tg_gif.file_id)
            await self.sender.sendMessage(tg_gif.file_id)
            await self.sender.sendMessage(str(ret_msg))
            return
        except TelegramGif.DoesNotExist:
            # Carry on with the rest of the function
            # TODO rework the flow of this function
            pass

        dbox_client = dropbox.client.DropboxClient(myconf.dbox_master_key)
        temp_dir = tempfile.mkdtemp()
        try:
            f, metadata = dbox_client.get_file_and_metadata(
                os.path.join(
                    source_video.dropbox_directory,
                    source_video.filename))
            print("Got video path")
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

                print("Putting file into RAM")
                dbox_file = io.BytesIO(f.read())
                print("Writing file")
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
            print("Sending file")
            tg_message = await self.sender.sendDocument(
                open(temp_gif_path, "rb"))
            print("File sent")
            # There is a bizzarre delay if a message is not sent immediately
            # after the document where the document does not show up until
            # after the user sends a message. Sending a message fixes this
            # problem.
            await self.sender.sendMessage(bsl_entry.gloss)
            # await self.sender.sendMessage(str(tg_message))
            TelegramGif.objects.create(file_id=tg_message['document']['file_id'], source_video=source_video)

        except Exception as e:
            # TODO something clever
            await self.sender.sendMessage(
                    "Sorry, something went wrong.")
            raise(e)
        finally:
            shutil.rmtree(temp_dir)



    async def list_signs(self, msg):
        await self.sender.sendMessage(
            "\n".join(
                [str(x) for x in RequestedSign.objects.all()]))

    async def request_info(self, prompt, timeout=30, **kwargs):
        logging.debug("kwargs for request_info: "+str(kwargs))
        await self.sender.sendMessage(prompt, **kwargs)
        logging.info("Message sent: "+prompt)
        l = self._bot.create_listener()
        l.set_options(timeout=timeout)
        l.capture(chat__id=self.chat_id)
        retmsg = await l.wait()

        return retmsg

    async def request_sign(self, msg):
        # TODO make a table in the Django way for the signs left to sign
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
            await self.sender.sendMessage("Request cancelled.")

        await self.sender.sendMessage("Sign request logged.")
