import myconf
import tweepy
import logging
import sys
import random
import time
import datetime
import dropbox
import os
import shutil
import tempfile
from helper import gif

from bslbot.models import BSLDictionaryTweet, InfoTweet
from videolibrary.models import SourceVideo
from dictionary.models import BSLEntry

# TODO use some kind of global signature instead of ^bb hardcoded

def tweet_random_info_entry():
    info_tweet = random.choice(InfoTweet.objects.order_by('last_tweeted')[0:2])
    info_tweet.last_tweeted = datetime.datetime.now()
    info_tweet.save()

    tweepy_auth = tweepy.OAuthHandler(
        myconf.consumer_key,
        myconf.consumer_secret,
    )
    tweepy_auth.set_access_token(
        myconf.access_key,
        myconf.access_secret,
    )
    tweepy_api = tweepy.API(tweepy_auth)

    status_to_tweet = info_tweet.tweet
    status_to_tweet += " ^bb"
    tweepy_api.update_status(status=status_to_tweet)


def tweet_random_dict_entry():
    logger = logging.getLogger(__name__)
    logger.addHandler(logging.StreamHandler(stream=sys.stdout))

    tweepy_auth = tweepy.OAuthHandler(
        myconf.consumer_key,
        myconf.consumer_secret,
    )
    tweepy_auth.set_access_token(
        myconf.access_key,
        myconf.access_secret,
    )
    tweepy_api = tweepy.API(tweepy_auth)

    dbox_client = dropbox.client.DropboxClient(myconf.dbox_master_key)

    # bsl_dictionary_tweet = random.choice(BSLDictionaryTweet.objects.order_by('last_tweeted')[0:70])
    # TODO make this more rigourous that exluding the word 'glossed'
    bsl_dictionary_tweet = random.choice((BSLDictionaryTweet.objects
                                          .exclude(tweet__contains='glossed')
                                          .order_by('last_tweeted')[0:30]))
    bsl_dictionary_tweet.last_tweeted = datetime.datetime.now()
    bsl_dictionary_tweet.save()

    bsl_entry = bsl_dictionary_tweet.bsl_entry

    # source_video = SourceVideo.objects.get(sha224=bsl_entry.source_video_sha224)
    source_video = bsl_entry.source_videos.order_by('date_added')[0]

    # Here is where I want to generate a gif instead of getting it from db
    # gif_record = NotSourceVideo.objects.get(source_video=source_video, target_platform='twitter')

    # f, metadata = dbox_client.get_file_and_metadata(
    #     os.path.join(gif_record.dropbox_directory, gif_record.filename))
    # with open(gif_record.filename, 'wb') as out:
    #     out.write(f.read())
    try:
        f, metadata = dbox_client.get_file_and_metadata(
            os.path.join(source_video.dropbox_directory, source_video.filename))
    except dropbox.rest.ErrorResponse as e:
        print(source_video.dropbox_directory)
        raise e

    temp_dir = tempfile.mkdtemp()
    try:
        temp_video_file_path = os.path.join(temp_dir, source_video.filename)

        with open(temp_video_file_path, 'wb') as out:
            out.write(f.read())

        # This function makes a file called temp_video_file_path+'.gif'
        gif.process_video(temp_video_file_path, gifdir=temp_dir, logo_path='~/bslparloursite/scripts/twitter_logo2.png')

        vimeo_url_prefix = "https://vimeo.com/groups/thebslparlour/videos/"

        status_to_tweet = bsl_dictionary_tweet.tweet
        status_to_tweet += " ^bb\n"+vimeo_url_prefix+str(source_video.vimeo_uri)
        tweepy_api.update_with_media(temp_video_file_path+'.gif', status=status_to_tweet)
        # tweepy_api.update_with_media(gif_record.filename, status=status_to_tweet)

    except tweepy.error.TweepError as e:
        # TODO something cleverer here
        print("Path: "+temp_video_file_path+'.gif')
        print("Path exists: "+str(os.path.exists(temp_video_file_path+'.gif')))
        raise e
    finally:
        # os.remove(gif_record.filename)
        # os.remove(temp_video_file_path)
        # os.remove(temp_video_file_path+'.gif')
        # os.rmdir(temp_dir)
        shutil.rmtree(temp_dir)

    print(bsl_dictionary_tweet.tweet, source_video)

def run():
    # time.sleep(random.randint(1,55*60)) # 50 minutes

    randomint = random.randint(0,20)
    if(randomint < 1):
        tweet_random_info_entry()
    else:
        tweet_random_dict_entry()
