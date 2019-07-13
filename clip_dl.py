import os
import re
import requests
import sys
import twitch
import urllib.request
import yaml
from time import sleep

config = None
with open('config.yml') as stream:
    try:
        config = yaml.safe_load(stream)
    except yaml.YAMLError as e:
        print("Error parsing yaml config file: {}".format(e))


client_id = config['client_id']
client = twitch.TwitchClient(client_id=client_id)
clips = client.clips

basepath = 'clips/'
base_clip_path = 'https://clips-media-assets2.twitch.tv/'


def dl_progress(count, block_size, total_size):
    percent = int(count * block_size * 100 / total_size)
    sys.stdout.write("\r...%d%%" % percent)
    sys.stdout.flush()

def retrieve_mp4_data(slug):
    clip_info = requests.get(
        "https://api.twitch.tv/helix/clips?id=" + slug,
        headers={"Client-ID": client_id}).json()

    if clip_info.get('status', '') == 429:
        print(clip_info)
        print("Sleeping 30 seconds...")
        sleep(30)
        return retrieve_mp4_data(slug)

    thumb_url = clip_info['data'][0]['thumbnail_url']
    slice_point = thumb_url.index("-preview-")
    mp4_url = thumb_url[:slice_point] + '.mp4'
    return mp4_url

def already_downloaded(filename):
    return os.path.isfile(filename)

def download_clips(channel="stroopc", cursor=100, limit=100, period="all"):
    channel_clips = clips.get_top(channel=channel, limit=limit, period=period)

    for clip in channel_clips:
        clip_title = clip.title.replace(' ', '_')
        regex = re.compile('[^a-zA-Z0-9_]')
        out_filename = regex.sub('', clip_title) + '.mp4'
        output_path = (basepath + out_filename)

        if already_downloaded(output_path):
            print("Skipping file", clip_title, "already downloaded it")
            continue

        print("Downloading", clip_title, "from:", clip.url)
        slug = clip.slug
        mp4_url = retrieve_mp4_data(slug)

        print('\nDownloading clip slug: ' + slug)
        print('"' + clip_title + '" -> ' + out_filename)
        print(mp4_url)
        urllib.request.urlretrieve(mp4_url, output_path, reporthook=dl_progress)
        print('\nDone.')


def main():
    duration = "all"
    if len(sys.argv) > 1:
        duration = sys.argv[1]
    download_clips(period=duration)
    print('Finished downloading all the videos.')


if __name__ == "__main__":
    main()
