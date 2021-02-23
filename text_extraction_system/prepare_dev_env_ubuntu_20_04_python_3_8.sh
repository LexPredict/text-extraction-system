#!/bin/bash

sudo apt-get install virtualenv python3-dev libreoffice maven tesseract-ocr tesseract-ocr-eng tesseract-ocr-ita tesseract-ocr-fra tesseract-ocr-spa tesseract-ocr-deu tesseract-ocr-rus


# ensure this is the expected Python executable
virtualenv -p /usr/bin/python3 venv


source venv/bin/activate
pip install -r requirements.txt

# Assume lexnlp core project is at ../../lexpredict-contraxsuite-core/
# For some reason -c did not work on 18.04. Installing lexnlp with
# --no-deps because we already have them in requirements.
# pip install -c requirements.txt -e ../../lexpredict-contraxsuite-core/
pip install --no-deps -e ../../lexpredict-contraxsuite-core/

pip install -e ../text_extraction_system_api

# NLTK should be installed within lexpredict-contraxsuite-core
# The following downloads its models
python3 -m nltk.downloader averaged_perceptron_tagger punkt stopwords words maxent_ne_chunker wordnet

# Downloading model for language detection
mkdir models
wget https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin -O ./models/lid.176.bin

./build_java_modules.sh
