#!/bin/bash

OS_NAME=$(awk -F= '/^NAME/{print $2}' /etc/os-release)
OS_VERSION=$(awk -F= '/^VERSION_ID/{print $2}' /etc/os-release)
PYTHON3_VERSION="$(python3 -V 2>&1)"

# Install python, office, maven and tesseract
sudo apt-get install virtualenv python3-dev libreoffice maven tesseract-ocr tesseract-ocr-eng \
                     tesseract-ocr-ita tesseract-ocr-fra tesseract-ocr-spa tesseract-ocr-deu \
                     tesseract-ocr-rus

# Prepare python virtual env
virtualenv -p /usr/bin/python3 .venv
source .venv/bin/activate
pip install -U wheel
pip install -U setuptools
pip install -U -r requirements.txt

# Install additional python packages
pip install -U --no-deps -e ../../lexpredict-contraxsuite-core/
pip install -U -e ../text_extraction_system_api

# NLTK should be installed within lexpredict-contraxsuite-core. The following downloads its models
python3 -m nltk.downloader averaged_perceptron_tagger punkt stopwords words maxent_ne_chunker \
                           wordnet omw-1.4

deactivate

# Downloading model for language detection
mkdir models
wget https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin -O ./models/lid.176.bin

# Build TES java modules
sudo ./build_java_modules.sh

# Prepare env files
cp ./docker/deploy/setenv_local.local_dev_example.sh ./docker/deploy/setenv_local.sh
cp ./docs/.env.local_dev_example .env
cp .test_env.local_dev_example .test_env

# Prepare docker containers
docker swarm init
docker network create --driver overlay contraxsuite_contrax_net

pushd docker/deploy
sudo ./deploy-to-swarm-cluster.sh
popd

#if [[ ("$OS_NAME" == "\"Ubuntu\"") && (("$OS_VERSION" == "\"18.04\"") || ("$OS_VERSION" == "\"20.04\"")) ]]; then
#  echo $OS_NAME
#  echo $OS_VERSION
#fi

#if [[ "$PYTHON3_VERSION" == "Python 3.8"* ]]; then
#  echo $PYTHON3_VERSION
#fi