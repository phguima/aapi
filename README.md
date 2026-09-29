# AFPI (Advanced Fedora Post-Install) - Ansible Role-Based

[![Project Status: Active](https://img.shields.io/badge/Project%20Status-Active-brightgreen.svg)](#-project-status)

AFPI is a modular and intelligent system for Fedora Workstation post-installation (Validated on Fedora 41-44). It uses an architecture based on **Roles** and environment-aware variables (Jinja2), allowing your desktop customization and hardware optimizations to be applied consistently, making your workstation deployment fully automated and "hardware-aware".

> [!WARNING]
> **Disclaimer:** This project is tailored specifically for my personal environment, preferences, and hardware configuration. If you choose to use it, you must thoroughly review all roles, configurations, and variables, and customize them to fit your own specific requirements and hardware setup. Use it at your own risk.

## 📊 Project Status

*   **Current Version:** 2.6.0
*   **Last Update:** September 23, 2026
*   **Latest Improvement:** Claude Code installed via the official native installer in the `ai_tools` role (new `claude` tag).
*   **Stability:** Production-ready for Fedora 41, 42, 43, and 44.

## 🏗️ Architecture and Roles

The project is organized to isolate responsibilities, ensuring idempotency and ease of maintenance:

*   **`update`**: DNF plugins and optimization, RPM Fusion repositories, and a full system upgrade.
*   **`nvidia`**: GPU detection and Secure Boot-ready driver installation (MOK key, signed akmods build, initramfs).
*   **`hardware`**: Post-driver GPU setup (NVIDIA Vulkan, VA-API/NVENC and power management; Intel and AMD acceleration), multimedia codecs, and ASUS ROG support.
*   **`common`**: Hostname, Flathub, kernel cleanup, GRUB tuning (timeout, resolution, regenerated automatically when changed), the Antigravity CLI, and **Zero-Config ZSH** setup (Oh-My-Zsh with Kali-like theme and self-managed plugins).
*   **`desktop`**: 
    *   **Universal Cedilla (ç) Fix**: Uses a `~/.XCompose` mapping (System) plus Flatpak overrides. Browsers, Bitwarden and Antigravity run on native Wayland with no extra fix; Zoom is the exception and always runs on XWayland (it hardcodes xcb), where the cedilla also works.
    *   **Terminal**: Konsole and PTYxis profile management.

*   **`apps`**: Complete suite via DNF and Flatpak, featuring GPU automation for Steam, **VirtualBox group management (vboxusers/vboxsf)**, and productivity tools (Brave, VS Code, GitHub CLI).
*   **`ai_tools`**: Integration of the AI ecosystem (Claude Code via the official native installer, Gemini CLI and extensions) and specialized Python libraries via `pipx`.

## 🏷️ Granular Control (Tags)

AFPI features a comprehensive tagging system that allows you to run specific parts of the configuration:

| Category | Primary Tags | Description |
| :--- | :--- | :--- |
| **Maintenance** | `update`, `cleanup`, `grub` | System upgrades, DNF optimization, kernel cleanup, and GRUB tuning. |
| **Hardware** | `nvidia`, `drivers`, `power`, `asus` | GPU drivers, power management, and ASUS-specific tools. |
| **Shell** | `shell`, `zsh`, `omz`, `aliases` | ZSH installation, Oh-My-Zsh theme, and custom aliases. |
| **Desktop** | `desktop`, `fonts`, `cedilla` | Terminal profiles, fonts, and the universal cedilla fix. |
| **Software** | `apps`, `software`, `dnf`, `flatpak` | Application installation via DNF or Flatpak. |
| **AI** | `ai`, `claude`, `gemini`, `extensions`, `python` | Claude Code, Gemini CLI, extensions, and AI-related Python libraries. |

## 🔐 Secrets Management (Ansible Vault)

AFPI uses **Ansible Vault** to protect sensitive information. Since the provided `group_vars/all/secrets.yml` is encrypted, you must create your own if you fork this project.

### Required Variables in `secrets.yml`
| Variable | Description | Example / Usage |
| :--- | :--- | :--- |
| `api_keys` | Block of environment exports for your shell | `export SERVICE_API_KEY="your_value_here"` |
| `mok_password` | Password for NVIDIA MOK enrollment | Used to sign drivers for Secure Boot |

## 🚀 Getting Started

### 1. Bootstrap the System
Prepare the Ansible environment:
```bash
./bootstrap.sh
```

### 2. Run the Playbook
Apply the full configuration (the provided `ansible.cfg` is optimized for faster deployment):
```bash
ansible-playbook -i inventory.ini site.yml -K --ask-vault-pass
```

> [!IMPORTANT]
> **NVIDIA Users:** To ensure compatibility of proprietary drivers with the latest kernel and Secure Boot signing, follow this specific 3-step workflow using tags:
> 1. **Update System:** `ansible-playbook -i inventory.ini site.yml --tags update -K --ask-vault-pass`
> 2. **Reboot** to load the new kernel.
> 3. **Install NVIDIA Drivers:** `ansible-playbook -i inventory.ini site.yml --tags nvidia -K --ask-vault-pass`
> 4. **Reboot** to enroll the MOK key (if Secure Boot is enabled).
> 5. **Finish Setup:** `ansible-playbook -i inventory.ini site.yml --skip-tags update,nvidia -K --ask-vault-pass`

## ⚠️ Troubleshooting: System Freezes

Some laptops (especially those with hybrid graphics or specific ASUS/NVIDIA combinations) may experience a system freeze during the `hardware` role.

1.  **Hard Reboot** the machine (hold power button).
2.  Run the playbook skipping the power management and hardware-specific tags to isolate the issue:
    ```bash
    ansible-playbook site.yml --skip-tags power,asus --ask-vault-pass
    ```
3.  If the playbook finishes successfully with these skips, the conflict is likely in the NVIDIA Deep Power Management settings or the `supergfxd` service.

## 🛠️ AFPI Differentiators

### Intelligent Environment Discovery
AFPI doesn't just run blindly. The `env_setup.yml` core task dynamically discovers your machine's profile:
*   **Hardware Detection:** Identifies NVIDIA, Intel, or AMD GPUs and applies specific acceleration packages.
*   **Vendor Awareness:** Specifically detects ASUS ROG/TUF systems to enable `asusctl` and `supergfxctl` tools.
*   **Desktop Agnostic:** Automatically identifies if you are running GNOME or KDE Plasma and applies environment-specific terminal profiles (PTYxis or Konsole) and apps.

### Zero-Config Shell
ZSH configuration has been simplified. The `kali-like-alt` theme manages its own dependencies (syntax highlighting and autosuggestions), reducing playbook complexity and execution time.

### Robust NVIDIA & Secure Boot Automation
The `nvidia` role implements an advanced MOK (Machine Owner Key) management system entirely via Ansible:
*   **Intelligent Detection:** Detects existing keys, pending enrollments, and kernel status to avoid redundant operations.
*   **Integrated Signing:** Automatically triggers `akmods` and `dracut` to ensure modules are signed and included in the initramfs immediately.
*   **Secure Pipe:** Uses high-reliability password injection for `mokutil` via Vault secrets.

### Universal Cedilla (ç) Fix
Uses a `~/.XCompose` mapping (System) plus Flatpak overrides. Browsers, Bitwarden and Antigravity run on native Wayland with no extra fix; Zoom is the exception and always runs on XWayland (it hardcodes xcb), where the cedilla also works.
