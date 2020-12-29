#!/bin/bash

export TEXT_EXTRACTION_SYSTEM_IMAGE=lexpredict/lexpredict-text-extraction-system:latest
export TEXT_EXTRACTION_SYSTEM_IMAGE_FROM=ubuntu:20.04
export DOCKER_BUILD_FLAGS=

export TEXT_EXTRACTION_SYSTEM_GIT_COMMIT=unknown
export TEXT_EXTRACTION_SYSTEM_VERSION=0.0.0

export SHARED_USER_ID=65432
export SHARED_USER_NAME=text_extraction_user

if [ -f build_setenv_local.sh ]
then
    echo "Loading build_setenv_local.sh"
    source build_setenv_local.sh
fi
