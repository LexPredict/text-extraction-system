#!/bin/bash
set -e
source setenv.sh

sudo -E docker stack rm ${TEXT_EXTRACTION_STACK_NAME}
