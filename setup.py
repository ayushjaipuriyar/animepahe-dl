
import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="anime_downloader",
    version="0.1.0",
    author="Ayush",
    author_email="ayush@example.com",
    description="A simple anime downloader",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pypa/sampleproject",
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
