#!/bin/bash

sudo apt-get install virtualenv python3-dev libreoffice maven tesseract-ocr tesseract-ocr-eng tesseract-ocr-ita tesseract-ocr-fra tesseract-ocr-spa tesseract-ocr-deu tesseract-ocr-rus

# ensure this is the expected Python executable
virtualenv -p /usr/local/bin/python3.6 venv


source venv/bin/activate
pip install -U setuptools
pip install -r requirements.txt

# Assume lexnlp core project is at ../../lexpredict-contraxsuite-core/
pip install -c requirements.txt -e ../../lexpredict-contraxsuite-core/
pip install -e ../text_extraction_system_api

# NLTK should be installed within lexpredict-contraxsuite-core
# The following downloads its models
python3 -m nltk.downloader averaged_perceptron_tagger punkt stopwords words maxent_ne_chunker wordnet omw-1.4

# Downloading model for language detection
mkdir models
wget https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin -O ./models/lid.176.bin

./build_java_modules.sh
