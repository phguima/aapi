# AAPI — instructions for Claude

AAPI (Ansible AlmaLinux Post-Install): port of AFPI (`phguima/afpi`, Fedora) to **AlmaLinux 10**.
Public repo `phguima/aapi`, single branch `main`, GPL-3.0. Talk to the user in English; all docs
are in English.

The target is a **work machine**. Therefore, by decision of 2026-09-29:
- the hostname is **never** changed;
- there is no support for NVIDIA, Steam and ASUS ROG (removed);
- VirtualBox comes from Oracle's repository and works with Secure Boot;
- `mok_password` lives in `group_vars/all/all.yml`, and there is no vault since 2026-10-04:
  `api_keys` is `""` in `all.yml`. An optional vault at `group_vars/all/secrets.yml` (in
  `.gitignore`) may define it; if it exists, Claude does not have the password: do not try to open
  it.

Architecture improvements made here (reboot gate, idempotent MOK, `is_secure_boot`, Ptyxis with a
real `changed`…) were taken to AFPI. When porting something between the two, adapt what belongs to
each distro: EL10 uses **dnf4** (4.20), CRB + EPEL + RPM Fusion EL and `ansible-core` 2.16.

**ALPI** (`phguima/alpi`, at `../alpi`) is the planned successor that unifies AFPI and AAPI (design
stage since 2026-10-05). Changes made here until parity must also be ported there: note them in
ALPI's `TODO.md`.

## Work status

`TODO.md` holds **only what is left**. The history (port audit, VM checklist, AFPI port and how
each item was validated) was removed from it on 2026-10-04 and lives in git:
`git show e4de25f:TODO.md` (in Portuguese). The user often asks "show the todo" and expects a
**compact per-section** status. When an item is done, remove it from `TODO.md` and record the
validation in the commit message; a new task goes into `TODO.md` until it is done.

Status on 2026-10-01: everything done, including the VM test checklist (section 11, EFI + Secure
Boot). Only the optional 🟡 item for the VLC/HEIF freeworld codecs is left, blocked until EPEL
catches up with RPM Fusion's versions. The test VM was **KDE**: what is GNOME-only (Ptyxis) was
validated only in containers.

Between 2026-10-03 and 2026-10-04 the AFPI improvements up to version 2.9.0 were ported (section
12 of the historical `TODO.md`; the `PORTAR_DO_AFPI.md` list was deleted and is also in git),
checked in the VM and published as **v1.1.0** (tag and release). Anything new to port from AFPI
goes into `TODO.md`.

## Git

- Start with `git fetch` + `git pull --ff-only`. Check again before every push.
- Commit and push **only when the user asks**. Commits in English, Conventional Commits with scope
  (`feat(update): …`, `fix(desktop): …`, `docs(todo): …`).
- If `git push` is blocked by the auto-mode classifier (it happened before 2026-09-30), ask the
  user to run `! git -C <repo path> push`.

## Tests — in a container, never on the host

Validate in a podman container `docker.io/library/almalinux:10`, **twice** (idempotency:
`changed=0` on the 2nd) and also with `--check`, before committing. Never run the playbook on the
host.

- The bare container lacks what a Workstation install already has (e.g. `vlc-libs`, `libheif`).
  Preinstall the packages relevant to the change, or bugs slip through (the `@multimedia` depsolve
  failure of 2026-09-30 slipped through that way).
- GNOME-only tasks: simulate the session with a regular user with a D-Bus session bus,
  `XDG_CURRENT_DESKTOP=GNOME` and the playbook run via `sudo` (`env_setup` uses `SUDO_USER`).
- The detailed recipes (fake Secure Boot via `/sys/firmware`, fake `mokutil`, `dnf needs-restarting`
  wrapper, `:z` vs `:Z`, `-e` in JSON for booleans, `-e api_keys` to test the API block) are in
  AFPI's `CLAUDE.md` and apply here too, swapping the image and dnf5 for dnf4.
- What depends on hardware (real `vboxdrv` build, MokManager enrollment, reboot) goes to the VM.

## Test VM

The user runs the checks in the VM (reference checklist: section 11 of the historical `TODO.md`)
and sends the results as screenshots in `~/Pictures/Screenshots`. File names change: list the
directory and take the newest ones.

## AlmaLinux 10 specifics

- `bootstrap.sh` installs `ansible-core` (the `ansible` package does not exist on EL10) and pins
  `community.general` to 11.x, the last series compatible with `ansible-core` 2.16.
- CRB + EPEL must come before any other package (`update` role).
- `community.general.dnf_config_manager` works here (dnf4), unlike on Fedora.
- No `@multimedia`: RPM Fusion's freeworld versions often require newer `vlc-libs`/`libheif` than
  EPEL's and break the whole transaction.
- Roboto is not packaged for EL10: it comes from the latest upstream release (`desktop` role).
