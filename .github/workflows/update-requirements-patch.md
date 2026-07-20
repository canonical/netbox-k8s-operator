---
on:
  pull_request:
    types: [opened, synchronize]
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

1. Read `download_netbox.sh` to extract the new `NETBOX_VERSION` value.

2. Read `patches/requirements.patch` to identify the lines that the patch
   **adds** (lines starting with `+` that are not the `+++` header line).
   These are the extra packages that must be preserved in every version of the patch.

3. Download the NetBox source archive for the new version:
   ```
   https://github.com/netbox-community/netbox/archive/refs/tags/v<VERSION>.tar.gz
   ```
   Extract it into a temporary directory and locate `requirements.txt` inside the
   archive root.

4. Check whether the current `patches/requirements.patch` applies cleanly to the
   downloaded `requirements.txt` using `patch --dry-run -p1`. If it applies
   without errors, call `noop` with the message "requirements.patch already
   applies cleanly to NetBox <VERSION>" and stop.

5. If the patch does **not** apply cleanly, regenerate it:
   a. Copy the downloaded `requirements.txt` to a file called
      `requirements.txt.orig`.
   b. Append all preserved added lines (from step 2) to `requirements.txt`.
   c. Run `diff -u requirements.txt.orig requirements.txt` to produce the new
      patch content. The `---` line should reference the original path
      `./netbox/requirements.txt` and the `+++` line should also reference
      `./netbox/requirements.txt` so the patch is compatible with the `-p1`
      flag used by `download_netbox.sh`.
   d. Write the output to `patches/requirements.patch` in the repository.

6. Push the updated `patches/requirements.patch` to the pull request branch
   using `push-to-pull-request-branch`.

7. Add a comment on the pull request using `add-comment` explaining that
   `patches/requirements.patch` was regenerated for NetBox `<VERSION>` and
   listing which packages were preserved from the previous patch.

## Notes

- Use `noop` whenever no file changes are needed (patch already applies).
- Do not modify any other files.
