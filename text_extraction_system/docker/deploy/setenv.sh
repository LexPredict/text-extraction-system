#!/bin/bash
echo "Applying setenv.sh..."

export DOLLAR=$

export TEXT_EXTRACTION_STACK_NAME=text_extraction

export TEXT_EXTRACTION_SYSTEM_ROOT_PATH=/text_extraction_system
export TEXT_EXTRACTION_SYSTEM_IMAGE=lexpredict/lexpredict-text-extraction-system:latest
export TEXT_EXTRACTION_SWARM_NETWORK=contraxsuite_contrax_net

export TEXT_EXTRACTION_SYSTEM_DELETE_TEMP_FILES_ON_REQUEST_FINISHED=true
export TEXT_EXTRACTION_SYSTEM_KEEP_FAILED_FILES=true

export DOCKER_COMPOSE_FILE=docker-compose-backend-develop.yml

export DOCKER_REDIS_IMAGE=redis:6.0.9
export DOCKER_REDIS_HOST_NAME=tes_redis

export DOCKER_WEBDAV_HOSTNAME=tes_webdav
export DOCKER_WEBDAV_PORT=8765
export DOCKER_WEBDAV_IMAGE=lexpredict/nginx-webdav:1.19.6
#export DOCKER_WEBDAV_AUTH_USER=$(uuidgen)
#export DOCKER_WEBDAV_AUTH_PASSWORD=$(uuidgen)
export DOCKER_WEBDAV_AUTH_USER=user
export DOCKER_WEBDAV_AUTH_PASSWORD=password

export DOCKER_MASTER_NODE_IP=$(docker node inspect self --format '{{ .Status.Addr  }}')

CUSTOM_SETTINGS_FILE=setenv_local.sh
if [[ -f "${CUSTOM_SETTINGS_FILE}"  ]]; then
  echo "Applying ${CUSTOM_SETTINGS_FILE}..."
  source ${CUSTOM_SETTINGS_FILE}
else
  echo "There is no ${CUSTOM_SETTINGS_FILE} in the current dir."
fi
