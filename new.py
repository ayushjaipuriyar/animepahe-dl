from bs4 import BeautifulSoup
from pyfzf.pyfzf import FzfPrompt
from Crypto.Cipher import AES
from urllib.parse import urlparse
from tqdm import tqdm
import json
import urllib3
import os
import re
import threading
import shutil
import subprocess
import math
import argparse
fzf = FzfPrompt()
script_path = os.getcwd()
max_episodes = 12


def download(url, anime_name="", episode=None, key=None):
    if anime_name != "":
        segment = os.path.basename(urlparse(url).path)[:-3]
        name = get_path_episode_folder(anime_name, episode) + segment + ".ts"
        if os.path.exists(name):
            print("{} already Downloaded".format(segment))
            return

    http = urllib3.PoolManager(
        10,
        headers={
            "Referer": "https://kwik.cx/",
            "Accept": "",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36",
        },
    )
    try:
        r = http.request("GET", url, preload_content=False)
    except urllib3.exceptions.BodyNotHttplibCompatible as e:
        print("Error:", e.reason)
    except urllib3.exceptions.ClosedPoolError as e:
        print("Error:", e.reason)
    except urllib3.exceptions.ConnectTimeoutError as e:
        print("Error:", e.reason)
    except urllib3.exceptions.DecodeError as e:
        print("Error:", e.reason)
    except urllib3.exceptions.DependencyWarning as e:
        print("Error:", e.reason)
    except urllib3.exceptions.EmptyPoolError as e:
        print("Error:", e.reason)
    except urllib3.exceptions.HTTPError as e:
        print("Error:", e.reason)
    except urllib3.exceptions.HTTPWarning as e:
        print("Error:", e.reason)
    except urllib3.exceptions.HeaderParsingError() as e:
        print("Error:", e.reason)
    except urllib3.exceptions.HostChangedError() as e:
        print("Error:", e.reason)
    except urllib3.exceptions.IncompleteRead() as e:
        print("Error:", e.reason)
    except urllib3.exceptions.InsecurePlatformWarning as e:
        print("Error:", e.reason)
    except urllib3.exceptions.InsecureRequestWarning as e:
        print("Error:", e.reason)
    except urllib3.exceptions.InvalidChunkLength() as e:
        print("Error:", e.reason)
    except urllib3.exceptions.InvalidHeader as e:
        print("Error:", e.reason)
    except urllib3.exceptions.LocationParseError() as e:
        print("Error:", e.reason)
    except urllib3.exceptions.LocationValueError as e:
        print("Error:", e.reason)
    except urllib3.exceptions.MaxRetryError() as e:
        print("Error:", e.reason)
    except urllib3.exceptions.NewConnectionError() as e:
        print("Error:", e.reason)
    except urllib3.exceptions.PoolError() as e:
        print("Error:", e.reason)
    except urllib3.exceptions.ProtocolError as e:
        print("Error:", e.reason)
    except urllib3.exceptions.ProxyError() as e:
        print("Error:", e.reason)
    except urllib3.exceptions.ProxySchemeUnknown() as e:
        print("Error:", e.reason)
    except urllib3.exceptions.ProxySchemeUnsupported as e:
        print("Error:", e.reason)
    except urllib3.exceptions.ReadTimeoutError() as e:
        print("Error:", e.reason)
    except urllib3.exceptions.RequestError() as e:
        print("Error:", e.reason)
    except urllib3.exceptions.ResponseError as e:
        print("Error:", e.reason)
    except urllib3.exceptions.ResponseNotChunked as e:
        print("Error:", e.reason)
    except urllib3.exceptions.SNIMissingWarning as e:
        print("Error:", e.reason)
    except urllib3.exceptions.SSLError as e:
        print("Error:", e.reason)
    except urllib3.exceptions.SecurityWarning as e:
        print("Error:", e.reason)
    except urllib3.exceptions.SubjectAltNameWarning as e:
        print("Error:", e.reason)
    except urllib3.exceptions.SystemTimeWarning as e:
        print("Error:", e.reason)
    except urllib3.exceptions.TimeoutError as e:
        print("Error:", e.reason)
    except urllib3.exceptions.TimeoutStateError as e:
        print("Error:", e.reason)
    except urllib3.exceptions.URLSchemeUnknown() as e:
        print("Error:", e.reason)
    except urllib3.exceptions.UnrewindableBodyError as e:
        print("Error:", e.reason)
    if anime_name != "":
        segment = os.path.basename(urlparse(url).path)[:-3]
        name = get_path_episode_folder(anime_name, episode) + segment + ".ts"
        data = r.data
        total_size_in_bytes = int(r.getheader("Content-Length"))
        block_size = 1024
        while len(data) % 16 != 0:
            data += b"0"
        for data in range(len(data), 1024):
            print(len(data), type(data))
        with open(name, "ab") as file:
            file.write(key.decrypt(data))
        with tqdm(
            desc=segment,
            total=total_size_in_bytes,
            unit="iB",
            unit_scale=True,
            unit_divisor=block_size,
        ) as bar:
            for d in range(len(data), block_size):
                bar.update(len(d))
    return r


