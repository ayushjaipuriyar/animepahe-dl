#!/usr/bin/env python3

import argparse
import http
import json
import logging
import math
import os
import re
import shutil
import subprocess
import threading
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from Crypto.Cipher import AES
from pyfzf.pyfzf import FzfPrompt
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from tqdm import tqdm

fzf = FzfPrompt()
max = 1
script_path = os.getcwd()
script_path = '/home/ayush/Videos/Anime'
s = requests.session()


def verbose():
    http.client.HTTPConnection.debuglevel = 1
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True


retry_strategy = Retry(
    total=3,
    backoff_factor=2,
    status_forcelist=[429, 500, 502, 503, 504],
)
adapter = HTTPAdapter(max_retries=retry_strategy)
s.mount("https://", adapter)
s.mount("http://", adapter)
headers = {
    "Referer": "https://kwik.cx/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "Connection": "Keep-Alive",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36"
}


def get_path(anime_name):
    """Returns the required path by an anime

    Args:
        anime_name (str): Name of the anime

    Returns:
        string: Path where the anime will be stored
    """
    path = script_path+'/'+anime_name_folder(anime_name)
    return path


def anime_name_folder(anime_name):
    """Returns the folder name replacing the invalid characters with _
        Should work for windows and unix devices

    Args:
        anime_name (str): Name of the anime

    Returns:
        string: The name of the folder after replacing invalid characters with _
    """
    temp = anime_name
    temp = temp.replace('/', '_')
    temp = temp.replace('<', '_')
    temp = temp.replace('>', '_')
    temp = temp.replace(':', '_')
    temp = temp.replace('\\', '_')
    temp = temp.replace('?', '_')
    temp = temp.replace('|', '_')
    temp = temp.replace('*', '_')
    return temp


def get_path_episode_folder(anime_name, episode):
    """Returns the required path for further processing when multithreading
       Folder to save the segments into
    Args:
        anime_name (str): Name of the anime
        episode (Integer): Episode to be downloaded

    Returns:
        string:Returns the path to the folder according to the episode number
    """
    path = get_path(anime_name)+"/"+str(episode)+"/"
    return path


def get_video_episode(anime_name, episode):
    """Returns the name of the video to be downloaded with path

    Args:
        anime_name (str): Name of the anime
        episode (Integer): Episode to be downloaded

    Returns:
        path: Return the path with the name of the file to be downloaded
    """
    global max
    name = get_path(anime_name)+"/"+anime_name + " Episode " + \
        str(episode).zfill(int(math.log10(max))+2)+".mp4"

    return name


def download_anime_list():
    """Parse animepahe.com/anime to retrieve all the anime with their UUIDs
    """
    # res = 'https://animepahe.com/anime'
    # response = req(res)
    try:
        response = requests.get('https://animepahe.com/anime/')
        response.raise_for_status()
    except requests.exceptions.RequestException as err:
        print(f"Error: {err}")
        quit()
    # Parsing the the request sent
    soup = BeautifulSoup(response.content, 'html.parser')
    divContainer = soup.find_all("div", {"class": "tab-content"})
    # Storing them to the file
    f = open('animelist.txt', 'w')
    for tag in divContainer:
        for tags in tag.find_all("a"):
            uuid = tags.attrs['href'].removeprefix('/anime/')
            name = tags.text.strip()
            f.write("{}::::{}".format(uuid, name))
            f.write("\n")
    f.close()


def add_anime_to_myanimelist(anime_name):
    """Adds an anime name to the myanimelist file, after prompting the user to confirm"""
    print("Do you want to add {} to myanimelist.txt? (y/n)".format(anime_name))
    response = input().strip().lower()
    if response == 'y':
        with open(os.path.join(script_path, 'myanimelist.txt'), 'a+', encoding='utf-8') as f:
            f.seek(0)
            if anime_name in f.read():
                print(f"{anime_name} already added")
            else:
                f.write(f"{anime_name}\n")
                print(f"{anime_name} added to myanimelist.txt")
    else:
        print(f"{anime_name} not added to myanimelist.txt")


