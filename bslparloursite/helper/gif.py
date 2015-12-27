from subprocess import call
from moviepy.editor import (
    VideoFileClip,
    CompositeVideoClip,
    TextClip,
    ImageClip,
    concatenate
)

# numpy is imported later

from os import listdir
from os.path import expanduser, isfile, getsize, join

import tempfile

import gc

def composite_video(filename, overwrite=False, max_width=720, max_height=720, max_file_size=2.9*1024**2, gifdir='gifs/', logo_path="~/dropbox/bslparlour/twitter_logo2.png"):
    
    print(filename)
    # Just in case the filename is really a file path
    gif_name = join(gifdir, filename.split('/')[-1] + '.gif')
    print(gif_name)

    if isfile(gif_name) and overwrite == False:
        print("Skipping " + gif_name + " as it already exists.")
        return 
    
    video_file = VideoFileClip(filename)

    try:
        # import here to save memory
        from numpy.testing import assert_approx_equal
        assert_approx_equal(float(video_file.w)/float(video_file.h),16.0/9.0)
        video_file = video_file.crop(x1=video_file.w/8, x2=7*video_file.w/8)
    except:
        print("Not resizing video.")

    if video_file.h > max_height:
        video_file = video_file.resize(height=max_height)

    if video_file.w > max_width:
        video_file = video_file.resize(width=max_width)

    end_image = video_file.to_ImageClip(video_file.end-(1/video_file.fps)).set_duration(0.7)
    
    video_file = concatenate([video_file, end_image])
    fadein_video_file = CompositeVideoClip(
        [video_file,
         (video_file.to_ImageClip()
          .set_duration(0.7)
          .crossfadein(0.4)
          .set_start(video_file.duration-0.7)),
     ]
    )
    
    logo_size = video_file.h/6
    text = ImageClip(
        expanduser(logo_path)).set_duration(
            video_file.duration).resize(width=logo_size).set_pos(
                (video_file.w-logo_size,video_file.h-logo_size))


    composite_video_file = CompositeVideoClip([fadein_video_file, text])
    composite_video_file.write_gif(gif_name,fps=20)

    # # Since this function recurs, we must manually clean up the memory hungry things
    # video_file_h = video_file.h
    
    return (gif_name, video_file.h, video_file.w)


def compress_video(gif_name):
    
    # Before trying to create subprocesses, try to free as much memory
    # as possible
    gc.collect()
    
    with tempfile.NamedTemporaryFile() as f:
        print("Trying gifsicle")
        fuzz_amt = 5
        process = call(
            'gifsicle' 
            # ' --conserve-memory "'+gif_name+'" -O3 > '+join(gifdir, "tmp.gif"),
            ' --conserve-memory "'+gif_name+'" -O3 > '+f.name,
            close_fds=True,
            shell=True)

        print("Trying ImageMagick")
        process = call(
            'convert '
            ' -limit map 32MiB -limit memory 32MiB -limit thread 1 -fuzz '+str(fuzz_amt)+'%'
            # ' '+join(gifdir, "tmp.gif")+' '
            ' '+f.name+' '
            ' -ordered-dither o8x8,16'
            ' -layers optimize-transparency "'+gif_name+'"',
            close_fds=True,
            shell=True)
    

def process_video(filename, overwrite=False, max_width=720, max_height=720, max_file_size=2.9*1024**2, gifdir='gifs/', logo_path="~/dropbox/bslparlour/twitter_logo2.png"):

    gif_name, video_file_h, video_file_w = composite_video(filename, overwrite, max_width, max_height, max_file_size, gifdir, logo_path)
    compress_video(gif_name)

    if getsize(gif_name) > max_file_size:
        # TODO make this accept **kwargs or something more change resistant
        process_video(filename,
                      max_height=video_file_h*0.95,
                      overwrite=True,
                      gifdir=gifdir,
                      max_file_size=max_file_size,
                      logo_path=logo_path)



def process_video_tumblr(filename):
    process_video(filename, max_width=540, max_file_size=1.75*1024**2, gifdir='gifs_tumblr/')
    
def process_video_tumblr_half_size(filename):
    process_video(filename, max_width=270, max_file_size=1.75*1024**2, gifdir='gifs_tumblr_half_size/')

def process_folder(path='.'):
    # for i in ['.mp4', '.mov', 'ogv']:
    #     for j in [x for x in listdir('.') if x.find(i) != -1]:
    #         process_video(j)
    #         # process_video_tumblr(j)
    #         # process_video_tumblr_half_size(j)

    from multiprocessing import Pool

    p = Pool(processes=4)
    
    for i in ['.mp4', '.mov', 'ogv']:
        p.map(process_video, [x for x in listdir('.') if x.find(i) != -1])
    #     p.map(process_video_tumblr, [x for x in listdir('.') if x.find(i) != -1])
    #     p.map(process_video_tumblr_half_size, [x for x in listdir('.') if x.find(i) != -1])
