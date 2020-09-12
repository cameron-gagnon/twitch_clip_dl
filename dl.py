#!./venv/bin/python

import hashlib
import os
import re
import requests
import sys
import twitch
import urllib.request
import yaml

import datetime
from time import sleep

config = None
with open('config.yml') as stream:
    try:
        config = yaml.safe_load(stream)
    except yaml.YAMLError as e:
        print("Error parsing yaml config file: {}".format(e))


client_id = config['client_id']
client = twitch.TwitchClient(config['client_id'])
clips = client.clips


channel = 'stroopc'
basepath = '/mnt/e/src/adobe/premiere/twitch/twitch_clips'
# hash of vod_id's to their creation date. Saves looking up the date of the same
# vod several times if there are several clips from the same vod
vod_infos = {}

def dl_progress(count, block_size, total_size):
    percent = int(count * block_size * 100 / total_size)
    sys.stdout.write("\r...%d%%" % percent)
    sys.stdout.flush()

def format_mp4_data(clip):
    thumb_url = clip['thumbnails']['medium']
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
    print("Downloading: {} clips".format(len(channel_clips)))

    for clip in channel_clips:
        full_output_name = generate_filename(clip)
        if not already_downloaded(full_output_name):
            download(clip, full_output_name)
            continue

        full_output_name_dup = generate_filename(clip, iterate=True)
        # needs to be downloaded before we can get its MD5 hash
        download(clip, full_output_name_dup)
        filenames = [file_ for file_ in iterate_filenames(clip)]
        if filenames:
            filenames = filenames[:-1]
        for file_path in filenames:
            if is_duplicate(file_path, full_output_name_dup):
                print("Already downloaded: ", full_output_name_dup, "...removing")
                os.remove(full_output_name_dup)
                break
    print("Downloaded {} clips".format(len(channel_clips)))


def out_filename(clip, i):
    clip_title = clip.title.replace(' ', '_')
    regex = re.compile('[^a-zA-Z0-9_]')
    out_f = regex.sub('', clip_title)
    return "{}_{}.mp4".format(out_f, i)

def full_name_for_clip(clip, i):
    return base_path_for_clip(clip) + out_filename(clip, i)

def base_path_for_clip(clip):
    clip_created_at = vod_created_date(clip)
    game = clip['game']
    # assign the date of the beginning of the week the clip was created. this
    # puts all clips created in the same week under the same folder.
    clip_binned_date = clip_created_at - datetime.timedelta(days=(clip_created_at.weekday()+1) % 7)

    full_path = "{}/{}/{}".format(basepath,
            clip_binned_date.strftime("%m-%d-%Y"), game.lower())

    os.makedirs(full_path, exist_ok=True)

    return full_path + '/'

def vod_created_date(clip):
    global vod_infos
    try:
        vod_id = clip['vod']['id']
    except:
        return datetime.datetime(1980,1,1)

    if not vod_infos.get(vod_id):
        vod_created_at = client.videos.get_by_id(vod_id)['created_at']
        vod_infos[vod_id] = vod_created_at
    return vod_infos[vod_id]

# generates [XXX_0.mp4, ..., XXX_4.mp4] from the clip
def iterate_filenames(clip):
    i = 0
    out_file_to_test = full_name_for_clip(clip, i)
    while already_downloaded(out_file_to_test):
        yield out_file_to_test
        i += 1
        out_file_to_test = full_name_for_clip(clip, i)

def generate_filename(clip, iterate=False):
    i = 0
    if iterate:
        while already_downloaded(full_name_for_clip(clip, i)):
            i += 1

    return full_name_for_clip(clip, i)

def download(clip, full_output_name):
    print("Downloading", full_output_name)
    slug = clip.slug
    mp4_url = format_mp4_data(clip)

    urllib.request.urlretrieve(mp4_url, full_output_name, reporthook=dl_progress)
    print('\nDone.')

def extract_slug(link):
    return link[link.rfind('/')+1:].strip()

def process_clip_link_file(link_file):
    channel_clips = []
    with open(link_file, 'r') as links:
        for link in links:
            clip = clips.get_by_slug(extract_slug(link))
            channel_clips.append(clip)

    return channel_clips


def main():
    durations = ['day', 'week', 'month', 'all']
    duration = durations[1]

    channel_clips = []
    if len(sys.argv) > 1:
        for arg in sys.argv:
            if arg in ['day', 'week', 'month', 'all']:
                channel_clips = clips.get_top(channel='stroopc', limit=100, period=arg)
            elif 'http' in arg:
                channel_clips = [clips.get_by_slug(extract_slug(arg))]
            elif 'twitch_clip_links_all' in arg:
                channel_clips = process_clip_link_file(arg)
                print('processed link file')
        if not channel_clips:
            print("Error, please include twitch link or duration in {}".format(durations))

    download_clips(channel_clips)
    print('Finished downloading all the clips.')


if __name__ == "__main__":
    main()
