#!/bin/bash

# Before running, you need to be sure that you have XCode installed (latest version is recommended)
brew install python@3.8
brew install maven
brew install postgresql

# it is required for `docker/deploy/deploy-to-swarm-cluster.sh` 'envsubst' command
brew install gettext
brew link --force gettext

# ensure this is the expected Python executable
virtualenv -p /usr/bin/python3 venv

# activate environment
source venv/bin/activate

# install requirements
pip install -r requirements.txt

# Assume lexnlp core project is at ../../lexpredict-contraxsuite-core/
# For some reason -c did not work on 18.04. Installing lexnlp with
# --no-deps because we already have them in requirements.
# pip install -c requirements.txt -e ../../lexpredict-contraxsuite-core/
pip install --no-deps -e ../../lexpredict-contraxsuite-core/

pip install -e ../text_extraction_system_api

mkdir models
curl https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin -o ./models/lid.176.bin

mkdir -p java_modules

pushd text_extraction_system_java
mvn clean package dependency:copy-dependencies

rm ../java_modules/*.jar
cp target/text_extraction_system_java-1.0.jar ../java_modules/
cp target/dependency/* ../java_modules/
popd
