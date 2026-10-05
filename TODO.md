# AAPI — What is left

Only what is still open. The history (port audit, VM checklist, port of AFPI 2.9.0 and how each
item was validated) lives in git: the full `TODO.md` is in commit `e4de25f`
(`git show e4de25f:TODO.md`, in Portuguese).

Legend: 🔴 breaks the playbook · 🟠 works wrong / silently · 🟡 cosmetic / AFPI legacy

---

## Codecs (`hardware` role)

- [ ] 🟡 VLC and HEIF/HEVC freeworld codecs (`vlc-plugins-freeworld`, `libheif-freeworld`): left
      out. Re-evaluate when stable EPEL catches up with the versions RPM Fusion requires.
      - Checked on 2026-10-01 (container), no change:
        - VLC: `vlc-plugins-freeworld` 3.0.24 requires `vlc-libs` >= 3.0.24; EPEL has 3.0.23 and
          3.0.24 is in `epel-testing`. Solves itself when it reaches stable.
        - HEIF: `libheif-freeworld` 1.20.2 requires `libheif` **=** 1.20.2; EPEL has 1.17.6 and
          `epel-testing` has 1.23.5. Needs an RPM Fusion rebuild at whatever version EPEL has.
      - Checked on 2026-10-04 (container): RPM Fusion rebuilt `libheif-freeworld` at 1.23.5
        (requires `libheif` = 1.23.5), the same version as `epel-testing`. Now **both** only wait
        for stable EPEL: it still has `vlc-libs` 3.0.23 and `libheif` 1.17.6; `epel-testing` has
        3.0.24 and 1.23.5. With `--enablerepo=epel-testing` the transaction resolves (it updates
        `vlc-libs` and `libheif` and installs both freeworld packages). Do not enable
        `epel-testing` in the playbook: wait for the push to stable, then add both to
        `multimedia_packages`.
      - To re-check (with CRB, EPEL and RPM Fusion enabled):
        `dnf repoquery --qf "%{name}-%{version}" vlc-libs libheif` vs
        `dnf repoquery --requires vlc-plugins-freeworld libheif-freeworld | grep -E "^(vlc-libs|libheif)"`.