def search_anime_name(name=""):
    """Search from the earlier created anime list
        And write those name for future auto downloading

    Returns:
        list: This lst contains the anime_slug and anime_name, anime UUID and anime name respectively
    """
    if name != "":
        name = name.replace(' ', '%20')
        res = 'https://animepahe.com/api?m=search&q={}'.format(name)
        try:
            response = requests.get(res)
            response.raise_for_status()
        except requests.exceptions.RequestException as err:
            print(f"Error: {err}")
            quit()
        data = response.json()['data']
        anime_list = []
        for element in data:
            uuid = element['session']
            anime_name = element['title']
            anime_list.append("{}::::{}".format(uuid, anime_name))
        result = fzf.prompt(anime_list)[0]
        anime_slug, anime_name, _ = result.split('::::')
    else:
        anime_list = open("animelist.txt").readlines()
        result = fzf.prompt(anime_list)
        # Select your desired anime to download
        anime_slug, anime_name, _ = result.strip().split('::::')
    # Writing to anime names to the
    add_anime_to_myanimelist(anime_name)
    return anime_name, anime_slug


def get_source_file(anime_name, anime_slug):
    """Retrieve the episode list

    Args:
        anime_name (str): Name of the anime
        anime_slug (str): UUID of the anime
    """
    print("Getting list of episodes for {}".format(anime_name))
    session = requests.session()
    try:
        response = session.get(
            "https://animepahe.com/api?m=release&id={}".format(anime_slug))
        response.raise_for_status()
    except requests.exceptions.RequestException as err:
        print("OOps: Something Else", err)
        quit()

    pages = json.loads(response.text)['last_page']
    episode_list = []
    # Running for all the pages possible to have the links for the episodes
    for page in range(1, pages+1):
        try:
            response = session.get(
                "https://animepahe.com/api?m=release&id={}&sort=episode_asc&page={}".format(anime_slug, i))
            response.raise_for_status()
        except requests.exceptions.RequestException as err:
            print("OOps: Something Else", err)
            quit()
        data = response.json()["data"]
        episode_list.extend(data)

    path = get_path(anime_name)
    # Checking if there exists a folder for the anime if not create one
    os.makedirs(path, exist_ok=True)
    # Writing to the source file of that anime
    source_data = {"data": episode_list}
    with open("{}/.source.json".format(path), "w") as f:
        json.dump(source_data, f)


def select_episode_to_download(anime_name):
    """Select episodes to download

    Args:
        anime_name (str): Name of the anime

    Returns:
        list: List of all the episodes to download
    """
    global max
    path = get_path(anime_name)
    print("Download location ", path)
    with open("{}/.source.json".format(path), 'r') as f:
        data = json.load(f)['data']
    max = data[-1]['episode']
    print("Episodes available {}".format(max))
    for element in data:
        print("Episode {}".format(element['episode']))
    while True:
        episodes_input = input(
            "Enter the episode numbers to download, separated by space: ")
        episodes = [int(ep) for ep in episodes_input.split() if ep.isdigit()]

        if not episodes:
            print("Invalid input, please enter valid episode numbers.")
            continue

        if any(ep < 1 or ep > max for ep in episodes):
            print(
                f"Invalid episode number, please enter numbers between 1 and {max_episode}.")
            continue

        return episodes


