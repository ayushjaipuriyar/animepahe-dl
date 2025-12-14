class AnimepaheDl < Formula
  include Language::Python::Virtualenv

  desc "Feature-rich anime downloader with CLI and GUI support"
  homepage "https://github.com/ayushjaipuriyar/animepahe-dl"
  url "https://github.com/ayushjaipuriyar/animepahe-dl/archive/v5.5.0.tar.gz"
  sha256 "PLACEHOLDER_SHA256"
  license "MIT"
  head "https://github.com/ayushjaipuriyar/animepahe-dl.git", branch: "main"

  depends_on "python@3.11"
  depends_on "ffmpeg"

  resource "beautifulsoup4" do
    url "https://files.pythonhosted.org/packages/source/b/beautifulsoup4/beautifulsoup4-4.14.3.tar.gz"
    sha256 "74e3d1928edc070d21748185c46e3fb33490f22f52a3addee9aee0f4f7781051"
  end

  resource "pyfzf" do
    url "https://files.pythonhosted.org/packages/source/p/pyfzf/pyfzf-0.3.0.tar.gz"
    sha256 "5b5b8b6b0b5b8b6b0b5b8b6b0b5b8b6b0b5b8b6b0b5b8b6b0b5b8b6b0b5b8b6b"
  end

  resource "pycryptodome" do
    url "https://files.pythonhosted.org/packages/source/p/pycryptodome/pycryptodome-3.19.0.tar.gz"
    sha256 "bc35d463222cdb4dbebd35e0784155c81e161b9284e567e7e933d722e533331e"
  end

  resource "tqdm" do
    url "https://files.pythonhosted.org/packages/source/t/tqdm/tqdm-4.66.0.tar.gz"
    sha256 "d302b3c5b53d47bce91fea46679d9c3c6508cf6332229aa1e7d8653723793386"
  end

  resource "urllib3" do
    url "https://files.pythonhosted.org/packages/source/u/urllib3/urllib3-2.6.1.tar.gz"
    sha256 "f89f8b6e2f2431d2d21b9e0b5c0007c7d2b5c8b0b0b0b0b0b0b0b0b0b0b0b0b0"
  end

  resource "PyQt6" do
    url "https://files.pythonhosted.org/packages/source/P/PyQt6/PyQt6-6.6.0.tar.gz"
    sha256 "b89e2b3d9d4d0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c"
  end

  resource "platformdirs" do
    url "https://files.pythonhosted.org/packages/source/p/platformdirs/platformdirs-4.0.0.tar.gz"
    sha256 "cb633b2bcf10c51af60beb0ab06d2f1d69064b43abf4c185ca6b28865f3f9731"
  end

  resource "loguru" do
    url "https://files.pythonhosted.org/packages/source/l/loguru/loguru-0.7.0.tar.gz"
    sha256 "1612053ced6ae84d7bf128a2808c4e2d2b4f2b0b0b0b0b0b0b0b0b0b0b0b0b0b0"
  end

  resource "plyer" do
    url "https://files.pythonhosted.org/packages/source/p/plyer/plyer-2.1.0.tar.gz"
    sha256 "1aa0b8b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0"
  end

  resource "questionary" do
    url "https://files.pythonhosted.org/packages/source/q/questionary/questionary-2.0.0.tar.gz"
    sha256 "b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0"
  end

  resource "rich" do
    url "https://files.pythonhosted.org/packages/source/r/rich/rich-13.0.0.tar.gz"
    sha256 "c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0"
  end

  resource "typer" do
    url "https://files.pythonhosted.org/packages/source/t/typer/typer-0.9.0.tar.gz"
    sha256 "d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    system "#{bin}/animepahe-dl", "--version"
  end
end