def anime_name_folder(anime_name):
    temp = anime_name
    temp = temp.replace("/", "_")
    temp = temp.replace("<", "_")
    temp = temp.replace(">", "_")
    temp = temp.replace(":", "_")
    temp = temp.replace("\\", "_")
    temp = temp.replace("?", "_")
    temp = temp.replace("|", "_")
    temp = temp.replace("*", "_")
    return temp


def get_path(anime_name):
    path = script_path + "/" + anime_name_folder(anime_name)
    return path


def get_path_episode_folder(anime_name, episode):
    """Returns the required path for further processing when multithreading
       Folder to save the segments into
    Args:
        anime_name (str): Name of the anime
        episode (Integer): Episode to be downloaded

    Returns:
        string:Returns the path to the folder according to the episode number
    """
    path = get_path(anime_name) + "/" + str(episode) + "/"
    return path


def download_anime_list():
    """
    Parse animepahe.com/anime to retrieve all the anime name with their UUID
    """
    url = "https://animepahe.com/anime/"
    # r = brotli.decompress(download(url).data)
    r = download(url)
    soup = BeautifulSoup(r.data, "html.parser")
    divContainer = soup.find_all("div", {"class": "tab-content"})
    with open("animelist.txt", "w") as f:
        for tag in divContainer:
            for tags in tag.find_all("a"):
                uuid = tags.attrs['href'].removeprefix('/anime/')
                name = tags.text.strip()
                f.write("{}::::{}\n".format(uuid, name))


def get_video_episode(anime_name, episode):
    """Returns the name of the video to be downloaded with path

    Args:
        anime_name (str): Name of the anime
        episode (Integer): Episode to be downloaded

    Returns:
        path: Return the path with the name of the file to be downloaded
    """
    global max_episodes
    name = get_path(anime_name) + "/" + anime_name + \
        " Episode " + str(episode) + ".mp4"

    return name


def add_anime_to_myanimelist(anime_name):
    """Adds an anime name to the myanimelist file, after prompting the user to confirm"""
    with open(os.path.join(script_path, 'myanimelist.txt'), 'a+', encoding='utf-8') as f:
        f.seek(0)
        if anime_name in f.read():
            print(f"{anime_name} already present")
            return
    print("Do you want to add {} to myanimelist.txt? (y/n)".format(anime_name))
    response = input().strip().lower()
    if response == 'y':
        with open(os.path.join(script_path, 'myanimelist.txt'), 'a+', encoding='utf-8') as f:
            f.write(f"{anime_name}\n")
            print(f"{anime_name} added to myanimelist")
    else:
        print(f"{anime_name} not added to myanimelist")


def search_anime_name(anime=""):
    anime_list = []
    if anime != "":
        anime = anime.replace(" ", "%20")
        res = "https://animepahe.com/api?m=search&q={}".format(anime)
        data = json.loads(download(res).data)
        # print(data)

        for element in data["data"]:
            uuid = element['session']
            name = element['title']
            anime_list.append("{}::::{}".format(uuid, name))
    else:
        anime_list = open("animelist.txt", "r").readlines()
    result = fzf.prompt(anime_list)[0]
    anime_slug, anime_name = result.split("::::")
    # Adding names to myanimelist
    add_anime_to_myanimelist(anime_name)
    return anime_name, anime_slug


def get_source_file(anime_name, anime_slug):
    res = "https://animepahe.com/api?m=release&id={}".format(anime_slug)
    data = download(res)
    data = json.loads(download(res).data)
    pages = data["last_page"]
    episode_list = []
    for i in range(1, pages+1):
        res = (
            "https://animepahe.com/api?m=release&id={}&sort=episode_asc&page={}".format(
                anime_slug, i
            )
        )
        data = json.loads(download(res).data)["data"]
        episode_list += data
    org = {"data": episode_list}
    # print(episode_list)
    path = get_path(anime_name)
    print(path)
    if not os.path.exists(path):
        os.makedirs(path)
    with open("{}/.source.json".format(path), "w") as write_file:
        json.dump(org, write_file)