def get_site_link(anime_name, episode, quality="", audio="", anime_id="", session=""):
    """Return the link to the site containing the m3u8 file to the specific episode
       Deals with the resolution and audio of the episode
    Args:
        anime_name (str): Name of the anime
        episode (int): Episode to be used
        quality (str, optional): Quality of the episode Defaults to "".
        audio (str, optional): Possible audio languages Defaults to "".

    Returns:
        string: Link to the site containing the m3u8 file
    """
    if (anime_id == "" and session == ""):
        path = get_path(anime_name)
        with open("{}/.source.json".format(path), 'r') as source_file:
            data = json.load(source_file)['data']
        for element in data:
            if element['episode'] == episode:
                anime_id = element['anime_id']
                session = element['session']
    if (anime_id == "" and session == ""):
        print("{} episode {} not found".format(anime_name, episode))
        exit()
        # Retrieve list the video files available for the episode
    try:
        response = requests.get(
            "https://animepahe.com/api?m=links&id={}&p=kwik".format(
                session)
        )
        response.raise_for_status()
        data = json.loads(response.text)['data']
    except requests.exceptions.RequestException as err:
        print("Oops: Something went wrong", err)
        exit()
    final_list = []
    # Get the desired quality according to the possible video files
    if (quality == ""):
        all_keys = set().union(*(d.keys() for d in data))
        for i in all_keys:
            print(i)
        quality = input("Select quality :- ")
    quality_list = []
    audio_list = []
    # Add the desired quality video data to the list
    for element in data:
        x = list(element.keys())[0]
        quality_list.append(x)
    # Adding the selected quality video data to the audio selection list
    for element in range(len(quality_list)):
        if quality_list[element] == quality:
            audio_list.append(data[element]['{}'.format(quality)])
    # Checking if the audio option is supplied or not
    if (audio == ""):
        # Getting the desired audio
        for element in range(len(audio_list)):
            print(str(element) + " " + str(audio_list[element]['audio']))
        audio_number = int(input("Select the preferred audio number :- "))
    else:
        for element in range(len(audio_list)):
            # Checking if that audio is possible or not
            if (audio_list[element]['audio'] == audio):
                if (audio_list[element]['av1'] == 0):
                    audio_number = element
            else:
                # The specified audio doesn't exists hence select from the available audios
                print(
                    "Given audio language doesn't exist please select from the following")
                for element in range(len(audio_list)):
                    print(str(element) + " " +
                          str(audio_list[element]['audio']))
                audio_number = int(
                    input("Select the preferred audio number :- "))
    # Getting the desired format of the video
    final_list.append(audio_list[audio_number])
    # Returning the link  to the site holding the mw3u8 file
    return final_list[0]['kwik']


