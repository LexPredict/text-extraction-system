#!/bin/bash

# to be executed as root in docker/deploy dir

set -e

pushd ../  # /text_extraction_system

source setenv.sh
popd  # /docker

mkdir -p ./temp
echo "Starting with docker-compose config: ${DOCKER_COMPOSE_FILE}"
envsubst < ./docker-compose-templates/${DOCKER_COMPOSE_FILE} > ./temp/${DOCKER_COMPOSE_FILE}
docker stack deploy --compose-file ./temp/${DOCKER_COMPOSE_FILE} text_extraction --with-registry-auth

echo "Deploy routines have been completed"
