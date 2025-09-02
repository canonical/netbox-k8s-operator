#!/bin/bash
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

# This script downloads and extracts the NetBox source code.
NETBOX_VERSION="4.3.6"
wget https://github.com/netbox-community/netbox/archive/refs/tags/v${NETBOX_VERSION}.tar.gz
if [ -d "netbox-k8s" ]; then
    rm -rf netbox-k8s
fi
mkdir netbox-k8s
tar -xzvf v${NETBOX_VERSION}.tar.gz --strip-components=1 -C netbox-k8s
patch -p1 <patches/settings.patch
patch -p1 <patches/requirements.patch

# Initiate Rockcraft 
cp netbox_rockcraft.yaml netbox-k8s/rockcraft.yaml
# Update the rockcraft.yaml with the correct version
sed -i "s/^version: \".*\"/version: \"${NETBOX_VERSION}\"/" netbox-k8s/rockcraft.yaml

# Set up the cron job
cp -r cron.d netbox-k8s/

cp configuration.py netbox-k8s/netbox/netbox/configuration.py

mv netbox-k8s/upgrade.sh netbox-k8s/migrate.sh