# AAPI — O que falta

Só o que ainda está aberto. O histórico (auditoria do port, roteiro da VM, port do AFPI 2.9.0 e
como cada item foi validado) fica no git: o `TODO.md` completo está no commit `e4de25f`
(`git show e4de25f:TODO.md`).

Legenda: 🔴 quebra o playbook · 🟠 funciona errado / silenciosamente · 🟡 cosmético / legado AFPI

---

## Codecs (role `hardware`)

- [ ] 🟡 Codecs freeworld do VLC e HEIF/HEVC (`vlc-plugins-freeworld`, `libheif-freeworld`): ficam
      de fora. Reavaliar quando o EPEL estável alcançar as versões exigidas pelo RPM Fusion.
      - Conferido em 2026-10-01 (container), sem mudança:
        - VLC: `vlc-plugins-freeworld` 3.0.24 exige `vlc-libs` >= 3.0.24; EPEL tem 3.0.23 e o
          3.0.24 está no `epel-testing`. Resolve sozinho quando ele for para o estável.
        - HEIF: `libheif-freeworld` 1.20.2 exige `libheif` **=** 1.20.2; EPEL tem 1.17.6 e o
          `epel-testing` tem 1.23.5. Precisa de rebuild do RPM Fusion na versão que o EPEL tiver.
      - Conferido em 2026-10-04 (container): o RPM Fusion refez o `libheif-freeworld` na 1.23.5
        (exige `libheif` = 1.23.5), a mesma versão do `epel-testing`. Agora **os dois** só esperam o
        EPEL estável: lá ainda estão `vlc-libs` 3.0.23 e `libheif` 1.17.6; o `epel-testing` tem
        3.0.24 e 1.23.5. Com `--enablerepo=epel-testing` a transação resolve (atualiza `vlc-libs` e
        `libheif`, instala os dois freeworld). Não habilitar o `epel-testing` no playbook: esperar
        o push para o estável e então pôr os dois em `multimedia_packages`.
      - Para reconferir (com CRB, EPEL e RPM Fusion habilitados):
        `dnf repoquery --qf "%{name}-%{version}" vlc-libs libheif` vs
        `dnf repoquery --requires vlc-plugins-freeworld libheif-freeworld | grep -E "^(vlc-libs|libheif)"`.
