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

PROJECT_DIR="/text_extraction_system"
VENV_PATH="/text_extraction_system/venv/bin/activate"
ACTIVATE_VENV="export LANG=C.UTF-8 && cd ${DOLLAR}{PROJECT_DIR} && . ${DOLLAR}{VENV_PATH} "
CPU_CORES=${DOLLAR}(grep -c ^processor /proc/cpuinfo)
CPU_QUARTER_CORES=${DOLLAR}(( ${DOLLAR}{CPU_CORES} > 4 ? ${DOLLAR}{CPU_CORES} / 4 : 1 ))

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
}

pushd ${DOLLAR}{PROJECT_DIR}


if [ "${DOLLAR}{ROLE}" == "unit_tests" ]; then
  startup
  su ${SHARED_USER_NAME} -c "${DOLLAR}{ACTIVATE_VENV} && ulimit -n 65535 && pytest text_extraction_system"
elif [ "${DOLLAR}{ROLE}" == "signal_debug" ]; then
  startup
  su ${SHARED_USER_NAME} -c "${DOLLAR}{ACTIVATE_VENV} && ulimit -n 65535 && python text_extraction_system/signal_debug.py"
elif [ "${DOLLAR}{ROLE}" == "web-api" ]; then
  startup
  su ${SHARED_USER_NAME} -c "${DOLLAR}{ACTIVATE_VENV} && ulimit -n 65535 && uvicorn --host 0.0.0.0 --port 8000 text_extraction_system.web_api:app"
elif [ "${DOLLAR}{ROLE}" == "celery-worker" ]; then
  startup
  mkdir -p /data/celery_worker_state/db
  chown ${SHARED_USER_NAME}:${SHARED_USER_NAME} /data/celery_worker_state/db
  su ${SHARED_USER_NAME} -c "${DOLLAR}{ACTIVATE_VENV} && \
   ulimit -n 65535 && \
   celery -A text_extraction_system.tasks worker \
      -l INFO \
      --concurrency=${DOLLAR}{CPU_QUARTER_CORES} \
      -Ofair \
      -n celery@%h \
      --statedb=/data/celery_worker_state/db/celery-worker-state-${DOLLAR}{HOSTNAME}.db"
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
  /bin/bash
else
  print_usage
fi
