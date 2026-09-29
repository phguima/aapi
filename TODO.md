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
- [x] 🟠 `p7zip` / `p7zip-plugins` → `7zip-standalone` (`7za`) / `7zip` (`7z`).
      Validado: toda a `dnf_packages_common` (menos VirtualBox) instala num container EL10.
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
