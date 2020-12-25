#!/bin/bash

sudo apt-get install virtualenv libpq-dev python3-dev img2pdf libreoffice maven

# img2pdf is under LGPLv3. Allows using it as a separate component in the system.
# img2pdf is executed as a subprocess.