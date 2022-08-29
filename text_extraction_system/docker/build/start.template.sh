#!/bin/bash

set -e

echo ""
echo "==================================================================="
echo "LexPredict Text Extraction System"
echo "==================================================================="

COPY_DST_DIR=/deploy_scripts_dst

function print_usage () {
  echo ""
  echo "Usage:"
  echo ""
  echo "Gnerate example deployment scripts for Docker Swarm:"
  echo "mkdir -p ./deploy_swarm && docker run --rm -it -v \$(pwd)/deploy_swarm:${DOLLAR}{COPY_DST_DIR} ${TEXT_EXTRACTION_SYSTEM_IMAGE} generate-swarm-scripts"
  echo " or with sudo if needed:"
  echo "mkdir -p ./deploy_swarm && sudo docker run --rm -it -v \$(pwd)/deploy_swarm:${DOLLAR}{COPY_DST_DIR} ${TEXT_EXTRACTION_SYSTEM_IMAGE} generate-swarm-scripts"
  echo ""
  echo "Browse image internals:"
  echo "docker run --rm -it -v \$(pwd)/deploy_swarm:${DOLLAR}{COPY_DST_DIR} ${TEXT_EXTRACTION_SYSTEM_IMAGE} shell"
  echo ""
  echo "To have a working deployment of the Text Extraction System we need:"
  echo "- webdav server to use as the file storage;"
  echo "- redis server to use as the celery backend/broker (any other config can be tried too);"
  echo "- web-api server of the system to accept the HTTP API requests;"
  echo "- a number of celery workers to process the text extraction tasks."
  echo ""
  echo "Run web-api (uvicorn):"
  echo "docker run --rm -it --env-file env.list ${TEXT_EXTRACTION_SYSTEM_IMAGE} web-api"
  echo ""
  echo "Run celery worker:"
  echo "docker run --rm -it --env-file env.list ${TEXT_EXTRACTION_SYSTEM_IMAGE} celery-worker"
  echo ""
  echo "...where the contents of env.list is similar to:"
  echo "---"
  cat /.env.local_dev_example
  echo "---"
  echo "Please take into account that celery broker/backend and webdav addresses need to be accessible from inside the container."
  echo "You can use the generated Docker Swarm config to quickly get the working system."
}

CPU_CORES=${DOLLAR}(grep -c ^processor /proc/cpuinfo)
CPU_QUARTER_CORES=${DOLLAR}(( ${DOLLAR}{CPU_CORES} > 4 ? ${DOLLAR}{CPU_CORES} / 4 : 1 ))
SHARED_USER_NAME=$(whoami)

ROLE=${DOLLAR}1
echo "${DOLLAR}{ROLE}"
echo ""

function startup () {
  echo "Starting: $DOLLAR{ROLE}"
  echo "Working as user: ${DOLLAR}{SHARED_USER_NAME} (id=${DOLLAR}(id -u ${DOLLAR}{SHARED_USER_NAME}))"
  if [[ -z "${DOLLAR}{STARTUP_DEPS_READY_CMD}" ]]; then
      echo "No dependencies specified to wait. Starting up..."
  else
      echo "Dependencies readiness test command: ${DOLLAR}{STARTUP_DEPS_READY_CMD}"
      while ! eval ${DOLLAR}{STARTUP_DEPS_READY_CMD}
      do
        echo "Dependencies are not ready. Waiting 5 seconds..."
        sleep 5
      done
      echo "Dependencies are ready. Starting up..."
  fi
  echo "Check Launch Type ..."
  if [[ -z "${DOLLAR}{LAUNCH_TYPE}" ]]; then
      echo "Set ulimit to 65535"
      ulimit -n 65535
  elif [[ "${DOLLAR}{LAUNCH_TYPE}" == "ECS" ]]; then
      echo "Starting on ECS Platform. Ulimit is set on task level"
  else
      echo '$LAUNCH_TYPE should be ECS or undefined'
      exit 1
  fi
}

