
import setuptools
import re

with open("README.md", "r") as fh:
    long_description = fh.read()

def get_version():
    with open("anime_downloader/__init__.py", "r") as f:
        return re.search(r'__version__\s*=\s*[\'\"]([^\'\"]*)[\'\"]', f.read()).group(1)

setuptools.setup(
    name="anime_downloader",
    version=get_version(),
    author="Ayush",
    author_email="ayushjaipuriyar21@gmail.com",
    description="A simple anime downloader",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ayushjaipuriyar/animepahe-dl",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=[
        "beautifulsoup4",
        "pyfzf",
        "pycryptodome",
        "tqdm",
        "urllib3",
        "PyQt6",
        "platformdirs",
        "loguru",
        "plyer",
        "questionary",
    ],
    entry_points={
        'console_scripts': [
            'anime-downloader = anime_downloader.main:main',
        ],
    },
)
