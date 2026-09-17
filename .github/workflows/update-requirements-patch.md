---
on:
  pull_request:
    types: [opened, synchronize]
    branches:
      - main
    paths:
      - download_netbox.sh

permissions:
  contents: read
  issues: read
  pull-requests: read

tools:
  github:
    mode: gh-proxy
    toolsets: [default]

network:
  allowed:
    - github

safe-outputs:
  push-to-pull-request-branch:
    allowed-files:
      - patches/requirements.patch
  add-comment:
  noop:

---

# Update requirements.patch for New NetBox Minor Version

## Goal

When a pull request bumps the NetBox version in `download_netbox.sh`, regenerate
`patches/requirements.patch` so it applies cleanly against the new
`requirements.txt` from that version.

## Steps

1. If the pull request head branch is not `renovate/all-minor-patch`, call
   `noop` with a short explanation and stop.
   This exact branch name is intentional because the repository uses the
   `renovate/all-minor-patch` aggregation branch for NetBox version bump PRs.

2. Read `download_netbox.sh` to extract the new `NETBOX_VERSION` value.

3. Read `patches/requirements.patch` to identify the lines that the patch
   **adds** (lines starting with `+` that are not the `+++` header line).
   These are the extra packages that must be preserved in every version of the patch.

4. Download the NetBox source archive for the `NETBOX_VERSION` value from step 2:
   ```
   https://github.com/netbox-community/netbox/archive/refs/tags/v${NETBOX_VERSION}.tar.gz
   ```
   Extract it into a temporary directory and locate `requirements.txt` inside the
   archive root.

5. Check whether the current `patches/requirements.patch` applies cleanly to the
   downloaded file after placing it at `./netbox/requirements.txt` inside a
   temporary work directory. From that temporary work directory root, run:
   ```
   patch --dry-run -p1 -F0 < patches/requirements.patch
   ```
   Here `-F0` disables fuzz, so the patch must match exactly rather than
   applying with loose context matching.
   The patch file path is relative to the repository root. If the exit code is
   **0** (no errors, no rejects, no fuzz), call `noop` with the message
   "requirements.patch already applies cleanly to NetBox ${NETBOX_VERSION}" and
   stop. Treat any non-zero exit code as meaning the patch needs regeneration.

6. If the patch does **not** apply cleanly, regenerate it:
   a. Place the downloaded `requirements.txt` at `./netbox/requirements.txt`
      inside a temporary work directory, and keep a copy at
      `./netbox/requirements.txt.orig`.
   b. Append all preserved added lines (from step 3) to
      `./netbox/requirements.txt`.
   c. Run `diff -u ./netbox/requirements.txt.orig ./netbox/requirements.txt`
      from the temporary work directory root to produce the patch body.
   d. Normalize only the **file paths** in the diff headers before saving so the
      final patch matches the repository convention: both header paths should be
      `./netbox/requirements.txt`, while standard diff metadata such as
      timestamps may remain distinct. For example, the saved header may look
      like:
      ```
      --- ./netbox/requirements.txt	2026-07-20 00:00:00.000000000 +0000
      +++ ./netbox/requirements.txt	2026-07-20 00:00:01.000000000 +0000
      ```
      After writing
      `patches/requirements.patch`, verify it with
      `patch --dry-run -p1 -F0 < patches/requirements.patch`.

7. Push the updated `patches/requirements.patch` to the pull request branch
   using `push-to-pull-request-branch`.

8. Add a comment on the pull request using `add-comment` explaining that
   `patches/requirements.patch` was regenerated for NetBox `${NETBOX_VERSION}` and
   listing which packages were preserved from the previous patch.

## Notes

- Use `noop` whenever no file changes are needed (patch already applies).
- Do not modify any other files.