def select_episode_to_download(anime_name):
    global max_episodes
    path = get_path(anime_name)
    print("Download location ", path)
    with open("{}/.source.json".format(path), "r") as f:
        data = json.load(f)["data"]
    max_episodes = data[-1]["episode"]
    for element in data:
        print("Episode {}".format(element["episode"]))

    valid = False
    while not valid:
        episodes = set()
        s = True
        user_input = input(
            "Enter episode numbers or ranges, separated by space: ")
        for r in user_input.split():
            if "-" in r:
                start, end = r.split("-")
                if (start.isdigit() and end.isdigit()) and s:
                    if int(start) > int(end):
                        start, end = end, start
                    episodes.update(range(int(start), int(end)+1))
                else:
                    s = False
            else:
                if r.isdigit() and s:
                    episodes.add(int(r))
                else:
                    s = False
        episodes = sorted(list(episodes))
        if not s:
            print(
                "Invalid input. Please enter valid episode numbers separated by space, and ranges using '-'.")
        elif len(episodes) > 0:
            if max(episodes) > max_episodes or min(episodes) < 1:
                print("Out of range episodes selected")
        else:
            valid = True

    return episodes


def check_resolution(buttons, selected_quality):
    matching_buttons = []
    available_qualities = set()
    for button in buttons:
        if button.has_attr('data-resolution'):
            available_qualities.add(button['data-resolution'])
            if button['data-resolution'] == selected_quality:
                matching_buttons.append(button)
    if len(matching_buttons) > 0:
        return matching_buttons
    else:
        print(f"Quality {selected_quality} is not available.")
        print("Available options are:")
        for quality in available_qualities:
            print(quality)
        selected_quality = input("Please choose from the available options: ")
        return check_resolution(buttons, selected_quality)


def check_audio(buttons, selected_audio):
    matching_buttons = []
    available_audios = set()
    for button in buttons:
        if button.has_attr('data-audio'):
            available_audios.add(button['data-audio'])
            if button['data-audio'] == selected_audio:
                matching_buttons.append(button)
    if len(matching_buttons) > 0:
        return matching_buttons
    else:
        print(f"Audio {selected_audio} is not available.")
        print("Available options are:")
        for audio in available_audios:
            print(audio)
        selected_audio = input("Please choose from the available options: ")
        return check_audio(buttons, selected_audio)


def get_site_link(anime_name, episode, quality, audio, anime_slug, session=None):
    if session is None:
        path = get_path(anime_name)
        source_file = os.path.join(path, ".source.json")
        with open(source_file, "r") as source_file:
            data = json.load(source_file)["data"]
        for element in data:
            if element["episode"] == episode:
                session = element["session"]
                break
    if session is None:
        print("{} episode {} not found".format(anime_name, episode))
        exit()
    else:
        res = "https://animepahe.com/play/{}/{}".format(anime_slug, session)
        data = download(res)
        soup = BeautifulSoup(data, "html.parser")
        buttons = soup.find_all(
            "button", attrs={"data-src": True, "data-av1": 0})
    fin = check_resolution(buttons, quality)
    fin = check_audio(fin, audio)
    print(fin)
    link = fin[0]['data-src']
    return link


