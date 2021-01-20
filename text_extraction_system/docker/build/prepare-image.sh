#!/bin/bash
set -e

source build_setenv.sh

echo "Image name: ${TEXT_EXTRACTION_SYSTEM_IMAGE}"
export DOLLAR='$' # escape $ in envsubst

if [[ "${INSTALL_LEXNLP_MASTER,,}" = "true" ]]; then
    export LEXNLP_MASTER_INSTALL_CMD="&& pip install -r requirements-lexnlp.txt"
else
    export LEXNLP_MASTER_INSTALL_CMD=""
fi

# Docker is not allowed to access files in the parent dir
# Preparing files in a temp dir
rm -f -r ./temp
mkdir -p ./temp

mkdir -p ./temp/text_extraction_system



rsync --exclude='.git/' ../../text_extraction_system ./temp/text_extraction_system -a --copy-links -v
rsync --exclude='.git/' ../../../text_extraction_system_api ./temp -a --copy-links -v

# Build java modules
pushd ../../text_extraction_system_java
mvn clean package dependency:copy-dependencies
rm -f ../java_modules/*.jar
mkdir -p ../java_modules
cp target/text_extraction_system_java-1.0.jar ../java_modules/
cp target/dependency/* ../java_modules/
popd
rsync --exclude='.git/' ../../java_modules ./temp -a --copy-links -v


cp ../../requirements.txt ./temp/
cp ../../.env.local_dev_example ./temp

if [[ "${LEXNLP_PROJECT_PATH}" == "" ]]; then
  echo "Will install lexnlp from its GIT repo..."
  cp ../../requirements-lexnlp.txt ./temp/
  export LEXNLP_MASTER_INSTALL_CMD="pip install -c /requirements.txt -r /requirements-lexnlp.txt"
  export LEXNLP_COPY_CMD="COPY ./temp/requirements-lexnlp.txt /"
else
  echo "Copying lexnlp from ${LEXNLP_PROJECT_PATH}"
  mkdir -p ./temp/lexnlp
  rsync --exclude='.git/' --exclude='lexnlpprivate/' \
        --exclude='/lexnlp.egg-info/' \
        --exclude='/test_data/' \
        --exclude='/notebooks/' \
        --exclude='/docs/' \
        --exclude='/scripts/' \
        ${LEXNLP_PROJECT_PATH}/ ./temp/lexnlp -a --copy-links -v
  export LEXNLP_MASTER_INSTALL_CMD="pip install -c /requirements.txt -e /lexnlp"
  export LEXNLP_COPY_CMD="COPY ./temp/lexnlp /lexnlp"
fi


echo "VERSION_NUMBER = '${TEXT_EXTRACTION_SYSTEM_VERSION}'" > ./temp/text_extraction_system/text_extraction_system/version.py

echo "GIT_BRANCH = '${TEXT_EXTRACTION_SYSTEM_GIT_BRANCH}'" >> ./temp/text_extraction_system/text_extraction_system/version.py
echo "GIT_COMMIT = '${TEXT_EXTRACTION_SYSTEM_GIT_COMMIT}'" >> ./temp/text_extraction_system/text_extraction_system/version.py

echo "LEXNLP_GIT_BRANCH = '${LEXNLP_GIT_BRANCH}'" >> ./temp/text_extraction_system/text_extraction_system/version.py
echo "LEXNLP_GIT_COMMIT = '${LEXNLP_GIT_COMMIT}'" >> ./temp/text_extraction_system/text_extraction_system/version.py

echo "BUILD_DATE = '$(date --rfc-3339=seconds)'" >> ./temp/text_extraction_system/text_extraction_system/version.py

# Preparing docker swarm deploy config bundled within the image
rsync --exclude='.git/' \
      --exclude='temp/' \
      --exclude='setenv_local.local_dev_example.sh' \
      --exclude='setenv_local.sh' \
      ../deploy/ ./temp/deploy-docker-swarm -a --copy-links -v
sed -i "/TEXT_EXTRACTION_SYSTEM_IMAGE/ c\export TEXT_EXTRACTION_SYSTEM_IMAGE=${TEXT_EXTRACTION_SYSTEM_IMAGE}" ./temp/deploy-docker-swarm/setenv.sh
sed -i "/DOCKER_COMPOSE_FILE/ c\export DOCKER_COMPOSE_FILE=docker-compose.yml" ./temp/deploy-docker-swarm/setenv.sh



envsubst < Dockerfile.template > Dockerfile
envsubst < start.template.sh > ./temp/start.sh
sudo docker build ${DOCKER_BUILD_FLAGS} --no-cache -t ${TEXT_EXTRACTION_SYSTEM_IMAGE} .

rm -f -r ./temp
rm -f -r Dockerfile
