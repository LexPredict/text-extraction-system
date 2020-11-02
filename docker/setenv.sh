#!/bin/bash
echo "Applying setenv.sh..."

export DOLLAR=$

export TEXT_EXTRACTION_SWARM_NETWORK=contraxsuite_contrax_net

export DOCKER_COMPOSE_FILE=docker-compose-backend-develop.yml

export DOCKER_REDIS_IMAGE=redis:6.0.9
export DOCKER_REDIS_HOST_NAME=tes_redis

export DOCKER_WEBDAV_HOSTNAME=tes_webdav
export DOCKER_WEBDAV_IMAGE=bytemark/webdav:2.4
export DOCKER_WEBDAV_AUTH_USER=user
export DOCKER_WEBDAV_AUTH_PASSWORD=password

CUSTOM_SETTINGS_FILE=setenv_local.sh
if [[ -f "${CUSTOM_SETTINGS_FILE}"  ]]; then
  echo "Applying ${CUSTOM_SETTINGS_FILE}..."
  source ${CUSTOM_SETTINGS_FILE}
else
  echo "There is no ${CUSTOM_SETTINGS_FILE} in the current dir."
fi
