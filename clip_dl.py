#!./venv/bin/python

import hashlib
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

channel = 'stroopc'
basepath = '/mnt/e/src/adobe/premiere/twitch/twitch_clips/'

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

    if len(clip_info['data']) == 0:
        print("Couldn't download clip: ", clip_info)
        return
    thumb_url = clip_info['data'][0]['thumbnail_url']
    slice_point = thumb_url.index("-preview-")
    mp4_url = thumb_url[:slice_point] + '.mp4'
    return mp4_url

def already_downloaded(filename):
    return os.path.isfile(filename)

def get_MD5(filename):
    hasher = hashlib.md5()
    with open(filename, 'rb') as in_file:
        buf = in_file.read()
        hasher.update(buf)
    return hasher.hexdigest()

def is_duplicate(out_path, out_path_dup):
    hash1 = get_MD5(out_path)
    hash2 = get_MD5(out_path_dup)
    return hash1 == hash2

def download_clips(channel_clips):
    print(channel_clips)

    for clip in channel_clips:
        out_path, out_f = generate_filename(clip)
        if not already_downloaded(out_path):
            download(clip, out_path, out_f)
            continue

        out_path_dup, out_filename_dup = generate_filename(clip, iterate=True)
        # needs to be downloaded before we can get its MD5 hash
        download(clip, out_path_dup, out_filename_dup)
        filenames = [file_ for file_ in iterate_filenames(clip)]
        if filenames:
            filenames = filenames[:-1]
        for file_path in filenames:
            if is_duplicate(file_path, out_path_dup):
                print("Removing clip: ", out_path_dup, "already downloaded it")
                os.remove(out_path_dup)
                break
            else:
                print("SAME FILES:", file_path, out_path_dup)
    print("Downloaded {} clips".format(len(channel_clips)))


def out_filename(clip):
    clip_title = clip.title.replace(' ', '_')
    regex = re.compile('[^a-zA-Z0-9_]')
    out_f = regex.sub('', clip_title)
    return out_f

# generates [XXX_0.mp4, ..., XXX_4.mp4] from the clip
def iterate_filenames(clip):
    out_f = out_filename(clip)
    i = 0
    out_file_to_test = basepath + out_f + '_{}.mp4'.format(i)
    print('out_file_to_test', out_file_to_test)
    while already_downloaded(out_file_to_test):
        yield out_file_to_test
        i += 1
        out_file_to_test = basepath + out_f + '_{}.mp4'.format(i)

def generate_filename(clip, iterate=False):
    out_f = out_filename(clip)
    i = 0
    if iterate:
        while already_downloaded(basepath + out_f + '_{}.mp4'.format(i)):
            i += 1

    out_f += '_{}.mp4'.format(i)

    out_path = (basepath + out_f)
    return out_path, out_f

def download(clip, out_path, out_f):
    print("Downloading", out_f, "from:", clip.url)
    slug = clip.slug
    mp4_url = retrieve_mp4_data(slug)

    print('\nDownloading clip slug: ' + slug)
    print(out_f, mp4_url)
    urllib.request.urlretrieve(mp4_url, out_path, reporthook=dl_progress)
    print('\nDone.')

def process_clip_link_file(link_file):
    channel_clips = []
    with open(link_file, 'r') as links:
        for link in links:
            clip = clips.get_by_slug(link[link.rfind('/')+1:].strip())
            channel_clips.append(clip)

    return channel_clips

def main():
    durations = ['day', 'week', 'month', 'all']
    duration = durations[1]

    channel_clips = []
    if len(sys.argv) > 1:
        for arg in sys.argv:
            if 'twitch_clip_links_all' in arg:
                channel_clips = process_clip_link_file(arg)
                print('processed link file')
            elif arg in ['day', 'week', 'month', 'all']:
                channel_clips = clips.get_top(channel='stroopc', limit=100, period=arg)
        if not channel_clips:
            print("Error, please include twitch link or duration in {}".format(durations))

    download_clips(channel_clips)
    print('Finished downloading all the videos.')


if __name__ == "__main__":
    main()
