import json
import urllib3
import os
import re
import threading
import shutil
import subprocess
import math
import argparse
from tqdm import tqdm
from urllib.parse import urlparse
from Crypto.Cipher import AES
from pyfzf.pyfzf import FzfPrompt
from bs4 import BeautifulSoup

fzf = FzfPrompt()

script_path = os.getcwd()


def unPack(code):
    def indent(code):
        tabs = 0
        old = -1
        add = ''
        try:
            for i in range(len(code)):
                if "{" in code[i]:
                    tabs += 1
                if "}" in code[i]:
                    tabs -= 1
                if old != tabs:
                    old = tabs
                    add = ""
                    while old > 0:
                        add += "\t"
                        old -= 1
                    old = tabs
                code[i] = add + code[i]
        finally:
            tabs = None
            old = None
            add = None
        return code

    env = {
        "eval": (lambda c: setattr(code, code, c)),
        "window": {},
        "document": {}
    }

    exec("with env: " + code)

    code = str(code).replace(";", ";\n").replace("{", "\n{\n").replace(
        "}", "\n}\n").replace("\n;\n", ";\n").replace("\n\n", "\n")

    code = code.split("\n")
    code = indent(code)

    code = "\n".join(code)
    return code


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
    f = open("animelist.txt", "w")
    for tag in divContainer:
        for tags in tag.find_all("a"):
            f.write(
                tags.attrs["href"].removeprefix("/anime/")
                + "::::"
                + tags.text.strip()
                + "::::"
            )
            f.write("\n")
    f.close


def get_video_episode(anime_name, episode):
    """Returns the name of the video to be downloaded with path

    Args:
        anime_name (str): Name of the anime
        episode (Integer): Episode to be downloaded

    Returns:
        path: Return the path with the name of the file to be downloaded
    """
    global max
    name = get_path(anime_name) + "/" + anime_name + \
        " Episode " + str(episode) + ".mp4"

    return name


def search_anime_name(anime=""):
    anime_list = []
    if anime != "":
        anime = anime.replace(" ", "%20")
        res = "https://animepahe.com/api?m=search&q={}".format(anime)
        data = json.loads(download(res).data)
        # print(data)

        for element in data["data"]:
            anime_list.append(element["session"] + "::::" + element["title"])

    else:
        anime_list = open("animelist.txt", "r").readlines()

    result = fzf.prompt(anime_list)[0]
    anime_slug = result.split("::::")[0]
    anime_name = result.split("::::")[1]
    # Adding names to myanimelist
    return anime_name, anime_slug


def get_source_file(anime_name, anime_slug):
    res = "https://animepahe.com/api?m=release&id={}".format(anime_slug)
    data = download(res)
    data = json.loads(download(res).data)
    pages = data["last_page"]
    i = 1
    episode_list = []
    while i <= pages:
        res = (
            "https://animepahe.com/api?m=release&id={}&sort=episode_asc&page={}".format(
                anime_slug, i
            )
        )
        data = json.loads(download(res).data)["data"]
        episode_list = episode_list + data
        i += 1
        org = dict({"data": episode_list})
    # print(episode_list)
    path = get_path(anime_name)
    print(path)
    if not os.path.exists(path):
        os.makedirs(path)
    with open("{}/.source.json".format(path), "w") as write_file:
        json.dump(org, write_file)


def select_episode_to_download(anime_name):
    path = get_path(anime_name)
    print("Download location ", path)
    with open("{}/.source.json".format(path), "r") as f:
        data = json.load(f)["data"]
    for element in data:
        print("Episode {}".format(element["episode"]))
    episodes = []
    episodes = [
        int(x) for x in input("Enter episode numbers, seperated by space :").split()
    ]
    global max
    max = data[-1]["episode"]
    return episodes


def get_site_link(anime_name, episode, quality, audio="", anime_id="", session=""):
    if anime_id == "" and session == "":
        path = get_path(anime_name)
        with open("{}/.source.json".format(path), "r") as source_file:
            data = json.load(source_file)["data"]
        for element in data:
            if element["episode"] == episode:
                anime_id = element["anime_id"]
                session = element["session"]
    if anime_id == "" and session == "":
        print("{} episode {} not found".format(anime_name, episode))
        exit()
    else:
        res = "https://animepahe.com/api?m=links&id={}&p=kwik".format(session)
        data = json.loads(download(res).data)["data"]
    qualities = set().union(*(d.keys() for d in data))
    qualities = [int(x) for x in qualities]
    if int(quality) in qualities:
        print("Required quality is present\n")
    else:
        print(
            "Required quality {} is not present reverting to the highest quality possible {}".format(
                quality, max(qualities)
            )
        )
        quality = max(qualities)
    audios = []
    for element in data:
        if element.get(str(quality)) is not None:
            audios.append(element["{}".format(str(quality))]["audio"])
    if audio in audios:
        print("Selected audio is present\n")
    else:
        print("Selected audio is not present hence reverting to jpn")
        audio = "jpn"
    for element in data:
        if element.get(str(quality)) is not None:
            if element["{}".format(str(quality))]["audio"] == audio:
                if element["{}".format(str(quality))]["av1"] == 0:
                    return element["{}".format(str(quality))]["kwik"]


