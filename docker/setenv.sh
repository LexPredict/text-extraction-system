#!/bin/bash
echo "Applying setenv.sh..."

export DOLLAR=$

export TEXT_EXTRACTION_SWARM_NETWORK=contraxsuite_contrax_net

export DOCKER_COMPOSE_FILE=docker-compose-backend-develop.yml

export DOCKER_RABBITMQ_IMAGE=rabbitmq:3-management
export DOCKER_RABBITMQ_USER=user
export DOCKER_RABBITMQ_PASSWORD=password
export DOCKER_RABBITMQ_HOSTNAME=tes_rabbitmq
export DOCKER_RABBITMQ_VHOST=vhost_tes

export DOCKER_PG_HOSTNAME=tes_postgres
export DOCKER_PG_IMAGE=postgres:13.0
export DOCKER_PG_USER=tes1
export DOCKER_PG_PASSWORD=tes1
export DOCKER_PG_DB_NAME=tes1

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
