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
- ⚠️ `mok_password` **fica** no vault: será usado pela assinatura do VirtualBox (seção 5).

## 4. Multimídia / aceleração de vídeo (`group_vars/all/all.yml`)

- [ ] 🔴 `gstreamer1-plugins-bad-free-extras` — **não existe**. Remover.
- [ ] 🔴 AMD: `mesa-va-drivers-freeworld`, `libva-utils`, `vdpauinfo` — **nenhum existe**, e o mesa
      do EL10 não traz nenhum driver VA-API (`mesa-va-drivers` também ausente). Não há aceleração
      VA-API para AMD via RPM no EL10. Remover a lista ou mover para "sem suporte".
- [ ] 🟠 `@multimedia` existe (grupo "Multimedia"), mas é bem menor que o do Fedora. OK manter.
- [ ] 🟠 Swap `ffmpeg-free` → `ffmpeg`: funciona (EPEL tem `ffmpeg-free`, RPM Fusion tem `ffmpeg` 7.1).
      Manter o `allowerasing`.
- [ ] ✅ `gstreamer1-plugins-bad-freeworld`, `gstreamer1-plugins-ugly`, `gstreamer1-libav`: OK.
- [ ] ✅ Intel: `libva-intel-driver` (RPM Fusion free), `intel-media-driver` (RPM Fusion nonfree): OK.

## 5. Pacotes do role `apps`

Faltando no EL10 (nem EPEL nem RPM Fusion):

- [ ] 🔴 `argyllcms` — ausente (afeta DisplayCAL, que é Flatpak e já traz o próprio Argyll; pode só remover).
- [ ] 🔴 `chkrootkit` — ausente. Remover (o `rkhunter` e o `lynis` existem).
- [ ] 🔴 `unhide` — ausente. Remover.
- [ ] 🔴 `google-roboto-fonts` — ausente (só `google-roboto-slab-fonts`). Trocar ou baixar via Google Fonts.
- [ ] 🔴 **`VirtualBox`** — ausente nos repos da distro. **Decisão (2026-09-29): manter VirtualBox via
      repo oficial da Oracle** (build el10 validado: `VirtualBox-7.2`).
      - Adicionar `yum_repository` (`https://download.virtualbox.org/virtualbox/rpm/el/$releasever/$basearch`)
        + chave `https://www.virtualbox.org/download/oracle_vbox_2016.asc`.
      - Tirar `VirtualBox` de `dnf_packages_common` e instalar `VirtualBox-7.2` numa task própria.
      - Pré-requisitos do build do `vboxdrv`: `kernel-devel`, `gcc`, `make`, `elfutils-libelf-devel`.
      - O pacote da Oracle já cria o grupo `vboxusers`; as tasks de grupo existentes continuam valendo.
      - Secure Boot: hoje **desligado no alvo** (`SecureBoot disabled`, 2026-09-29), mas o playbook
        deve detectar e se adaptar. Validado lendo o `vboxdrv.sh` do pacote `VirtualBox-7.2` el10:
        o script da Oracle **já assina sozinho** (em qualquer distro, não só Debian) se existir a
        chave em `/var/lib/shim-signed/mok/MOK.{der,priv}` e o `sign-file` do `kernel-devel`.
        E no boot, se não houver módulo para o kernel atual, ele recompila e reassina — então
        updates de kernel ficam cobertos sem hook extra. Plano:
        1. `env_setup.yml`: fact `is_secure_boot` a partir de `mokutil --sb-state`
           (`SecureBoot enabled` → true; qualquer outra saída → false).
        2. Se `is_secure_boot`, **antes** de instalar o VirtualBox: criar `/var/lib/shim-signed/mok`
           (0700), gerar a chave com `openssl req ... -addext extendedKeyUsage=codeSigning`
           (`creates:` MOK.priv) e, se `mokutil --test-key` disser que não está registrada nem
           pendente, `mokutil --import` com `mok_password` do vault.
        3. Instalar `VirtualBox-7.2` — o postinst compila e assina.
        4. Avisar: reboot + registrar a chave na tela azul do MokManager (passo manual inevitável).
        - Consequência: **manter `mok_password` no vault** (a seção 3 previa remover).
        - Teste do ramo com Secure Boot só em VM com firmware OVMF Secure Boot, não em container.
- [ ] 🟠 `p7zip` / `p7zip-plugins` — resolvem via *provides* para `7zip-standalone` / `7zip`.
      Funciona, mas trocar pelos nomes reais.
- [ ] 🟡 `clamav-update` resolve para `clamav-freshclam`; `vim` → `vim-enhanced`; `shellcheck` →
      `ShellCheck`. Funcionam via provides; opcional renomear.
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

- [ ] 🟠 Handler `Regenerate GRUB` (`site.yml`) escreve em `/etc/grub2-efi.cfg`. No EL9+/EL10 o
      `grub.cfg` real é `/boot/grub2/grub.cfg` (o da ESP é um stub que o carrega). Usar
      `grub2-mkconfig -o /boot/grub2/grub.cfg`. (Vale conferir no host: `readlink -f /etc/grub2-efi.cfg`.)
- [ ] 🟡 O EL usa BLS + `grubby`; parâmetros de kernel devem ir via `grubby`, não `GRUB_CMDLINE_LINUX`
      (hoje o playbook não mexe no cmdline, então só fica o aviso).

## 8. Resto do código — sem mudança necessária

`common` (hostname, Flathub, ZSH/Oh-My-Zsh, aliases, Antigravity), `desktop` (Konsole, Ptyxis,
cedilha via `~/.XCompose`), `ai_tools` (Claude Code, pipx) — nada específico do Fedora.
Pontos só para ficar de olho:

- [ ] 🟡 `pipx ... playwright install chromium`: o Playwright não suporta EL oficialmente; costuma
      funcionar, mas `playwright install-deps` não funciona.
- [ ] 🟡 EL10 não tem servidor Xorg (só Xwayland). Não afeta nada hoje (Zoom continua via Xwayland).

## 9. Legado AFPI / Fedora (renomear)

- [ ] 🟡 `README.md` inteiro ainda é do AFPI / Fedora 41-44.
- [ ] 🟡 `bootstrap.sh` — cabeçalho, mensagens e "root of the afpi project".
- [ ] 🟡 `site.yml:24` — task `AFPI | Final Status`.
- [ ] 🟡 `group_vars/all/all.yml:19` — comentário "Retired into Fedora 44".
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
