import stashapi.log as log
from stashapi.stashapp import StashInterface
import os.path


stash = StashInterface({
    "scheme": "http",
    "host":"c-eel.local.samir.systems",
    "port": "9999",
    "logger": log
})

def get_scenes(include_tags=[]):
    tags_to_include = stash.map_tag_ids(include_tags)
    scene_data = stash.find_scenes(f={"tags": {"modifier": "INCLUDES_ALL", "value":tags_to_include}})
    return scene_data

def get_scene_file(scene_data):
    for stashfile in scene_data.get("files"):
        filepath = stashfile['path']
        print(filepath)
        if os.path.exists(filepath):
            return filepath
    return None

def add_tag_to_scene(scene_id, tags):
    print(stash.update_scene({"id": scene_id, "tags": tags}))
