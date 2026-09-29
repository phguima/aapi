# AAPI — Auditoria do port Fedora → AlmaLinux 10

Auditoria feita em 2026-09-29. A disponibilidade de pacotes foi validada num container
`almalinux:10` com CRB + EPEL 10 + RPM Fusion EL10 habilitados (dnf **4.20**, não dnf5).

Legenda: 🔴 quebra o playbook · 🟠 funciona errado / silenciosamente · 🟡 cosmético / legado AFPI

---

## 1. Repositórios e bootstrap

- [x] 🔴 **`bootstrap.sh`: `dnf install ansible` falha** — o pacote `ansible` não existe no EL10 base.
      Usar `ansible-core` (2.16, AppStream) + `ansible-galaxy collection install community.general`
      (já feito). Adicionar também `pciutils` (o `lspci` do `env_setup.yml` depende dele).
- [x] 🔴 **Habilitar CRB + EPEL antes de tudo** (role `update`): `dnf config-manager --set-enabled crb`
      e `dnf install epel-release` (vem do repo `extras` do Alma). Metade dos pacotes do `apps`
      vem do EPEL, e o RPM Fusion EL depende dele.
- [x] 🔴 **URLs do RPM Fusion** (`update`; a do `nvidia` sai junto com o role na seção 3): trocar `.../free/fedora/...` e
      `.../nonfree/fedora/...` por `.../free/el/...` e `.../nonfree/el/...`
      (`rpmfusion-{free,nonfree}-release-10.noarch.rpm`). Validado: ambos existem.
- [x] 🟠 Considerar assertar `ansible_facts['distribution'] == 'AlmaLinux'` e major `10` no
      `env_setup.yml`, para falhar cedo se rodar no Fedora por engano.

## 2. dnf4 vs dnf5

EL10 usa **dnf 4**. O que foi escrito com sintaxe dnf5 falha — e várias tasks têm
`failed_when: false`, então falham **em silêncio**.

- [x] 🟠 `kernel_maintenance.yml:25` — `dnf config-manager setopt "*debug*".enabled=0` é dnf5.
      No dnf4: `dnf config-manager --set-disabled '*debug*'` (ou simplesmente remover: no Alma
      os repos debug já vêm desabilitados).
- [x] `hardware/main.yml:6` (comentado) — `dnf mark user` (dnf5) saiu junto com o bloco NVIDIA.
- [ ] 🟡 `kernel_maintenance.yml:40` — `repoquery --installonly --latest-limit=-1` funciona no dnf4,
      mas a saída inclui epoch (`kernel-0:6.12.0-…`). O `grep -v $(uname -r)` continua funcionando;
      só validar num host real antes de confiar na remoção.

## 3. Remover NVIDIA e Steam — feito

Decisão de 2026-09-29: o alvo não tem GPU NVIDIA e Steam não será usado.

- [x] Role `nvidia` apagado e retirado do `site.yml`.
- [x] Bloco NVIDIA do role `hardware` (incl. o `dnf mark user` comentado e o `/etc/modprobe.d/nvidia.conf`).
- [x] Variáveis `nvidia_*`, pacote `steam` e alias `nvidia-run` do `all.yml`.
- [x] Seção "Shortcuts & Overrides" do role `apps` (4 tasks, todas só para o `steam.desktop`).
- [x] `env_setup.yml`: facts `is_nvidia` / `has_nvidia_driver` e o check de `nvidia-smi`
      (detecção Intel/AMD mantida).
- [x] `.zshrc`: bloco renomeado para `API CONFIGURATION` sem os `__NV_PRIME_*`, e uma task
      remove o bloco antigo `NVIDIA AND API CONFIGURATION` para não ficar órfão.
      Validado em container: migra na 1ª execução, `changed=0` na 2ª.
- [x] Aviso de reboot do `bootstrap.sh` generalizado.
- [ ] 🟡 `README.md` — seção "NVIDIA Users", tags `nvidia`/`drivers`/`power`, troubleshooting de
      freeze NVIDIA/ASUS → fica para a reescrita do README (seção 9).
- [x] `mok_password` saiu do vault: agora é `alma-aapi` no `all.yml` (o vault segue só com `api_keys`).

## 4. Multimídia / aceleração de vídeo — feito

