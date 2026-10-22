#!/bin/bash
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

set -euo pipefail

sudo snap install charmcraft --classic --channel=latest/edge
CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS=1 charmcraft fetch-libs
