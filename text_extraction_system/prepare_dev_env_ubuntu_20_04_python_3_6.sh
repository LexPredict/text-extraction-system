#!/bin/bash

sudo apt-get install virtualenv libpq-dev python3-dev img2pdf libreoffice maven libpoppler-dev poppler-utils
virtualenv -p /usr/local/bin/python3.6 venv
source venv/bin/activate
pip install -U setuptools
pip install -r requirements.txt

# Assume lexnlp core project is at ../../lexpredict-contraxsuite-core/
pip install -c requirements.txt -e ../../lexpredict-contraxsuite-core/
pip install -e ../text_extraction_system_api

wget https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin -O ./models/lid.176.bin

./prepare_tika.sh
