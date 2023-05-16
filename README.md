# animepahe-dl

Python program to download anime from [AnimePahe](https://animepahe.com)

## Table of contents

- [animepahe-dl](#animepahe-dl)
  - [Table of contents](#table-of-contents)
  - [Requirements](#requirements)
    - [How to Use](#how-to-use)
  - [Examples](#examples)
  - [To-dos](#to-dos)

## Requirements

```
node
requests
tqdm
crypto
pyfzf
ffmpeg
fzf
```

### How to Use

---

```
usage: downloader.py [-h] [-n NAME] [-e [EPISODES ...]] [-q QUALITY] [-a AUDIO] [-t THREADS] [-u]

Downloader for animepahe [UNOFFICIAL] Speed shown is faulty

options:
  -h, --help            show this help message and exit
  -n NAME, --name NAME  Name of the anime
  -e [EPISODES ...], --episodes [EPISODES ...]
                        List of episodes separated by spaces
  -q QUALITY, --quality QUALITY
                        Quality of videos
  -a AUDIO, --audio AUDIO
                        Language of the audio eng|jpn
  -t THREADS, --threads THREADS
                        Number of threads to use to download
  -u, --updates         Updater
```

## Examples

```

```

## To-dos

---

- [x] ~~Trying to get rid of Node.js as a dependency~~
- [x] ~~Fixing multiple entries of same anime in the myanimelist for checking for updates~~
- [x] Fixing codes
- [x] ~~Option to select node or dumb method~~ (No longer option possible Node is required)
- [ ] Maybe making a proper package :thinking:
- [x] Option for adding anime for future checking ?
- [x] Fix download indicator segments
- [x] ~~Fix download indicator main indicator~~
- [x] ~~New issue with ffmpeg trouble with audio , AAC codec issue~~
- [ ] Change the default download location ? :thinking: or as an option ?
- [x] Resuming Capability
- [ ] Some problem with naming scheme
- [x] What if no quality present ?
