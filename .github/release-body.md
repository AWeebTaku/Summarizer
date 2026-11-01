## Download

| System | File |
|---|---|
| Windows | `Summarizer-setup.exe` (current user, no admin needed) or `Summarizer.msi` (all users) |
| macOS (Apple Silicon) | `Summarizer-macOS-arm64.dmg` |
| Debian, Ubuntu, Mint | `Summarizer-amd64.deb` (`sudo apt install ./Summarizer-amd64.deb`) |
| Fedora, openSUSE | `Summarizer-x86_64.rpm` (`sudo dnf install ./Summarizer-x86_64.rpm`) |
| Arch, Manjaro | `Summarizer-x86_64.pkg.tar.zst` (`sudo pacman -U Summarizer-x86_64.pkg.tar.zst`) |
| Any Linux | `Summarizer-x86_64.AppImage` (`chmod +x`, then run it) |

The installers are not code-signed yet, so Windows SmartScreen and macOS Gatekeeper will warn the first time. The README explains how to open them (on macOS 15 and later, use System Settings, Privacy & Security, Open Anyway). `SHA256SUMS.txt` lists a checksum for each file. Linux builds need glibc 2.35 or newer (Ubuntu 22.04, Debian 12, Fedora 36 and later).

Prefer to run it from source? The README explains how.