def get_playlist_link(link):
    data = download(link)
    soup = BeautifulSoup(data, "html.parser")
    scripts = soup.find_all("script", string=True)
    for script in scripts:
        sc = script.string.encode('utf-8')
        p = subprocess.Popen(
            ['node'], shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate(sc)
        match = re.search("const source='(.*)';", stderr.decode('utf-8'))
        if match:
            source = match.group(1)
            print(source)
            return str(source)
        else:
            print("Source not found in output.")
            exit()


def get_m3u8(anime_name, episode, res):
    folder_path = get_path_episode_folder(anime_name, episode)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    file_path = "{}playlist.m3u8".format(
        get_path_episode_folder(anime_name, episode))
    if os.path.exists(file_path):
        print("m3u8 file already present")
    else:
        data = download(res).read()
        with open(file_path, "wb") as f:
            f.write(data)


def download_video(anime_name, episode, u_threads=0):
    links = []
    if u_threads != 0:
        link = ""
        with open(
            "{}playlist.m3u8".format(
                get_path_episode_folder(anime_name, episode)), "r"
        ) as f:
            for line in f:
                if link == "":
                    if re.match("^#EXT-X-KEY:METHOD", line):
                        line = line[:-1]
                        sep = line.split(",")
                        link = sep[1].split("=")
                        link = link[1].split('"')[1::2]
                if re.match("^https", line):
                    links.append(line[:-1])

        if os.path.exists(
            "{}file.list".format(get_path_episode_folder(anime_name, episode))
        ):
            print("File already exists")
        else:
            print("Creating the file")
            with open(
                r"{}file.list".format(
                    get_path_episode_folder(anime_name, episode)), "w"
            ) as fp:
                fp.write(
                    "\n".join(
                        str("file " + "'" +
                            os.path.basename(urlparse(item).path) + "'")
                        for item in links
                    )
                )
    print("link= ", link)
    key = download(link[0]).read()
    sprytor = AES.new(key, AES.MODE_CBC, IV=None)
    if u_threads <= len(links):
        print("Number of threads {}".format(u_threads))
    else:
        print(
            "Numer of threads supplied too many reverting to the max possible {}".format(
                len(links)
            )
        )
        u_threads = len(links)
    i = 0
    pbar = tqdm(desc="Downloading segments", total=len(links))
    while i < len(links):
        downloaded_threads = []
        if (len(links) - i) > u_threads:
            p = u_threads
        else:
            p = len(links) - i
        for j in range(p):
            download_thread = threading.Thread(
                target=download, args=(
                    links[i + j], anime_name, episode, sprytor)
            )
            downloaded_threads.append(download_thread)
            download_thread.start()
        for threads in downloaded_threads:
            threads.join()
        i += p
        pbar.update(p)
    pbar.close()
    compile(anime_name, episode)

    # else:


def compile_video(anime_name, episode):
    """
    Compiles the segments of an anime episode into a single video file using ffmpeg.

    Args:
        anime_name (str): The name of the anime.
        episode (str): The episode number as a string (e.g., "01").

    Returns:
        None
    """
    episode_folder = get_path_episode_folder(anime_name, episode)
    list_file_path = os.path.join(episode_folder, "file.list")
    output_video_path = get_video_episode(anime_name, episode)

    # Use ffmpeg to concatenate the segments into a video
    cmd = [
        "ffmpeg",
        "-f", "concat",
        "-safe", "0",
        "-i", list_file_path,
        "-c", "copy",
        "-y", output_video_path
    ]
    try:
        subprocess.check_call(cmd, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print("Failed to compile the video: {}".format(e.stderr))
        print("You can try running the following command manually in the episode folder:")
        print(
            "ffmpeg -f concat -safe 0 -i file.list -c copy -y {}".format(output_video_path))
        return

    # If the video was created successfully, delete the episode folder
    shutil.rmtree(episode_folder)
    print("{} episode {} downloaded to {}".format(
        anime_name, episode, output_video_path))


def updates():
    res = "https://animepahe.com/api?m=airing&page1"
    data = json.loads(download(res))["data"]
    with open("{}/myanimelist.txt".format(script_path)) as f:
        anime_list = [line.strip() for line in f]
    count = 0
    for episode in data:
        if episode["anime_title"] in anime_list:
            anime_id = episode["anime_id"]
            uuid = episode["anime_session"]
            session = episode["session"]
            anime_name = episode["anime_title"]
            episode = episode["episode"]
            print("New Episode {} of {} found".format(episode, anime_name))
            max_episode = episode
            if not (os.path.exists(get_video_episode(anime_name, episode))):
                link = get_site_link(anime_name, int(
                    episode), "720", "jpn", uuid, session)
                video_link = get_playlist_link(link)
                download_video(anime_name, episode, video_link, 50)
                count += 1
            else:
                print("File Already Present")
                continue
    if count == 0:
        print("No new episode found")


def main(args):
    if args.updates:
        updates()
    else:
        download_anime_list()
        anime_name, anime_slug = search_anime_name(args.name)
        get_source_file(anime_name, anime_slug)
        if args.episodes[0] == 0:
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
                                 args.quality, args.audio, anime_slug)
            print(
                "\nGot the link for the episode {} of {}\n".format(
                    episode, anime_name)
            )
            m3u8_link = get_playlist_link(link)
            get_m3u8(anime_name, episode, m3u8_link)
            print(
                "Got the link to download",
            )
            download_video(anime_name, episode, threads)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Downloader for animepahe [UNOFFICIAL]\nSpeed shown is faulty"
    )
    parser.add_argument("-n", "--name", type=str,
                        default="", help="Name of the anime")
    parser.add_argument(
        "-e",
        "--episodes",
        type=int,
        nargs="*",
        default=[0],
        help="List of episodes separated by spaces",
    )
    parser.add_argument(
        "-q", "--quality", type=str, default="720", help="Quality of videos"
    )
    parser.add_argument(
        "-a", "--audio", type=str, default="jpn", help="Language of the audio eng|jpn"
    )
    parser.add_argument(
        "-t",
        "--threads",
        type=int,
        default=0,
        help="Number of threads to use to download",
    )
    parser.add_argument("-u", "--updates", action="store_true", help="Updater")
    parser.add_argument("-v", "--verbose", action="store_true", help="Logs")

    args = parser.parse_args()
    main(args)