- [x] `gstreamer1-plugins-bad-free-extras` removido de `multimedia_packages`.
- [x] AMD: `amd_multimedia_packages`, a task do role `hardware` e o fact `is_amd` removidos
      (o mesa do EL10 não traz VA-API e não há build freeworld no EPEL/RPM Fusion EL).
      Ficou um comentário no role explicando.
- [x] Comentário `libvdpau-va-gl // Retired into Fedora 44` removido da lista Intel.
- [x] Validado em container (`--tags repos,hardware`, Intel simulado): 1ª execução instalou
      `ffmpeg` 7.1 (trocou o `ffmpeg-free`), `libva-intel-driver`, `intel-media-driver`,
      `gstreamer1-plugins-bad-freeworld`, `-ugly` e `-libav`; 2ª execução `changed=0`.
- [x] `gstreamer1-libav` → `gstreamer1-plugin-libav` (nome real no EL10).

## 5. Pacotes do role `apps`

Faltando no EL10 (nem EPEL nem RPM Fusion):

- [x] 🔴 `argyllcms` — ausente (afeta DisplayCAL, que é Flatpak e já traz o próprio Argyll; pode só remover).
- [x] 🔴 `chkrootkit` — ausente. Remover (o `rkhunter` e o `lynis` existem).
- [x] 🔴 `unhide` — ausente. Remover.
- [x] 🔴 `google-roboto-fonts` — ausente no EL10 (o `google-roboto-slab-fonts` é outra família).
      Agora o role `desktop` instala o **último release** de `googlefonts/roboto-3-classic`
      (TTFs estáticos hinted em `/usr/local/share/fonts/roboto`), conferindo o SHA-256 que a API do
      GitHub publica, e substitui a instalação inteira quando sai versão nova (`.version`). Sem
      acesso ao GitHub, só avisa e mantém o que houver. Validado em container: instalação limpa,
      re-run sem mudança, upgrade de versão antiga (arquivos velhos removidos), GitHub fora,
      `--check`, e leitura por usuário não-root.
- [x] 🔴 **`VirtualBox`** — via repo oficial da Oracle (`VirtualBox-7.2`), adaptado ao Secure Boot:
      - `env_setup.yml`: fact `is_secure_boot` lido direto da variável EFI `SecureBoot` (não depende
        do `mokutil`; boot BIOS → false). Conferido num EFI real: `0` ↔ `mokutil` "disabled".
      - Repo `virtualbox` (`yum_repository`, `gpgcheck` + `repo_gpgcheck`; a chave é importada pelo
        dnf — `rpm_key` exigiria `gpg2`, que pode faltar).
      - Com Secure Boot: exige `mok_password` (`all.yml`), instala `mokutil`/`openssl`, gera
        `/var/lib/shim-signed/mok/MOK.{der,priv}` (0700/0600, EKU codeSigning) e pede o registro
        com `mokutil --import` só se `--test-key` não disser "already" (senha via stdin, `no_log`).
        Tudo **antes** do pacote: o postinst da Oracle compila e assina, e o `vboxdrv.sh` refaz isso
        no boot quando entra kernel novo. Aviso final pede reboot + "Enroll MOK".
      - Dependências do build: `kernel-devel`, `gcc`, `make`, `elfutils-libelf-devel`.
      - Validado em container: sem Secure Boot (instala, 2ª execução `changed=0`) e com Secure Boot
        simulado por `mokutil` falso (chave criada com as permissões certas, 1 único `--import` com a
        senha, 2ª execução `changed=0`).
      - [ ] 🟡 Pendente de VM: build real do `vboxdrv` (o container roda o kernel do host) e o
        registro na tela do MokManager — testar numa VM com EFI + Secure Boot.
- [x] 🟠 `p7zip` / `p7zip-plugins` → `7zip-standalone` (`7za`) / `7zip` (`7z`).
      Validado: toda a `dnf_packages_common` (menos VirtualBox) instala num container EL10.
- [x] 🟡 `clamav-update` → `clamav-freshclam`, `vim` → `vim-enhanced`, `shellcheck` → `ShellCheck`
      (nomes reais no EL10; o `clamav-freshclam.service` usado no role `apps` vem desse pacote).
- [ ] ✅ OK: `chromium`, `clamav`, `fastfetch`, `htop`, `hwinfo`, `lm_sensors`, `lynis`, `nodejs` (22),
      `nvtop`, `pipx`, `python3-pip`, `rkhunter`, `testdisk`, `tmux`, `tuptime`, `unrar`, `unzip`,
      `uv`, `fira-code-fonts`.
