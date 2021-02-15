#!/bin/bash

sudo apt-get install virtualenv libpq-dev python3-dev img2pdf libreoffice maven


# ensure this is the expected Python executable
virtualenv -p /usr/bin/python3 venv


source venv/bin/activate
pip install -r requirements.txt

# Assume lexnlp core project is at ../../lexpredict-contraxsuite-core/
pip install -c requirements.txt -e ../../lexpredict-contraxsuite-core/
pip install -e ../text_extraction_system_api


mkdir models
wget https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin -O ./models/lid.176.bin

./build_java_modules.sh
