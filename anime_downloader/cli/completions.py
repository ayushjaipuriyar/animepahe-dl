"""
Shell completion support for animepahe-dl.

This module provides shell completion functionality for bash, zsh, and fish.
"""

import os
import sys
from typing import List, Optional
from ..utils.config_manager import load_config
from ..api import AnimePaheAPI


def get_anime_suggestions(incomplete: str = "") -> List[str]:
    """Get anime name suggestions for completion."""
    try:
        # Load from cache if available
        cache_file = os.path.join(os.path.expanduser("~/.config/anime_downloader"), "animelist.txt")
        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as f:
                anime_list = []
                for line in f:
                    if "::::" in line:
                        _, title = line.strip().split("::::", 1)
                        if incomplete.lower() in title.lower():
                            anime_list.append(title)
                return anime_list[:10]  # Limit to 10 suggestions
    except Exception:
        pass
    return []


def get_quality_options() -> List[str]:
    """Get available quality options."""
    return ["best", "1080", "720", "480", "360"]


def get_audio_options() -> List[str]:
    """Get available audio options."""
    return ["jpn", "eng"]


def generate_bash_completion() -> str:
    """Generate bash completion script."""
    return '''
_animepahe_dl_completion() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    opts="-h --help -n --name -e --episodes -q --quality -a --audio -t --threads -c --concurrent-downloads --updates --manage --run-once --insecure --m3u8-only --single --gui"

    case "${prev}" in
        -q|--quality)
            COMPREPLY=( $(compgen -W "best 1080 720 480 360" -- ${cur}) )
            return 0
            ;;
        -a|--audio)
            COMPREPLY=( $(compgen -W "jpn eng" -- ${cur}) )
            return 0
            ;;
        -n|--name)
            # Could add anime name completion here
            return 0
            ;;
        *)
            ;;
    esac

    COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
    return 0
}

complete -F _animepahe_dl_completion animepahe-dl
'''


def generate_zsh_completion() -> str:
    """Generate zsh completion script."""
    return '''
#compdef animepahe-dl

_animepahe_dl() {
    local context state line
    typeset -A opt_args

    _arguments -C \
        '(-h --help)'{-h,--help}'[Show help message]' \
        '(-n --name)'{-n,--name}'[Name of anime to search]:anime name:' \
        '(-e --episodes)'{-e,--episodes}'[Episode numbers to download]:episodes:' \
        '(-q --quality)'{-q,--quality}'[Video quality]:quality:(best 1080 720 480 360)' \
        '(-a --audio)'{-a,--audio}'[Audio language]:audio:(jpn eng)' \
        '(-t --threads)'{-t,--threads}'[Number of download threads]:threads:' \
        '(-c --concurrent-downloads)'{-c,--concurrent-downloads}'[Concurrent downloads]:concurrent:' \
        '--updates[Check for new episodes]' \
        '--manage[Manage anime list]' \
        '--run-once[Run update check once]' \
        '--insecure[Disable SSL verification]' \
        '--m3u8-only[Fetch playlist only]' \
        '--single[Single selection mode]' \
        '--gui[Launch GUI]'
}

_animepahe_dl "$@"
'''


def install_completions():
    """Install shell completions."""
    shell = os.environ.get('SHELL', '').split('/')[-1]
    
    if shell == 'bash':
        completion_dir = os.path.expanduser("~/.bash_completion.d")
        os.makedirs(completion_dir, exist_ok=True)
        completion_file = os.path.join(completion_dir, "animepahe-dl")
        with open(completion_file, 'w') as f:
            f.write(generate_bash_completion())
        print(f"Bash completion installed to {completion_file}")
        print("Add 'source ~/.bash_completion.d/animepahe-dl' to your ~/.bashrc")
    
    elif shell == 'zsh':
        completion_dir = os.path.expanduser("~/.zsh/completions")
        os.makedirs(completion_dir, exist_ok=True)
        completion_file = os.path.join(completion_dir, "_animepahe-dl")
        with open(completion_file, 'w') as f:
            f.write(generate_zsh_completion())
        print(f"Zsh completion installed to {completion_file}")
        print("Add 'fpath=(~/.zsh/completions $fpath)' to your ~/.zshrc")
    
    else:
        print(f"Shell completions not supported for {shell}")
        print("Supported shells: bash, zsh")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "install":
        install_completions()
    else:
        print("Usage: python -m anime_downloader.completions install")