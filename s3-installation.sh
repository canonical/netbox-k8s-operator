#!/bin/bash
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

set -euo pipefail

S3_ACCESS_KEY="test-access-key"
S3_SECRET_KEY="test-secret-key"
S3_BUCKET="netboxbucket"

sudo snap install microceph
sudo microceph cluster bootstrap
sudo microceph disk add loop,1G,3
sudo microceph enable rgw --port 7480 --wait
sudo microceph.ceph config set client rgw_dns_name s3.localhost.localstack.cloud

sudo snap restart microceph.rgw

# Allow Kubernetes workloads to reach RGW on the test host.
sudo iptables --check INPUT -p tcp --dport 7480 -j ACCEPT 2>/dev/null ||
    sudo iptables --insert INPUT -p tcp --dport 7480 -j ACCEPT

curl --connect-timeout 2 --max-time 3 --retry 5 --retry-delay 2 \
    --retry-connrefused -s http://127.0.0.1:7480

sudo microceph.radosgw-admin user create \
    --uid netbox-ci \
    --display-name "NetBox CI" \
    --access-key "${S3_ACCESS_KEY}" \
    --secret-key "${S3_SECRET_KEY}"

curl -sf -X PUT "http://127.0.0.1:7480/${S3_BUCKET}" \
    --aws-sigv4 "aws:amz:us-east-1:s3" \
    --user "${S3_ACCESS_KEY}:${S3_SECRET_KEY}"
