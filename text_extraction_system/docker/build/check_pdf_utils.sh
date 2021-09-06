#!/bin/bash

CONTRAX_FILE_STORAGE_WEBDAV_ROOT_URL=http://${DOCKER_WEBDAV_SERVER_NAME_ACCESS}:80

ensure_webdav_dir () {
  local PDF_UTIL_STATUS=$(curl -u $DOCKER_WEBDAV_AUTH_USER:$DOCKER_WEBDAV_AUTH_PASSWORD http://tasks.contrax-webdav:80/flags/pdfutils.txt)
  if [[ $PDF_UTIL_STATUS == "1" ]]; then
    echo "checking PDF utils"
    pdftocairo -help
    command_status=$?
    if [ "$command_status" -eq 0 ]; then
      echo "PDF utils are found"
    else
      echo "PDF utils are not found. Installing utils"
      sudo apt-get update -y && sudo apt-get install -y poppler-utils
    fi
  else
    echo "dont check PDF utils"
  fi
}
