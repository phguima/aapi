# AAPI (Ansible AlmaLinux Post-Install) - Ansible Role-Based

[![Project Status: Active](https://img.shields.io/badge/Project%20Status-Active-brightgreen.svg)](#-project-status)

AAPI is a modular system for AlmaLinux 10 workstation post-installation. It is a port of AFPI (Ansible Fedora Post-Install) and keeps its architecture based on **Roles** and environment-aware variables (Jinja2), so desktop customization and hardware setup are applied consistently and the workstation deployment is fully automated.

> [!WARNING]
> **Disclaimer:** This project is tailored specifically for my personal environment, preferences, and hardware configuration. If you choose to use it, you must thoroughly review all roles, configurations, and variables, and customize them to fit your own specific requirements and hardware setup. Use it at your own risk.

## 📊 Project Status

*   **Current Version:** 1.0.0 (port of AFPI 2.6.0)
*   **Last Update:** September 29, 2026
*   **Target:** AlmaLinux 10.x only (validated on 10.2). The playbook stops right away on any other distribution or major version.
*   **Validation:** The parts changed in the port (repositories, OS guard, dnf 4 fixes, codecs, package lists, Roboto, VirtualBox with Secure Boot simulated) were validated in `almalinux:10` containers: the first run applies, the second reports no changes. A full run on a real machine or VM (EFI + Secure Boot) is still pending: see `TODO.md`.

## 🏗️ Architecture and Roles

The project is organized to isolate responsibilities, ensuring idempotency and ease of maintenance:

*   **`update`**: DNF tuning, the **CRB** and **EPEL** repositories (enabled before anything else is installed), **RPM Fusion for EL**, a full system upgrade, and a **reboot gate** that stops the playbook when the upgrade requires a reboot.
*   **`hardware`**: Intel VA-API drivers, full `ffmpeg` (replacing `ffmpeg-free`) and multimedia codecs.
*   **`common`**: Flathub, kernel cleanup, GRUB tuning (regenerated automatically when changed), Git identity and defaults, the Antigravity CLI (user only), and **Zero-Config ZSH** setup (Oh-My-Zsh with Kali-like theme and self-managed plugins).
*   **`apps`**: DNF and Flatpak applications, ClamAV, Brave, VS Code, GitHub CLI and **VirtualBox from Oracle's repository**, with Secure Boot-aware module signing (see below). Adds a menu entry (icon included) for the Antigravity IDE when it is found in `antigravity_ide_dir`.
*   **`desktop`**:
    *   **Fonts**: Fira Code from EPEL and **Roboto from its latest upstream release** (not packaged for EL10). It is replaced automatically whenever a new release is published.
    *   **Universal Cedilla (ç) Fix**: Uses a `~/.XCompose` mapping plus Flatpak overrides. Browsers, Bitwarden and Antigravity run on native Wayland with no extra fix; Zoom always runs on Xwayland (it hardcodes xcb), where the cedilla also works.
    *   **Terminal**: Konsole (KDE) and Ptyxis (GNOME) profile management.
*   **`ai_tools`**: Claude Code via the official native installer and AI-related Python tools via `pipx` (markitdown, notebooklm-py with Playwright Chromium).

## 🏷️ Granular Control (Tags)

AAPI features a tagging system that allows you to run specific parts of the configuration:

| Category | Primary Tags | Description |
| :--- | :--- | :--- |
| **Maintenance** | `update`, `repos`, `kernel`, `cleanup`, `grub` | Repositories (CRB, EPEL, RPM Fusion), upgrades, kernel cleanup, and GRUB tuning. |
| **Hardware** | `hardware`, `intel`, `codecs`, `ffmpeg` | Intel video acceleration and multimedia codecs. |
| **Shell** | `shell`, `zsh`, `omz`, `aliases` | ZSH installation, Oh-My-Zsh theme, and custom aliases. |
| **Git** | `git` | Git identity (from `bootstrap.sh`) and defaults in the user's `~/.gitconfig`. |
| **Desktop** | `desktop`, `fonts`, `roboto`, `cedilla` | Terminal profiles, fonts, and the universal cedilla fix. |
| **Software** | `apps`, `software`, `dnf`, `flatpak`, `virtualbox`, `shortcuts` | Application installation via DNF, Flatpak, or vendor repositories, and menu entries (Antigravity IDE). |
| **AI** | `ai`, `claude`, `python` | Claude Code and AI-related Python tools. |

## 🔐 Secrets Management (Ansible Vault)

AAPI uses **Ansible Vault** for API keys. Since the provided `group_vars/all/secrets.yml` is encrypted, you must create your own if you fork this project.

### Required Variables in `secrets.yml`
| Variable | Description | Example / Usage |
| :--- | :--- | :--- |
| `api_keys` | Block of environment exports for your shell | `export SERVICE_API_KEY="your_value_here"` |

The MOK enrollment password (`mok_password`) is **not** a secret and lives in `group_vars/all/all.yml`: see the Secure Boot section below.

## 🚀 Getting Started

### 1. Bootstrap the System
Prepare the Ansible environment (installs `ansible-core`, `pciutils` and the `community.general` collection):
```bash
./bootstrap.sh
```
It also asks for your **Git `user.name` and `user.email`** (Enter keeps the saved value or the one already in `~/.gitconfig`; empty skips them) and saves them to `host_vars/127.0.0.1.yml`, which is git-ignored and overrides `group_vars/all/all.yml` (other variables you put there are kept). The playbook writes them to your `~/.gitconfig`, together with `init.defaultBranch=main` and `pull.ff=only` (`git_config_defaults` in `all.yml`, tag `git`), without stopping to ask. Run `./bootstrap.sh` again to change them.

### 2. Run the Playbook (update, reboot, run again)
```bash
ansible-playbook -i inventory.ini site.yml -K --ask-vault-pass
```

On a fresh install the first run only sets up the repositories and upgrades the system. If the upgrade brings a new kernel or core libraries (`dnf needs-restarting -r`, or a newer installed `kernel-core` than the running kernel, a check that does not depend on the clock), the playbook **stops there and asks for a reboot**. After rebooting, run the **same command again**: the update step passes and the rest of the setup runs on the new kernel. This matters because VirtualBox builds its kernel modules against the running kernel, and the old kernel can only be cleaned up once it is no longer in use.

With Secure Boot on, one more reboot is needed at the end to enroll the VirtualBox signing key (see below).

Or only a part of it, for example just the repositories:
```bash
ansible-playbook -i inventory.ini site.yml --tags repos -K --ask-vault-pass
```

With `--check`, the Roboto step only reports which version would be installed (the full playbook has not been validated in check mode yet).

### 3. GitHub CLI login
The playbook installs `gh` but cannot log in for you (it opens the browser and keeps the token in the keyring). At the end of each run it reminds you while you are not logged in. As your user:
```bash
gh auth login --hostname github.com --git-protocol https --web
gh auth setup-git
```

## 🛡️ VirtualBox and Secure Boot

VirtualBox is not packaged for EL10, so AAPI installs `VirtualBox-7.2` from Oracle's official repository. Its kernel modules are built locally, which matters when Secure Boot is on:

*   **Secure Boot off:** VirtualBox is just installed.
*   **Secure Boot on:** before installing the package, AAPI creates a signing key pair in `/var/lib/shim-signed/mok/` and queues it for enrollment with `mokutil --import`. Oracle's `vboxdrv.sh` then signs the modules with that key, both at install time and whenever it rebuilds them at boot for a new kernel.

After a run that queued the key, **reboot**, choose **Enroll MOK** in the blue MokManager screen, and type the `mok_password` from `group_vars/all/all.yml` (default: `alma-aapi`). This confirmation is manual by design.

> [!NOTE]
> MokManager uses a US keyboard layout. Keep `mok_password` to plain letters, digits and `-`, otherwise what you type on an ABNT2 (or other) keyboard will not match.

Check the Secure Boot state with `mokutil --sb-state`.

## 🛠️ AAPI Differentiators

### Intelligent Environment Discovery
AAPI doesn't just run blindly. The `env_setup.yml` core task dynamically discovers your machine's profile:
*   **Distribution Guard:** Fails fast unless the target is AlmaLinux 10.x.
*   **Hardware Detection:** Identifies Intel GPUs and applies the matching video acceleration packages.
*   **Secure Boot Detection:** Reads the `SecureBoot` EFI variable directly (works before `mokutil` is installed; legacy BIOS boots count as disabled).
*   **Desktop Agnostic:** Detects GNOME or KDE Plasma (via EPEL) and applies environment-specific terminal profiles (Ptyxis or Konsole) and apps.

### Zero-Config Shell
ZSH configuration has been simplified. The `kali-like-alt` theme manages its own dependencies (syntax highlighting and autosuggestions), reducing playbook complexity and execution time.

### Always-Current Roboto
Roboto is fetched from the latest `googlefonts/roboto-3-classic` release, verified against the SHA-256 digest published by GitHub, and replaces the previous installation only when the version changes. If GitHub is unreachable, the playbook warns and keeps what is already installed.

## 🔄 Differences from AFPI (Fedora)

| Area | AFPI (Fedora) | AAPI (AlmaLinux 10) |
| :--- | :--- | :--- |
| Package manager | dnf5 | dnf 4 (commands adapted) |
| Extra repositories | RPM Fusion | CRB + EPEL + RPM Fusion for EL |
| NVIDIA / Steam / ASUS ROG | Supported | Removed (out of scope; Steam needs i686, which EL10 does not ship; no `asusctl` builds for EL10) |
| AMD video acceleration | `mesa-va-drivers-freeworld` | Not available on EL10 |
| VirtualBox | RPM Fusion | Oracle repository, Secure Boot-aware signing |
| Roboto font | `google-roboto-fonts` RPM | Latest upstream release |
| `argyllcms`, `chkrootkit`, `unhide` | Installed | Dropped (not available on EL10) |
