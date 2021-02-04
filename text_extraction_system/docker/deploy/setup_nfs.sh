#!/bin/bash
set -e

sudo apt-get install nfs-kernel-server nfs-common -y
sudo mkdir -p /data/nfs/text_extraction
sudo chown -R nobody:nogroup /data/nfs/text_extraction

s="/data/nfs/text_extraction *(rw,sync,no_subtree_check)"
grep -q -F "${s}" /etc/exports || echo "${s}" | sudo tee --append /etc/exports

sudo systemctl restart nfs-kernel-server
sudo systemctl enable nfs-kernel-server


wget https://github.com/ContainX/docker-volume-netshare/releases/download/v0.36/docker-volume-netshare_0.36_amd64.deb -O /tmp/docker-volume-netshare_0.36_amd64.deb
sudo dpkg -i /tmp/docker-volume-netshare_0.36_amd64.deb
sudo service docker-volume-netshare start
sudo rm -rf /tmp/docker-volume-netshare_0.36_amd64.deb