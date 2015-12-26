import asyncio
import random
import telepot
import dropbox
import tempfile
import shutil
import myconf
import os
import hashlib
from moviepy.editor import VideoFileClip
import datetime

from tgbot.models import RequestedSign
from dictionary.models import BSLEntry
from videolibrary.models import SourceVideo

@asyncio.coroutine
def upload_to_dropbox(file_object, file_name, directory="/bslparlour/videos/tg_uploads/"):
    """A simple function to upload a thing to dropbox."""
    dbox_client = dropbox.client.DropboxClient(myconf.dbox_master_key)
    print("Uploading to dropbox...")
    retval = dbox_client.put_file(
        os.path.join(directory, file_name), file_object)
    print("Uploaded to dropbox...")
    return retval
    

class Charles(telepot.helper.ChatHandler):
    def __init__(self, seed_tuple, timeout):
        super(Charles, self).__init__(seed_tuple, timeout)

    @asyncio.coroutine
    def on_message(self, msg):
        try:
            if msg["text"] == "/requestsign" or msg['text'] == "/tosign":
                yield from self.request_sign(msg)
            elif msg["text"] == "/listsigns":
                yield from self.list_signs(msg)
            elif msg["text"] == "/signwhat":
                yield from self.sign_what(msg)
            elif msg["text"] == "/uploadsign":
                yield from self.upload_sign(msg)
        except KeyError:
            # If there is no "text", just carry on.
            pass

    @asyncio.coroutine
    def fetch_video_from_user(self, video_json, video_file):
        retval = yield from self._bot.downloadFile(video_json["video"]["file_id"], video_file)
        return retval
        
    @asyncio.coroutine
    def upload_sign(self, msg):
        video_json = yield from self.request_info("Send your video!")

        prefix =   datetime.datetime.strftime(
            datetime.datetime.now(),
            "%Y%m%d%H%M%S",
        )
        with tempfile.NamedTemporaryFile(prefix=prefix, suffix=".mp4") as f:
            try:
                yield from self.fetch_video_from_user(video_json, f.file)
            except KeyError:
                yield from self.sender.sendMessage("Sorry, I must recieve a file.")
                return
            
            yield from self.sender.sendMessage("File "+f.name+" recieved!")
            f.seek(0)
            dropbox_json = yield from upload_to_dropbox(f.file, f.name.split("/")[-1])
            yield from self.sender.sendMessage("File "+f.name+" uploaded to Dropbox!")
#             vimeo_json = yield from upload_to_vimeo_and_process(f)
#             
#             source_video = SourceVideo.objects.create(
#                 sha224=hashlib.sha224(f).hexdigest(),
#                 filename=          # from fetch_video_from_user
#                 dropbox_directory= # from dropbox json
#                 mime_type=         # from dropbox json
#                 size=              # from dropbox json
#                 vimeo_uri=         # from vimeo json
#             )
#         yield from self.sender.sendMessage(
#             "Added to Dropbox, Vimeo, and SourceVideo table")
# 
#         gloss = request information
#         # Check for additional gloss
#         # Confirm if gloss already present
#         bsl_entry = BSLEntry.objects.create(
#             # blah blah blah
#         )
#         
#         tweet_entry =           # blah blah


 
    @asyncio.coroutine
    def sign_what(self, msg):
        a = yield from self.request_info("What would you like to know the sign for?")
        a = a["text"]
        try:
            bsl_entry = BSLEntry.objects.get(gloss=a.upper())
        except:
            bsl_entries = BSLEntry.objects.filter(gloss__contains=a.upper())
            bsl_entry = bsl_entries[0]
        yield from self.sender.sendMessage(bsl_entry.gloss)
        source_video = bsl_entry.source_videos.all()[0]
        
        yield from self._bot.sendChatAction(self.chat_id, 'upload_video')

        dbox_client = dropbox.client.DropboxClient(myconf.dbox_master_key)
        temp_dir = tempfile.mkdtemp()
        try:
            f, metadata = dbox_client.get_file_and_metadata(
                os.path.join(
                    source_video.dropbox_directory, 
                    source_video.filename))
            print("Got video path")
            temp_video_file_path = os.path.join(temp_dir, source_video.filename)
            print("Writing file")
            with open(temp_video_file_path, "wb") as out:
                out.write(f.read())
            print("Converting file")
            v = VideoFileClip(temp_video_file_path)
            v.write_videofile(temp_video_file_path+".mp4")
            print("Sending file")
            yield from self.sender.sendVideo(
                open(temp_video_file_path+".mp4", "rb"))
            
        except Exception as e:
            # TODO something clever
            raise(e)
        finally:
            shutil.rmtree(temp_dir)

            
   
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

        return retmsg

    @asyncio.coroutine
    def request_sign(self, msg):
        # TODO make a table in the Django way for the signs left to sign
        try:
            short_description = yield from self.request_info(
                "Which sign would you like to video later?")
            short_description = short_description['text']
            description = yield from self.request_info(
                "Description?")
            description = description['text']
            rs = RequestedSign.objects.create(
                short_description=short_description,
                description=description,)
        except telepot.helper.WaitTooLong:
            yield from self.sender.sendMessage("Request cancelled.")

        yield from self.sender.sendMessage("Sign request logged.")
