import shutil
import os
from urllib.parse import urlparse
import subprocess
from bs4 import BeautifulSoup
import requests
import json
import re
import math
import threading
from Crypto.Cipher import AES
from pyfzf.pyfzf import FzfPrompt
fzf = FzfPrompt()
script_path = os.getcwd()
max = 1


def download_anime_list():
    """Parse animepahe.com/anime to retrieve all the anime with their UUIDs
    """

    try:
        response = requests.get('https://animepahe.com/anime/')
        response.raise_for_status()
    except requests.exceptions.RequestException as err:
        print("OOps: Something Else", err)
    except requests.exceptions.HTTPError as httpError:
        print("Http Error:", httpError)
    except requests.exceptions.ConnectionError as connectionError:
        print("Error Connecting:", connectionError)
    except requests.exceptions.Timeout as timeoutError:
        print("Timeout Error:", timeoutError)
    # Parsing the the request sent
    soup = BeautifulSoup(response.content, 'lxml')
    divContainer = soup.find_all("div", {"class": "tab-content"})
    # Storing them to the file
    f = open('animelist.txt', 'w')
    for tag in divContainer:
        for tags in tag.find_all("a"):
            f.write(tags.attrs['href'].removeprefix(
                '/anime/') + " ::::" + tags.text.strip() + "::::")
            f.write("\n")
    f.close()


def search_anime_name():
    """Search from the earlier created anime list
        And write those name for future auto downloading

    Returns:
        list: This lst contains the anime_slug and anime_name, anime UUID and anime name respectively
    """
    # Search for the possible animes to download from the animelist
    anime_list = open("animelist.txt").readlines()
    anime = fzf.prompt(anime_list)
    # Select your desired anime to download
    anime_slug = anime[0].split(' ::::')[0]
    anime_name = anime[0].split('::::')[1]
    # Writing to anime names to the
    myanimelist = open('myanimelist.txt', 'a')
    myanimelist.write(anime_name)
    myanimelist.write('\n')
    myanimelist.close()
    return anime_name, anime_slug


def anime_name_folder(anime_name):
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


def get_path(anime_name):
    path = script_path+'/'+anime_name_folder(anime_name)
    return path


def get_path_episode(anime_name, episode):
    path = get_path(anime_name)+"/"+str(episode)+"/"
    return path


def get_video_episode(anime_name, episode):
    global max
    name = get_path(anime_name)+"/"+anime_name + " Episode " + \
        str(episode).zfill(int(math.log10(max))+2)+".mp4"

    return name


def get_episode_list(anime_name, anime_slug):
    try:
        response = requests.get(
            "https://animepahe.com/api?m=release&id={}".format(anime_slug))
        response.raise_for_status()
    except requests.exceptions.RequestException as err:
        print("OOps: Something Else", err)
    except requests.exceptions.HTTPError as httpError:
        print("Http Error:", httpError)
    except requests.exceptions.ConnectionError as connectionError:
        print("Error Connecting:", connectionError)
    except requests.exceptions.Timeout as timeoutError:
        print("Timeout Error:", timeoutError)

    pages = json.loads(response.text)['last_page']
    i = 1
    episode_list = []
    while(i <= pages):
        try:
            response = requests.get(
                "https://animepahe.com/api?m=release&id={}&sort=episode_asc&page={}".format(anime_slug, i))
            response.raise_for_status()
        except requests.exceptions.RequestException as err:
            print("OOps: Something Else", err)
        except requests.exceptions.HTTPError as httpError:
            print("Http Error:", httpError)
        except requests.exceptions.ConnectionError as connectionError:
            print("Error Connecting:", connectionError)
        except requests.exceptions.Timeout as timeoutError:
            print("Timeout Error:", timeoutError)

        data = json.loads(response.text)
        temp = data['data']
        episode_list = episode_list+temp
        i += 1
        org = dict({"data": episode_list})
    path = get_path(anime_name)
    isExist = os.path.exists(path)
    if not isExist:
        os.makedirs(path)
    with open("{}/.source.json".format(path), "w") as write_file:
        json.dump(org, write_file)