def get_playlist_link(link):
    """Returns the decoded m3u8 playlist link to the episode

    Returns:
        string: Link to the m3u8 file
    """
    global headers
    # response = sreq(link)
    try:
        response = s.get(link, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as err:
        print("OOps: Something Else", err)
    except requests.exceptions.HTTPError as httpError:
        print("Http Error:", httpError)
    except requests.exceptions.ConnectionError as connectionError:
        print("Error Connecting:", connectionError)
    except requests.exceptions.Timeout as timeoutError:
        print("Timeout Error:", timeoutError)
    # Parse the site and find the script tags
    soup = BeautifulSoup(response.content, 'lxml')
    scripts = soup.find_all("script")

    # Not so great code , trying to get the link of the m3u8 file without node

    sc = []
    for element in scripts:
        x = element.text.strip()
        if re.match("^eval", x):
            sc = x.split('|')
    # print(sc[-12:-1])
    actual_link = sc[-12:-1]
    actual_link.reverse()
    actual_link[0] = "https://"
    actual_link[1] = actual_link[1]+"-"
    actual_link[2] = actual_link[2]+"."
    actual_link[3] = actual_link[3]+"."
    actual_link[4] = actual_link[4]+"."
    actual_link[5] = actual_link[5]+"/"
    actual_link[6] = actual_link[6]+"/"
    actual_link[7] = actual_link[7]+"/"
    actual_link[8] = actual_link[8]+"/"
    actual_link[9] = actual_link[9]+"."
    m3u8_link = ''.join(actual_link)
    return m3u8_link

    # Code for getting the m3u8 link with node

    # var = ""
    # for element in scripts:
    #     temp = element.text.strip()
    #     if(temp != ""):
    #         var = temp
    # # Evaluate the javascript code
    # result = subprocess.run(["node", "-e", var],
    #                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    # # Gets the link to the m3u8 file in the stderr
    # source = result.stderr
    # sub1 = "const source='"
    # sub2 = "';const video="
    # id1 = source.index(sub1)
    # id2 = source.index(sub2)
    # res = ''
    # for idx in range(id1 + len(sub1), id2):
    #     res = res + source[idx]
    # return res


def download_key(anime_name, episode):
    """Download the key and return it

    Args:
        anime_name (str): Name of the anime
        episode (int): Episode to be downloaded

    Returns:
        crypto.cipher: THe key to decrypt the smaller segments
    """
    link = ''
    # Getting the link to the key from the m3u8 file
    with open("{}playlist.m3u8".format(get_path_episode_folder(anime_name, episode)), "r") as f:
        for line in f:
            if re.match('^#EXT-X-KEY:METHOD', line):
                line = line[:-1]
                sep = line.split(',')
                link = sep[1].split('=')
    link = link[1].split('"')[1::2]
    global headers
    # response = req(link[0])
    try:
        response = requests.get(link[0], headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as err:
        print("OOps: Something Else", err)
    except requests.exceptions.HTTPError as httpError:
        print("Http Error:", httpError)
    except requests.exceptions.ConnectionError as connectionError:
        print("Error Connecting:", connectionError)
    except requests.exceptions.Timeout as timeoutError:
        print("Timeout Error:", timeoutError)

    key = response.content
    # Getting the actual key
    sprytor = AES.new(key, AES.MODE_CBC, IV=None)
    return sprytor


def get_threads_number(anime_name, episode, t):
    count = 0
    with open("{}playlist.m3u8".format(get_path_episode_folder(anime_name, episode)), 'r') as f:
        for line in f:
            if re.match('^https', line):
                count += 1
    if count < t:
        print("More threads asked than required, selecting the maximum possible threads")
        return count
    else:
        return t


def download_video(anime_name, episode, res, t=0):
    """Download loads the video when multithreading is disabled otherwise use multithreading to download smaller segments

    Args:
        anime_name (str): Name of the anime
        episode (int): Episode to be downloaded
        res (str): link of the m3u8 file
        t (int, optional): Number of threads Defaults to 0.
    """
    if t != 0:
        # Download the m3u8 file for further processing
        global headers
        # print("Trying to download the m3u8 file")
        # response = req(res)
        try:
            response = requests.get(res, headers=headers, stream=True)
            response.raise_for_status()
        except requests.exceptions.RequestException as err:
            print("OOps: Something Else", err)
        except requests.exceptions.HTTPError as httpError:
            print("Http Error:", httpError)
        except requests.exceptions.ConnectionError as connectionError:
            print("Error Connecting:", connectionError)
        except requests.exceptions.Timeout as timeoutError:
            print("Timeout Error:", timeoutError)
        # Checking if folder exists for saving the segments
        if not os.path.exists(get_path_episode_folder(anime_name, episode)):
            os.makedirs(get_path_episode_folder(anime_name, episode))
        # Saving the m3u8 file
        if (os.path.exists("{}playlist.m3u8".format(get_path_episode_folder(anime_name, episode)))):
            print("m3u8 file already present")
        else:
            print("Trying to download the m3u8 file")
            try:
                response = requests.get(res, headers=headers, stream=True)
                response.raise_for_status()
            except requests.exceptions.RequestException as err:
                print("OOps: Something Else", err)
            except requests.exceptions.HTTPError as httpError:
                print("Http Error:", httpError)
            except requests.exceptions.ConnectionError as connectionError:
                print("Error Connecting:", connectionError)
            except requests.exceptions.Timeout as timeoutError:
                print("Timeout Error:", timeoutError)
        open("{}playlist.m3u8".format(get_path_episode_folder(
            anime_name, episode)), "wb").write(response.content)
        # Getting possible threads
        t = get_threads_number(anime_name, episode, t)
        links = []
        # Getting the segment links from the m3u8 file
        with open("{}playlist.m3u8".format(get_path_episode_folder(anime_name, episode)), "r") as f:
            for line in f:
                if re.match('^https', line):
                    links.append(line[:-1])

        # Saving the links in order present in the m3u8 file for later on merging the files
        if (os.path.exists("{}file.list".format(get_path_episode_folder(anime_name, episode)))):
            print("File list already present")
        else:
            print("Creating the file")
            with open(r'{}file.list'.format(get_path_episode_folder(anime_name, episode)), 'w') as fp:
                fp.write("\n".join(str(
                    "file "+"'"+os.path.basename(urlparse(item).path)+"'") for item in links))
        # Getting the key for decryption
        key = download_key(anime_name, episode)
        print("Got the key")
        i = 0
        pbar = tqdm(desc='Downloading segments', total=len(links))
        while i < len(links):
            download_threads = []
            p = t if (len(links)-i) > t else (len(links)-i)
            # print("Getting {} threads".format(p))
            for j in range(p):
                download_thread = threading.Thread(
                    target=download_segments, args=(links[i+j], anime_name, episode, key))
                download_threads.append(download_thread)
                download_thread.start()
            for threads in download_threads:
                threads.join()
            i += p
            pbar.update(p)
        pbar.close()
        compile(anime_name, episode)

    else:
        # Downloading the mru8 file using ffmpeg
        headers_str = "Referer: https://kwik.cx/"
        download = subprocess.run(["ffmpeg", "-headers", headers_str, "-i", res, "-c", "copy", "-y",
                                   get_video_episode(anime_name, episode)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print(download)
        print("{} Episode {} downloaded", anime_name, episode)
        exit()


def compile(anime_name, episode):
    """Compiles the smaller segments of the m3u8 file to a video

    Args:
        anime_name (str): Name of the anime
        episode (int): Episode to be downloaded
    """
    path = get_path_episode_folder(anime_name, episode)
    file = path+"file.list"
    print("Compiling the segments into video")
    print("Location ", get_path(anime_name))
    result = subprocess.run(["ffmpeg", "-f", "concat", "-safe", "0", "-i", file, "-c", "copy", "-y",
                             get_video_episode(anime_name, episode)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if (os.path.exists(get_video_episode(anime_name, episode))):
        # print(result.stdout, result.stderr)
        shutil.rmtree(path)
        print("{} Episode {} downloaded".format(anime_name, episode))
    else:
        print("Some error occurred while compiling the video", result.stderr)
        print("\nHence the folder is not deleted for the episode segments have not been deleted\nYou can try running [ffmpeg -f concat 0safe 0 -i file.list -c copy -y {}] in the episode folder to get your required episode {} of your anime {}".format(
            anime_name+" "+episode+".mp4", episode, anime_name))


def download_segments(link, anime_name, episode, key, retry=0):
    """Downloads the smaller segments of them3u8 file

    Args:
        link (string): Link to the segment
        anime_name (str): Name of the anime
        episode (int): Episode to be downloaded
        key (crypto class): 16 bit key for decryption
        segment (str): Name of the segment to be downloaded as a subprocess
    """
    segment = os.path.basename(urlparse(link).path)[:-3]
    name = get_path_episode_folder(anime_name, episode)+segment+".ts"
    global headers
    if (os.path.exists(name)):
        print("{} already Downloaded".format(segment))
    else:
        # print("Download started for {}".format(segment))
        # response = sreq(link)
        try:
            response = s.get(link, headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as err:
            print("OOps: Something Else", err)
            print("Retrying ", segment)
            response = s.get(link, headers=headers)
        except requests.exceptions.HTTPError as httpError:
            print("Http Error:", httpError)
        except requests.exceptions.ConnectionError as connectionError:
            print("Error Connecting:", connectionError)
        except requests.exceptions.Timeout as timeoutError:
            print("Timeout Error:", timeoutError)
        ts = response.content
        total_size_in_bytes = int(response.headers.get('content-length', 0))
        block_size = 1024
        while len(ts) % 16 != 0:
            ts += b"0"
        progress_bar = tqdm(desc="{}".format(
            segment), total=total_size_in_bytes, unit='iB', unit_scale=True)
        # print(len(ts))
        for data in range(len(ts), 1024):
            print(len(data), type(data))
        with open('{}.encrypted'.format(name), "ab") as file:
            # file.write(key.decrypt(ts))
            for data in response.iter_content(block_size):
                progress_bar.update(len(data))
            progress_bar.close()
        progress_bar.clear()
        if total_size_in_bytes != 0 and progress_bar.n != total_size_in_bytes:
            print("ERROR, something went wrong")

        with open(name, "ab") as file:
            file.write(key.decrypt(ts))
        # if os.path.exists(name):
        # print(segment, "download completed")
        if not os.path.exists(name):
            if retry < 3:
                download_segments(link, anime_name, episode, key, retry+1)
            else:
                print("Something went wrong, servers not working properly")
                exit()


def updates():
    global max
    res = "https://animepahe.com/api?m=airing&page1"
    # response = req(res)
    try:
        response = requests.get(res)
        response.raise_for_status()
    except requests.exceptions.RequestException as err:
        print("OOps: Something Else", err)
    except requests.exceptions.HTTPError as httpError:
        print("Http Error:", httpError)
    except requests.exceptions.ConnectionError as connectionError:
        print("Error Connecting:", connectionError)
    except requests.exceptions.Timeout as timeoutError:
        print("Timeout Error:", timeoutError)

    data = response.json()['data']
    with open('{}/myanimelist.txt'.format(script_path)) as f:
        anime_list = [line.strip() for line in f]
    count = 0
    for episode in data:
        if episode['anime_title'] in anime_list:
            anime_id = episode['anime_id']
            session = episode['session']
            anime_name = episode['anime_title']
            episode = episode['episode']
            print("New Episode {} of {} found".format(episode, anime_name))
            max = episode
            if not (os.path.exists(get_video_episode(anime_name, episode))):
                link = get_site_link(anime_name, int(
                    episode), "720", "jpn", anime_id, session)
                video_link = get_playlist_link(link)
                download_video(anime_name, episode, video_link, 50)
                count += 1
            else:
                print("File Already Present")
                continue
    if count == 0:
        print("No new episode found")


def main(args):
    if (args.verbose):
        verbose()
    if (args.updates):
        updates()
    else:
        download_anime_list()
        anime_name, anime_slug = search_anime_name(args.name)
        if args.episodes[0] == 0:
            get_source_file(anime_name, anime_slug)
            episodes = select_episode_to_download(anime_name)
        else:
            episodes = args.episodes
        print("Selected Episodes are ", episodes)
        if args.threads == 0:
            threads = int(input("Enter number of threads to use "))
        else:
            threads = args.threads
        for episode in episodes:
            link = get_site_link(anime_name, int(episode),
                                 args.quality, args.audio)
            print("\nGot the link for the episode {} of {}\n".format(
                episode, anime_name))
            video_link = get_playlist_link(link)
            print("Got the link to download",)
            download_video(anime_name, episode, video_link, threads)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Downloader for animepahe [UNOFFICIAL]\nSpeed shown is faulty")
    parser.add_argument('-n', '--name', type=str, default="",
                        help='Name of the anime')
    parser.add_argument('-e', '--episodes', type=int, nargs='*', default=[0],
                        help="List of episodes separated by spaces")
    parser.add_argument('-q', '--quality', type=str,
                        default="720", help='Quality of videos')
    parser.add_argument('-a', '--audio', type=str, default='jpn',
                        help='Language of the audio eng|jpn')
    parser.add_argument('-t', '--threads', type=int, default=0,
                        help='Number of threads to use to download')
    parser.add_argument('-u', '--updates', action='store_true',
                        help='Updater')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Logs')

    args = parser.parse_args()
    main(args)
