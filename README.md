# animepahe-dl

Python program to download anime from [AnimePahe](https://animepah.com)

## Table of contents

- [animepahe-dl](#animepahe-dl)
  - [Table of contents](#table-of-contents)
  - [Requirements](#requirements)
    - [How to Use](#how-to-use)
  - [Examples](#examples)
  - [Todos](#todos)

## Requirements

```
node (optional)
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

## Todos

---

- [x] ~~Trying to get rid of Node.js as a dependency~~
- [x] ~~Fixing multiple entries of same anime in the myanimelist for checking for updates~~
- [ ] Fixing codes
- [ ] Option to select node or dumb method
- [ ] Maybe making a proper package :thinking:
- [ ] Option for adding anime for future checking ?
- [ ] Fix download indicator