def get_playlist_link(anime_name, episode, quality="", audio=""):
    path = get_path(anime_name)
    with open("{}/.source.json".format(path), 'r') as source_file:
        data = json.load(source_file)['data']
    anime_id = ""
    session = ""
    for element in data:
        if element['episode'] == episode:
            anime_id = element['anime_id']
            session = element['session']
    if(anime_id == "" and session == ""):
        print("{} episode {} not found".format(anime_name, episode))
        exit()
    else:
        try:
            response = requests.get(
                "https://animepahe.com/api?m=embed&id={}&session={}&p=kwik".format(
                    anime_id, session)
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as err:
            print("OOps: Something Else", err)
        except requests.exceptions.HTTPError as httpError:
            print("Http Error:", httpError)
        except requests.exceptions.ConnectionError as connectionError:
            print("Error Connecting:", connectionError)
        except requests.exceptions.Timeout as timeoutError:
            print("Timeout Error:", timeoutError)

        data = json.loads(response.text)['data']
    final_list = []
    audio_number = 0
    if(quality == ""):
        all_keys = set().union(*(d.keys() for d in data))
        for i in all_keys:
            print(i)
        quality = input("Select quality :- ")
    quality_list = []
    audio_list = []
    for element in data:
        x = list(element.keys())[0]
        quality_list.append(x)
    for element in range(len(quality_list)):
        if quality_list[element] == quality:
            audio_list.append(data[element]['{}'.format(quality)])
    if(audio == ""):
        for element in range(len(audio_list)):
            print(str(element) + " " + str(audio_list[element]['audio']))
        audio_number = int(input("Select the preferred audio number :- "))
    else:
        for element in range(len(audio_list)):
            if(audio_list[element]['audio'] == audio):
                audio_number = element
    final_list.append(audio_list[audio_number])
    return final_list[0]['kwik']


def select_episode_to_download(anime_name):
    path = get_path(anime_name)
    print(path)
    with open("{}/.source.json".format(path), 'r') as f:
        data = json.load(f)['data']
    for element in data:
        print("Episode {}".format(element['episode']))
    episodes = input().split(' ')
    global max
    max = data[-1]['episode']
    return episodes


def download_file(link, anime_name, episode, segment="", key=None):
    # referer_url = "https://kwik.cx/"
    if(segment != ""):
        headers = {"Referer": "https://kwik.cx/",
                   "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                   "Connection": "Keep-Alive",
                   "Accept-Encoding": "gzip, deflate, br",
                   "Accept-Language": "zh-CN,zh;q=0.9",
                   "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36"
                   }
        try:
            response = requests.get(link, headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as err:
            print("OOps: Something Else", err)
        except requests.exceptions.HTTPError as httpError:
            print("Http Error:", httpError)
        except requests.exceptions.ConnectionError as connectionError:
            print("Error Connecting:", connectionError)
        except requests.exceptions.Timeout as timeoutError:
            print("Timeout Error:", timeoutError)

        key = download_key(anime_name, episode)
        print("Downloading {}".format(segment))
        ts = response.content
        while len(ts) % 16 != 0:
            ts += b"0"
        name = get_path_episode(anime_name, episode) + segment+".ts"
        with open(name, "ab") as file:
            file.write(key.decrypt(ts))
        print(segment, "download complete")
    else:
        headers = {"Referer": "https://kwik.cx/"}
        try:
            response = requests.get(link, headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as err:
            print("OOps: Something Else", err)
        except requests.exceptions.HTTPError as httpError:
            print("Http Error:", httpError)
        except requests.exceptions.ConnectionError as connectionError:
            print("Error Connecting:", connectionError)
        except requests.exceptions.Timeout as timeoutError:
            print("Timeout Error:", timeoutError)

        soup = BeautifulSoup(response.content, 'lxml')
        scripts = soup.find_all("script")
        var = ""
        for element in scripts:
            temp = element.text.strip()
            if(temp != ""):
                var = temp
        result = subprocess.run(["node", "-e", var],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        source = result.stderr
        sub1 = "const source='"
        sub2 = "';const video="
        id1 = source.index(sub1)
        id2 = source.index(sub2)
        res = ''
        for idx in range(id1 + len(sub1), id2):
            res = res + source[idx]
        return res


def download_key(anime_name, episode):
    link = ''
    with open("{}playlist.m3u8".format(get_path_episode(anime_name, episode)), "r") as f:
        for line in f:
            if re.match('^#EXT-X-KEY:METHOD', line):
                line = line[:-1]
                sep = line.split(',')
                link = sep[1].split('=')
    headers = {"Referer": "https://kwik.cx/"}
    link = link[1].split('"')[1::2]
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
    sprytor = AES.new(key, AES.MODE_CBC, IV=key)
    return (sprytor)


def download_video(anime_name, episode, res, t=0):
    if t != 0:
        headers = {"Referer": "https://kwik.cx/"}
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
        isExist = os.path.exists(get_path_episode(anime_name, episode))
        if not isExist:
            os.makedirs(get_path_episode(anime_name, episode))
        open("{}playlist.m3u8".format(get_path_episode(
            anime_name, episode)), "wb").write(response.content)
        t = get_threads_number(anime_name, episode, t)
        print("After getting the number of threads", t)
        links = []
        with open("{}playlist.m3u8".format(get_path_episode(anime_name, episode)), "r") as f:
            for line in f:
                if re.match('^https', line):
                    links.append(line[:-1])
        with open(r'{}file.list'.format(get_path_episode(anime_name, episode)), 'w') as fp:
            fp.write("\n".join(str(
                "file "+"'"+os.path.basename(urlparse(item).path)+"'") for item in links))
        key = download_key(anime_name, episode)
        i = 0
        while i < len(links):
            download_threads = []
            p = t if (len(links)-i) > t else (len(links)-i)
            for j in range(p):
                download_thread = threading.Thread(
                    target=download_file, args=(links[i+j], anime_name, episode, os.path.basename(
                        urlparse(links[i+j]).path)[:-3], key))
                download_threads.append(download_thread)
                download_thread.start()
            for threads in download_threads:
                threads.join()
            i += t
        compile(anime_name, episode)

    else:
        print(res)
        headers_str = "Referer: https://kwik.cx/"
        download = subprocess.run(["ffmpeg", "-headers", headers_str, "-i", res, "-c", "copy", "-y",
                                   get_video_episode(anime_name, episode)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print(download)


def get_threads_number(anime_name, episode, t):
    count = 0
    with open("{}playlist.m3u8".format(get_path_episode(anime_name, episode)), 'r') as f:
        for line in f:
            if re.match('^https', line):
                count += 1
    if count < t:
        return count
    else:
        return t


def compile(anime_name, episode):
    path = get_path_episode(anime_name, episode)
    file = path+"file.list"
    print("Compiling the segments into video")
    result = subprocess.run(["ffmpeg", "-f", "concat", "-safe", "0", "-i", file, "-c", "copy", "-y",
                            get_video_episode(anime_name, episode)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if(os.path.exists(get_video_episode(anime_name, episode))):
        shutil.rmtree(path)
        print("{} Episode {} downloaded".format(anime_name, episode))
    else:
        print("Some error occurred while compiling the video", result.stderr)
        print("\nHence the folder is not deleted for the episode segments have not been deleted\nYou can try running [ffmpeg -f concat 0safe 0 -i file.list -c copy -y {}] in the episode folder to get your required episode {} of your anime {}".format(
            anime_name+" "+episode+".mp4", episode, anime_name))


def main():

    download_anime_list()
    anime_name, anime_slug = search_anime_name()
    get_episode_list(anime_name, anime_slug)
    episodes = select_episode_to_download(anime_name)
    print("Selected Episodes are ", episodes)
    threads = int(input("Enter number of threads to use "))
    for episode in episodes:
        link = get_playlist_link(anime_name, int(episode), "720", "jpn")
        print(link)
        video_link = download_file(link, anime_name, episode)
        print(video_link)
        download_video(anime_name, episode, video_link, threads)


if __name__ == "__main__":
    main()