if [ "${DOLLAR}{ROLE}" == "unit_tests" ]; then
  startup
  exec pytest text_extraction_system
elif [ "${DOLLAR}{ROLE}" == "signal-debug" ]; then
  startup
  exec python3 text_extraction_system/signal_debug.py
elif [ "${DOLLAR}{ROLE}" == "web-api" ]; then
  startup
  pushd .
  cd text_extraction_system/templates
  echo "New SPA subfolder is [${DOLLAR}{text_extraction_system_root_path:1}]"
  sed -i "s/TEXT_EXTRACTION_SPA_SUBDIRECTORY/${DOLLAR}{text_extraction_system_root_path:1}/g" bundle.js
  popd
  exec uvicorn --host 0.0.0.0 --port 8000 --root-path ${DOLLAR}{text_extraction_system_root_path} text_extraction_system.web_api:app
elif [ "${DOLLAR}{ROLE}" == "celery-worker" ]; then
  startup
  if [[ -z "${DOLLAR}{CELERY_CPU_CORES_NUMBER}" ]]; then
    echo "CELERY_CPU_CORES_NUMBER is unset, setting to 1"
    CELERY_CPU_CORES_NUMBER=${DOLLAR}{CPU_QUARTER_CORES}
  fi
  if [[ -z "${DOLLAR}{CELERY_WORKERS_NUMBER}" ]]; then
    echo "CELERY_WORKERS_NUMBER is unset, setting to 1"
    CELERY_WORKERS_NUMBER=1
  fi
  echo "Start ${DOLLAR}{CELERY_WORKERS_NUMBER} workers, concurrency=${DOLLAR}{CELERY_CPU_CORES_NUMBER}"
  for (( i=1; i<=${DOLLAR}((${DOLLAR}{CELERY_WORKERS_NUMBER} - 1)); i++ ))
  do
    celery -A text_extraction_system.tasks worker \
      -X beat \
      -l INFO \
      -c ${DOLLAR}{CELERY_CPU_CORES_NUMBER} \
      -n celery-${DOLLAR}{i}@%h \
      -S /data/celery_worker_state/celery-worker-state-${DOLLAR}{i}-${DOLLAR}{HOSTNAME}.db &
  done
  exec celery -A text_extraction_system.tasks worker \
      -X beat \
      -l INFO \
      -c ${DOLLAR}{CELERY_CPU_CORES_NUMBER} \
      -n celery-${DOLLAR}{CELERY_WORKERS_NUMBER}@%h \
      -S /data/celery_worker_state/celery-worker-state-${DOLLAR}{CELERY_WORKERS_NUMBER}-${DOLLAR}{HOSTNAME}.db
elif [ "${DOLLAR}{ROLE}" == "celery-beat" ]; then
  startup
   exec celery -A text_extraction_system.tasks worker \
      -B \
      -Q beat \
      -l INFO \
      -c 1 \
      -n beat@%h \
      -S /data/celery_worker_state/celery-beat-state-${DOLLAR}{HOSTNAME}.db
elif [ "${DOLLAR}{ROLE}" == "generate-swarm-scripts" ]; then
  echo "Copying Docker Swarm deployment scripts to the mounted volume at: ${DOLLAR}{COPY_DST_DIR}..."
  if [[ ! -d /deploy_scripts_dst  ]]; then
    echo "Directory does not exist: ${DOLLAR}{COPY_DST_DIR}"
    echo "Did you mount a volume to this path?"
    echo ""
    print_usage
  else
    cp -r /deploy-docker-swarm/* ${DOLLAR}{COPY_DST_DIR}/
    echo "Done."
    ls -l ${DOLLAR}{COPY_DST_DIR}
  fi

elif [ "${DOLLAR}{ROLE}" == "shell" ]; then
  echo "Starting bash..."
  exec /bin/bash
else
  print_usage
fi
