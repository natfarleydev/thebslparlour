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

from django.core.exceptions import MultipleObjectsReturned

import vimeo
from sizefield.utils import parse_size

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
    
@asyncio.coroutine
def upload_to_vimeo(file_name):
    print("Uploading to vimeo...")
    v = vimeo.VimeoClient(
        token=myconf.vimeo_access_token,
        key=myconf.vimeo_client_identifier,
        secret=myconf.vimeo_client_secret
        )
    return v.upload(file_name)
    print("Uploaded to vimeo.")
    

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
    def create_source_video_from_msg(self, video_json):
 
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
            
            yield from self.sender.sendMessage("Processing video...")

            f.seek(0)
            dropbox_json = yield from upload_to_dropbox(f.file, f.name.split("/")[-1])

            vimeo_uri = yield from upload_to_vimeo(f.name)
            
            # TODO add logger stuffs for return things
        
            f.seek(0)
            file_hash = yield from sha224_of_file(f)
                
            source_video = SourceVideo.objects.create(
                sha224=file_hash.hexdigest(),
                filename=f.name.split("/")[-1],
                dropbox_directory="/bslparlour/videos/tg_uploads",
                mime_type=dropbox_json["mime_type"],
                size=parse_size(dropbox_json["size"]),
                vimeo_uri=int(vimeo_uri.split("/")[-1]),
            )

        yield from self.sender.sendMessage(
            "Added to Dropbox, Vimeo, and SourceVideo table")
        
        return source_video

    @asyncio.coroutine
    def send_bsl_entry(self, bsl_entry):
        assert False, "Function not complete!"

    @asyncio.coroutine
    def get_single_bsl_entry_if_any(self, msg):
        """If an entry is present, return it.

           if there are multiple entries, ask the user which to return

        """
        assert False, "Make sure that the user wants to use one of the signs before this function is called."
        try:
            entry = BSLEntry.objects.get(gloss=msg['text'].upper())
        except MultipleObjectsReturned as e:
            entries = BSLEntry.objects.filter(gloss=msg['text'].upper())
            yield from self.sender.sendMessage("Multiple possible duplicates found.")
            for tmp_entry in entries:
                yield from self.send_bsl_entry(tmp_entry)
            
            # make a keyboard of all the duplicates and then ask which
            # of them it should be added to, if any.`
            
            reply_keyboard = [[x.gloss+" "+str(x.gloss_index)] for x in entries]
            add_new_sign_text = "Add new sign"
            reply_keyboard += [add_new_sign_text]
            chosen_to_add = yield from self.request_info(
                "Which would you like to add it to?",
                reply_markup=reply_keyboard)
            if chosen_to_add == add_new_sign_text:
                return
            elif chosen_to_add in [x[0] for x in reply_keyboard]:
                return bsl
                    
            # TODO cancel the keyboard
            yield from self.sender.sendMessage("Added to "+chosen_to_add+".")
            # TODO get the bsl entry from the keyboard reply

        assert False, "Function not complete!"
        
        return entry
        
    @asyncio.coroutine
    def upload_sign(self, msg):
        video_json = yield from self.request_info("Send your video!")
        source_video = yield from self.create_source_video_from_msg(video_json)
        gloss = yield from self.request_info("What's the gloss for this sign?")
        gloss = gloss.upper()
        try:
            gloss_index = max(
                [x.gloss_index for x in BSLEntry.objects.filter(gloss=gloss)]
            ) + 1 
        except ValueError:
            gloss_index = 1

        if gloss_index != 1:
            yield from self.sender.sendMessage("Multiple signs for this gloss detected. You may need to merge some later.")
            for tmp_bsl_entry in BSLEntry.objects.filter(gloss=gloss):
                with tempfile.NamedTemporaryFile() as f:
                    tmp_source_video = tmp_bsl_entry.source_videos[-1]
                    dbox_file, metadata = dbox_client.get_file_and_metadata(
                        os.path.join(
                            tmp_source_video.dropbox_directory, 
                            tmp_source_video.filename))
                    f.write(dbox_file.read())
                    f.seek(0)
                    yield from self.sender.sendVideo(f)
                    
        bsl_entry = BSLEntry.objects.create(
            gloss=gloss,
            gloss_index=gloss_index,
        )
        bsl_entry.source_videos.add(source_video)
        
        # tweet_entry =           # blah blah


 
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
    def request_info(self, prompt, timeout=30, **kwargs):
        yield from self.sender.sendMessage(prompt, kwargs)
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
