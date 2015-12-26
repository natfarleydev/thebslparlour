import vimeo
import yaml
import os
import re

def setup_vimeo_client():
    credentials = yaml.load(open(os.path.expanduser("~/.interactive-vimeo"), "rb"))
    v = vimeo.VimeoClient(
        token=credentials["access_token"],
        key=credentials["client_identifier"],
        secret=credentials["client_secret"]
        )
    
    # Make the request to the server for the "/me" endpoint.
    about_me = v.get('/me')
    assert about_me.status_code == 200

    return v


v = setup_vimeo_client()

def upload_video(filename):
    uri = v.upload_video(filename)

    return uri
    
def rename_video(video_id, name):
    """Easy way to rename a video."""
    return v.patch(video_id, data={"name" : name })

def rename_with_regex(video_id, regex, subst):
    video_name = v.get(video_id).json()["name"]
    subst_video_name = re.sub(regex, subst, video_name)
    if subst_video_name != video_name:
        print("Substituting "+video_name+" for "+subst_video_name+".")
        return rename_video(video_id, subst_video_name)
    else:
        print("No substitution for "+video_name+".")

def remove_file_ext(video_id):
    """Removes file extensions from Vimeo video names."""
    return rename_with_regex(video_id, r"\.\w{3}$", "")

# Really, I want this to be a generator
def all_my_videos(per_page=25):
    """Generator for all videos.

    First, the function fetches the first page, and yields all results
from that page. Then it iterates to the next page, and yields results
from that. When all pages are exhausted, the generator completes.  """
    current_page = v.get("/me/videos", params={"page":1, "per_page":per_page})
    while current_page.json()["paging"]["next"]:
        for i in current_page.json()["data"]:
            yield i
        current_page = v.get(current_page.json()["paging"]["next"])
    

