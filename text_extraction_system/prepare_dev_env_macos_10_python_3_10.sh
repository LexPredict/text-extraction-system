#!/bin/bash

# Mac minimum system requirements: RAM - 16gb, ROM - 256gb
# You need to have preinstalled MacPorts: https://www.macports.org/install.php

# Install Homebrew
curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh

# Add directory for manual installations
mkdir installers

# Install python and venv
brew install wget
brew install python@3.10
pip3 install virtualenv
# For python-magic
brew install libmagic

brew install qpdf
brew install tesseract

# Install Java stuff
brew install openjdk
brew install maven

# Required for successful python packages compilation
xcode-select --install

# Install Libre Office tools
sudo port install libreoffice

# ensure this is the expected Python executable
python3.10 -m venv .venv

source .venv/bin/activate
pip3 install -U wheel setuptools pip pipenv
pipenv install --deploy --dev
pip3 install --no-deps -e ../../lexpredict-contraxsuite-core/

# NLTK should be installed within lexpredict-contraxsuite-core. The following downloads its models
python3.10 -m nltk.downloader averaged_perceptron_tagger punkt stopwords words maxent_ne_chunker wordnet

# Downloading model for language detection
mkdir models
wget https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin -O ./models/lid.176.bin

./build_java_modules.sh