def get_playlist_link(link):
    data = download(link)
    soup = BeautifulSoup(data, "html.parser")
    scripts = soup.find_all("script", string=True)
    packed = ""
    slips = scripts[0].string.split("eval")
    # print(scripts[0].string)
    packed = slips[2][1:-2]
    print(packed)
    print(unPack(packed))

    # z = x.text.strip()
    # if re.match("^eval", z):
    # print(x[8:-10])
    # l = x.split("eval")
    # print(l)
    # sc = []
    # for element in scripts:
    # if re.match("^eval", x):
    # sc = x.split("|")
    # actual_link = ""
    # for i in reversed(range(len(sc))):
    #     if "eu" in sc[i]:
    #         actual_link += "https://" + sc[i] + "-" + sc[i + 1] + "."
    #     if "files" in sc[i]:
    #         actual_link += +sc[i] + "."
    #     if "" in sc[i]:
    #         actual_link += "https://" + sc[i] + "-"
    #     if "eu" in sc[i]:
    #         actual_link += "https://" + sc[i] + "-"
    #     if "eu" in sc[i]:
    #         actual_link += "https://" + sc[i] + "-"
    #     if "eu" in sc[i]:
    #         actual_link += "https://" + sc[i] + "-"
    #     if "eu" in sc[i]:
    #         actual_link += "https://" + sc[i] + "-"
    #     if "eu" in sc[i]:
    #         actual_link += "https://" + sc[i] + "-"
    #     if "eu" in sc[i]:
    #         actual_link += "https://" + sc[i] + "-"

    #     if "m3u8" in sc[i]:
    #         actual_link.append(sc[i])
    #         break
    #     else:
    #         actual_link.append(sc[i])
    # print(actual_link)
    # actual_link.pop(0)
    # actual_link.pop(0)
    # print(actual_link)
    # actual_link[0] += "-"
    # actual_link[1] += "."
    # actual_link[2] += "."
    # actual_link[3] += "."
    # actual_link[4] += "/"
    # actual_link[5] += "/"
    # actual_link[6] += "/"
    # actual_link[7] += "/"
    # actual_link[8] += "/"
    # actual_link[9] += "."
    # m3u8_link = "https://" + "".join(actual_link)
    # print(m3u8_link)
    m3u8_link = ""
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


def get_m3u8(anime_name, episode, res):
    if not os.path.exists(get_path_episode_folder(anime_name, episode)):
        os.makedirs(get_path_episode_folder(anime_name, episode))
    if os.path.exists(
        "{}playlist.m3u8".format(get_path_episode_folder(anime_name, episode))
    ):
        print("m3u8 file already present")
    else:
        data = download(res).read()
        open(
            "{}playlist.m3u8".format(
                get_path_episode_folder(anime_name, episode)), "wb"
        ).write(data)


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


def compile(anime_name, episode):
    path = get_path_episode_folder(anime_name, episode)
    file = path + "file.list"
    print("Compiling the segments into video")
    print("Location ", get_path(anime_name))
    result = subprocess.run(
        [
            "ffmpeg",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            file,
            "-c",
            "copy",
            "-y",
            get_video_episode(anime_name, episode),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if os.path.exists(get_video_episode(anime_name, episode)):
        # print(result.stdout, result.stderr)
        shutil.rmtree(path)
        print("{} Episode {} downloaded".format(anime_name, episode))
    else:
        print("Some error occurred while compiling the video", result.stderr)
        print(
            "\nHence the folder is not deleted for the episode segments have not been deleted\nYou can try running [ffmpeg -f concat 0safe 0 -i file.list -c copy -y {}] in the episode folder to get your required episode {} of your anime {}".format(
                anime_name + " " + episode + ".mp4", episode, anime_name
            )
        )


# if __name__ == "__main__":
#     # download_anime_list()
#     # anime_name, anime_slug = search_anime_name("")
#     anime_name, anime_slug = search_anime_name("Chainsaw Man")
#     # get_source_file(anime_name, anime_slug)
#     # episodes = select_episode_to_download(anime_name)
#     # for episode in episodes:

#     link = get_site_link(anime_name, 11,
#                          720, "jpn")
#     video_link = get_playlist_link(link)
#     get_m3u8(anime_name, 11, video_link)
#     threads = 100
#     download_video(anime_name, 11, threads)
#     # compile(anime_name, 11)

#     # print(episodes)


def updates():
    res = "https://animepahe.com/api?m=airing&page1"
    data = json.loads(download(res))["data"]
    with open("{}/myanimelist.txt".format(script_path)) as f:
        anime_list = [line.strip() for line in f]
    count = 0
    for episode in data:
        if episode["anime_title"] in anime_list:
            anime_id = episode["anime_id"]
            session = episode["session"]
            anime_name = episode["anime_title"]
            episode = episode["episode"]
            print("New Episode {} of {} found".format(episode, anime_name))
            max = episode
            if not (os.path.exists(get_video_episode(anime_name, episode))):
                link = get_site_link(
                    anime_name, int(episode), 720, "jpn", anime_id, session
                )
                video_link = get_playlist_link(link)
                download_video(anime_name, episode, video_link, 50)
                count += 1
            else:
                print("File Already Present")
                continue
    if count == 0:
        print("No new episode found")


def main(args):
    # if (args.verbose):
    # verbose()
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
                                 args.quality, args.audio)
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
