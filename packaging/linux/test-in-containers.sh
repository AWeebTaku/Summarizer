#!/usr/bin/env bash
# Install each package in a clean distribution and run the app's self-test there.
# Every distribution is tried (not just until the first failure), and any shared libraries the app
# cannot find are listed, so one run shows everything that is missing. Needs Docker.
# Usage: packaging/linux/test-in-containers.sh   (after packaging/linux/build.sh)
set -uo pipefail
cd "$(dirname "$0")/../.."
REL="$PWD/release"
FAILED=()

# runs inside the container, after the package is installed
CHECK='export LD_LIBRARY_PATH=/opt/summarizer/_internal:/opt/summarizer/_internal/PyQt6/Qt6/lib
missing=$(find /opt/summarizer -type f \( -name "*.so" -o -name "*.so.*" -o -name QtWebEngineProcess \) -exec ldd {} + 2>/dev/null | grep "not found" | sort -u)
if [ -n "$missing" ]; then echo "MISSING LIBRARIES:"; echo "$missing"; fi
summarizer-app --selftest'

try() {  # name, image, install command, [extra command to run afterwards]
  echo "::group::$1"
  if docker run --rm -v "$REL:/r:ro" "$2" sh -c "$3 && $CHECK${4:+ && $4}"; then echo "PASS: $1"; else echo "FAIL: $1"; FAILED+=("$1"); fi
  echo "::endgroup::"
}

try "Ubuntu 22.04 (.deb)"  ubuntu:22.04     'apt-get update -qq && apt-get install -y -qq /r/Summarizer-amd64.deb >/dev/null'
try "Ubuntu 24.04 (.deb)"  ubuntu:24.04     'apt-get update -qq && apt-get install -y -qq /r/Summarizer-amd64.deb >/dev/null'
try "Debian 12 (.deb)"     debian:12        'apt-get update -qq && apt-get install -y -qq /r/Summarizer-amd64.deb >/dev/null'
try "Fedora (.rpm)"        fedora:latest    'dnf install -y -q /r/Summarizer-x86_64.rpm >/dev/null'
# Arch always has the newest Mesa, so it also runs the app under a virtual X server. With a display set, Qt
# initialises GLX through the system's graphics driver, which is how a libstdc++ mismatch between the bundle and a
# newer distribution showed up ("Could not initialize GLX").
try "Arch (.pkg.tar.zst)"  archlinux:latest 'pacman -Sy --noconfirm >/dev/null 2>&1 && pacman -U --noconfirm /r/Summarizer-x86_64.pkg.tar.zst 2>&1 | tail -3' \
  'pacman -Syu --noconfirm xorg-server-xvfb xorg-xauth 2>&1 | tail -5 && xvfb-run -a summarizer-app --selftest'

echo
if [ ${#FAILED[@]} -gt 0 ]; then echo "FAILED: ${FAILED[*]}"; exit 1; fi
echo "All distributions passed."
