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
pip install virtualenv
# For python-magic
brew install libmagic

# Install Java stuff
brew install openjdk@8
sudo ln -sfn /usr/local/opt/openjdk@8/libexec/openjdk.jdk /Library/Java/JavaVirtualMachines/openjdk-8.jdk
brew install maven

# Install Libre Office tools
sudo port install libreoffice

# ensure this is the expected Python executable
virtualenv -p /usr/local/bin/python3.10 venv

source venv/bin/activate
pip install -U setuptools
pip install -r requirements.txt
pip install -e ../text_extraction_system_api/
pip install --no-deps -e ../../lexpredict-contraxsuite-core/

# NLTK should be installed within lexpredict-contraxsuite-core. The following downloads its models
bash /Applications/Python\ 3.10/Install\ Certificates.command
python3 -m nltk.downloader averaged_perceptron_tagger punkt stopwords words maxent_ne_chunker wordnet

# Downloading model for language detection
mkdir models
wget https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin -O ./models/lid.176.bin

./build_java_modules.sh
