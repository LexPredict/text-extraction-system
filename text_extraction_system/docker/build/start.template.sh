#!/bin/bash

set -e

PROJECT_DIR="/text_extraction_system"
VENV_PATH="/text_extraction_system/venv/bin/activate"
ACTIVATE_VENV="export LANG=C.UTF-8 && cd ${DOLLAR}{PROJECT_DIR} && . ${DOLLAR}{VENV_PATH} "
CPU_CORES=${DOLLAR}(grep -c ^processor /proc/cpuinfo)
CPU_QUARTER_CORES=${DOLLAR}(( ${DOLLAR}{CPU_CORES} > 4 ? ${DOLLAR}{CPU_CORES} / 4 : 1 ))

ROLE=${DOLLAR}2

if [[ "${DOLLAR}{ROLE}" == "" ]]; then
  ROLE=celery-worker
fi

echo ""
echo "==================================================================="
echo "Lexpredict Text Extraction System"
echo "Starting ${DOLLAR}{ROLE}..."
echo "==================================================================="
echo ""


echo "Working as user: ${DOLLAR}{SHARED_USER_NAME} (id=${DOLLAR}(id -u ${DOLLAR}{SHARED_USER_NAME}))"

pushd ${DOLLAR}{PROJECT_DIR}

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

if [ "${DOLLAR}{ROLE}" == "unit_tests" ]; then
  su ${SHARED_USER_NAME} -c "${DOLLAR}{ACTIVATE_VENV} && pytest text_extraction_system"
elif [ "${DOLLAR}{ROLE}" == "web-api" ]; then
  su ${SHARED_USER_NAME} -c "${DOLLAR}{ACTIVATE_VENV} && uvicorn text_extraction_system.web_api:app --reload"
elif [ "${DOLLAR}{ROLE}" == "celery-worker" ]; then
  su ${SHARED_USER_NAME} -c "${DOLLAR}{ACTIVATE_VENV} && celery -A text_extraction_system.tasks worker --concurrency 1 -l INFO"
fi
