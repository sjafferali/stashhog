import os
import sys
import json
import asyncio
import logging as log
import aiohttp
import config
import shutil

from stash import get_scenes, get_scene_file, add_tag_to_scene

TAGS_TO_PROCESS = ["ExternalAIProcessing"]
ERROR_TAGS = ["AI_Errored"]
SUCESS_TAGS = ["AI_Tagged", "AI_TagMe"]
PROCESSING_TAGS = ["AI_Processing"]

def process_scene(scene_data):
    scene_file = get_scene_file(scene_data)
    if not scene_file:
        print(f"File not found for scene {scene_data['title']}")
        return None
    print(f"Processing scene: {scene_data['title']}")
    asyncio.run(process_file(scene_file))
    return scene_file

def process_scenes(limit=1):
    scenes = get_scenes(TAGS_TO_PROCESS)
    successful = []
    total = []
    if not scenes:
        return None
    batch_count = len(scenes)
    if batch_count > int(limit):
        batch_count = limit
    for idx, scene_data in enumerate(scenes[:int(limit)]):
        add_tag_to_scene(scene_data['id'], PROCESSING_TAGS)
    for idx, scene_data in enumerate(scenes[:int(limit)]):
        number = idx + 1
        print(f"Processing {number} of {batch_count} (total {len(scenes)})")
        scene_file = process_scene(scene_data)
        output_file = f"{scene_file}.AI.json"
        scene_id = scene_data['id']
        total.append(scene_id)
        if not scene_file or os.path.exists(output_file):
            add_tag_to_scene(scene_id, SUCESS_TAGS)
            print(f"Tagged scene {scene_id} with {SUCESS_TAGS}.")
            successful.append(scene_id)
        else:
            print("Failed to process scene, skipping")
            add_tag_to_scene(scene_id, ERROR_TAGS)
    print(f"Processed {len(successful)} scenes of {len(total)} attempted scenes out of {len(scenes)} total scenes")


async def post_api_async(session, endpoint, payload):
    url = f'{config.API_BASE_URL}/{endpoint}'
    try:
        async with session.post(url, json=payload) as response:
            if response.status == 200:
                return await response.json()
            else:
                log.error(f"Failed to process {endpoint} status_code: {response.status}")
                return None
    except aiohttp.ClientConnectionError as e:
        log.error(f"Failed to connect to AI server. Is the AI server running at {config.API_BASE_URL}?   {e}")
        raise e


async def process_video_async(video_path, vr_video=False, frame_interval=config.FRAME_INTERVAL,threshold=config.AI_VIDEO_THRESHOLD, return_confidence=True, existing_json=None):
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=config.SERVER_TIMEOUT)) as session:
        return await post_api_async(session, 'process_video/', {"path": video_path, "frame_interval": frame_interval, "threshold": threshold, "return_confidence": return_confidence, "vr_video": vr_video, "existing_json_data": existing_json})


def read_json_from_file(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

def write_json_to_file(file_path, json_data):
    with open(file_path, 'w') as f:
        f.write(json_data)

async def process_file(file_path):
    """
    Processes the given file path and returns the generated JSON result.
    """
    if not os.path.exists(file_path):
        print(f"Error: The file '{file_path}' does not exist.")
        return

    output_file = f"{file_path}.AI.json"

    try:
        # Mock existing JSON data for demonstration purposes.
        existing_json = None
        if os.path.exists(output_file):
            existing_json = read_json_from_file(output_file)

        # Process video and get the result
        result = await process_video_async(
            video_path=file_path,
            existing_json=existing_json
        )

        if result is None:
            print("Error: Failed to process the file.")
            return

        # Parse and print the result
        result_data = result.get('result', {}).get('json_result', {})
        write_json_to_file(output_file, result_data)
        shutil.chown(output_file, user=1050, group=1050)

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python local_file_processor.py [number to process]")
        sys.exit(1)

#    file_path = sys.argv[1]
#    asyncio.run(process_file(file_path))
    process_scenes(sys.argv[1])