- [ ] ✅ GNOME: `flatseal`, `gnome-tweaks` (EPEL). KDE: `ktorrent`, `plasma-sdk`, `kde-gtk-config`,
      `konsole` (EPEL, Plasma 6.6). `ptyxis` é o terminal padrão do EL10 (AppStream).
- [ ] ✅ Brave, VS Code, GitHub CLI: repos próprios, sem dependência de versão do Fedora. OK.

## 6. Hardware ASUS — removido

- [x] Bloco ASUS removido (decisão de 2026-09-29): tasks do role `hardware`, variáveis `asus_*`
      do `all.yml` e o fact `is_asus` do `env_setup.yml`. Não havia pacote para EL10 de qualquer
      forma (COPR `lukenukem/asus-linux` só tem chroots Fedora/openSUSE).
- [ ] 🟡 `README.md` ainda cita ASUS (linhas 23, 39, 79-86, 93) — limpar junto com a seção 9.

## 7. GRUB

- [x] Handler `Regenerate GRUB` (`site.yml`) agora grava em `/boot/grub2/grub.cfg`.
      Correção da auditoria: no EL10 `/etc/grub2-efi.cfg` já é symlink para esse arquivo, então em
      UEFI o handler antigo funcionava; a troca deixa explícito e cobre boot BIOS (sem
      `grub2-efi-x64` o symlink não existe e o antigo criaria um arquivo solto em `/etc`).
- [ ] 🟡 O EL usa BLS + `grubby`; parâmetros de kernel devem ir via `grubby`, não `GRUB_CMDLINE_LINUX`
      (hoje o playbook não mexe no cmdline, então só fica o aviso).

## 8. Resto do código — sem mudança necessária

`common` (hostname, Flathub, ZSH/Oh-My-Zsh, aliases, Antigravity), `desktop` (Konsole, Ptyxis,
cedilha via `~/.XCompose`), `ai_tools` (Claude Code, pipx) — nada específico do Fedora.
Pontos só para ficar de olho:

- [x] `pipx ... playwright install chromium` — verificado em container EL10: o Chromium do Playwright
      abre headless após instalar libs comuns de desktop (`nss`, `atk`, `at-spi2-*`, `cairo`, `pango`,
      `alsa-lib`, `cups-libs`, `mesa-libgbm`, `libxkbcommon`, `libX*`), que o GNOME/KDE já trazem.
      `playwright install-deps` (só Debian/Ubuntu) não é usado. Nada a mudar.
- [x] EL10 sem servidor Xorg — verificado: `xorg-x11-server-Xwayland` (AppStream) vem com o GNOME;
      Zoom segue via Xwayland e o cedilha via `~/.XCompose`. Só some a sessão "GNOME on Xorg",
      que o playbook não usa. Nada a mudar.

## 9. Legado AFPI / Fedora (renomear)

- [x] `mok_password` saiu do vault para o `all.yml` (`alma-aapi`). O vault **continua** para `api_keys`.
- [ ] 🟡 `README.md` — tabela de variáveis do vault: tirar `mok_password` (agora no `all.yml`).

- [ ] 🟡 `README.md` inteiro ainda é do AFPI / Fedora 41-44.
- [x] `bootstrap.sh` — cabeçalho, mensagens e "root of the afpi project" → AAPI.
- [x] `site.yml` — task `AFPI | Final Status` → `AAPI | Final Status` (banner realinhado).
- [x] `group_vars/all/all.yml:19` — comentário "Retired into Fedora 44" (removido na seção 4).
- [x] `git init` + commit baseline (`497f521`).

---

## Ordem sugerida

1. ~~`git init` + commit do estado atual~~ ✅ feito.
2. Seção 1 (bootstrap + CRB/EPEL/RPM Fusion) — sem isso nada roda.
3. Seções 4 e 5 (listas de pacotes) — o grosso das falhas duras.
4. ~~Seção 3 (remoção de NVIDIA/Steam)~~ ✅ feito.
5. Seções 7 e 2 (6 já feita).
6. Seção 9 (renomear) + README.
7. Rodar `ansible-playbook --check` num host/VM AlmaLinux 10.
