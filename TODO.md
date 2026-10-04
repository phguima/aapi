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

- [x] **Reboot gate** no fim do role `update` (2026-09-29): `dnf needs-restarting -r` → rc 1 para o
      playbook (`meta: end_host`) com aviso "reinicie e rode de novo"; rc 0 segue; outro rc falha.
      Reproduz o fluxo do AFPI (atualizar → reiniciar → resto) sem depender de lembrar dele.
      Validado em container forçando rc 1/0/3.

## 2. dnf4 vs dnf5

EL10 usa **dnf 4**. O que foi escrito com sintaxe dnf5 falha — e várias tasks têm
`failed_when: false`, então falham **em silêncio**.

- [x] 🟠 `kernel_maintenance.yml:25` — `dnf config-manager setopt "*debug*".enabled=0` é dnf5.
      No dnf4: `dnf config-manager --set-disabled '*debug*'` (ou simplesmente remover: no Alma
      os repos debug já vêm desabilitados).
- [x] `hardware/main.yml:6` (comentado) — `dnf mark user` (dnf5) saiu junto com o bloco NVIDIA.
- [x] 🟡 `kernel_maintenance.yml:40` — `repoquery --installonly --latest-limit=-1` funciona no dnf4,
      mas a saída inclui epoch (`kernel-0:6.12.0-…`). O `grep -v $(uname -r)` continua funcionando;
      só validar num host real antes de confiar na remoção.
      - Lógica já validada em container (2026-09-29): com `kernel-core` 211.55.1 e 211.56.1
        instalados, removeu o 211.55.1 e manteve o 211.56.1; 2ª execução `changed=0`. O container
        roda o kernel do host, então a proteção do kernel em uso só é testável na VM.
      - Roteiro na VM (o repo mantém versões anteriores do 10.x: `dnf --showduplicates list kernel`):
        1. Instalar um kernel anterior ao atual: `sudo dnf install kernel-<versão anterior>`.
        2. **Teste 1** — rodando o kernel novo: `--tags kernel` → sobra só o novo; re-run sem mudança.
        3. **Teste 2 (segurança)** — reinstalar o antigo, dar boot nele pelo GRUB (`uname -r`),
           rodar `--tags kernel` → os **dois** continuam instalados (o novo nunca entra na lista e
           o antigo é o que está rodando).
        4. **Teste 3** — com um só kernel: a task é pulada.
      - Validado na VM (2026-10-01): testes 1, 2 e 3 ok.

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
- [x] `README.md` — seção "NVIDIA Users", tags `nvidia`/`drivers`/`power`, troubleshooting de
      freeze NVIDIA/ASUS → resolvido na reescrita do README.
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
- [x] 🔴 `@multimedia` removido de `multimedia_packages` (2026-09-30, achado na VM). A versão do
      RPM Fusion do grupo tem pacotes condicionais: com `vlc-libs` / `libheif` instalados (caso do
      Workstation) puxa `vlc-plugins-freeworld` 3.0.24 (exige `vlc-libs` >= 3.0.24; EPEL tem 3.0.23)
      e `libheif-freeworld` 1.20.2 (exige `libheif` = 1.20.2; EPEL tem 1.17.6) → depsolve error na
      task `Codecs | Install Multimedia Group and Codecs`. A validação acima não pegou porque o
      container não tinha esses pacotes. O grupo não acrescentava nada: o Workstation já instala o
      grupo Multimedia do Alma, e os freeworld úteis já estão listados explicitamente.
      Validado em container com `libheif` + `vlc-libs` instalados: instala, 2ª execução `changed=0`.
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
      - [x] 🟡 Pendente de VM: build real do `vboxdrv` (o container roda o kernel do host) e o
        registro na tela do MokManager — testar numa VM com EFI + Secure Boot.
        Validado na VM (2026-10-01): etapas 3 e 6 da seção 11.
- [x] 🟠 `p7zip` / `p7zip-plugins` → `7zip-standalone` (`7za`) / `7zip` (`7z`).
      Validado: toda a `dnf_packages_common` (menos VirtualBox) instala num container EL10.
- [x] 🟡 `clamav-update` → `clamav-freshclam`, `vim` → `vim-enhanced`, `shellcheck` → `ShellCheck`
      (nomes reais no EL10; o `clamav-freshclam.service` usado no role `apps` vem desse pacote).
- [x] ✅ OK: `chromium`, `clamav`, `fastfetch`, `htop`, `hwinfo`, `lm_sensors`, `lynis`, `nodejs` (22),
      `nvtop`, `pipx`, `python3-pip`, `rkhunter`, `testdisk`, `tmux`, `tuptime`, `unrar`, `unzip`,
      `uv`, `fira-code-fonts`.
- [x] ✅ GNOME: `flatseal`, `gnome-tweaks` (EPEL). KDE: `ktorrent`, `plasma-sdk`, `kde-gtk-config`,
      `konsole` (EPEL, Plasma 6.6). `ptyxis` é o terminal padrão do EL10 (AppStream).
- [x] ✅ Brave, VS Code, GitHub CLI: repos próprios, sem dependência de versão do Fedora. OK.
      Os três itens confirmados (2026-10-01). A VM era **KDE**: o que é só do GNOME foi validado em
      container simulando uma sessão GNOME (usuário com D-Bus, `XDG_CURRENT_DESKTOP=GNOME`, playbook
      via `sudo`): `--tags gnome` instalou `flatseal`, `gnome-tweaks`, os 3 Flatpaks GNOME e aplicou
      o Ptyxis; 2ª execução `changed=0`, `--check` `failed=0`.

## 6. Hardware ASUS — removido

- [x] Bloco ASUS removido (decisão de 2026-09-29): tasks do role `hardware`, variáveis `asus_*`
      do `all.yml` e o fact `is_asus` do `env_setup.yml`. Não havia pacote para EL10 de qualquer
      forma (COPR `lukenukem/asus-linux` só tem chroots Fedora/openSUSE).
- [x] `README.md` ainda cita ASUS (linhas 23, 39, 79-86, 93) — resolvido na reescrita do README.

## 7. GRUB

- [x] Handler `Regenerate GRUB` (`site.yml`) agora grava em `/boot/grub2/grub.cfg`.
      Correção da auditoria: no EL10 `/etc/grub2-efi.cfg` já é symlink para esse arquivo, então em
      UEFI o handler antigo funcionava; a troca deixa explícito e cobre boot BIOS (sem
      `grub2-efi-x64` o symlink não existe e o antigo criaria um arquivo solto em `/etc`).
- [x] 🟡 O EL usa BLS + `grubby`; parâmetros de kernel devem ir via `grubby`, não `GRUB_CMDLINE_LINUX`
      (hoje o playbook não mexe no cmdline, então só fica o aviso).
      Ciente (2026-10-01): nada a mudar enquanto o playbook não mexer no cmdline.

## 8. Resto do código — sem mudança necessária

`common` (Flathub, ZSH/Oh-My-Zsh, aliases, Antigravity), `desktop` (Konsole, Ptyxis,
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
- [x] `README.md` — tabela de variáveis do vault: tirar `mok_password` (agora no `all.yml`).

- [x] `README.md` reescrito para AlmaLinux 10 (sem NVIDIA/ASUS, vault só com `api_keys`, seção VirtualBox + Secure Boot, tabela de diferenças vs AFPI).
- [x] `bootstrap.sh` — cabeçalho, mensagens e "root of the afpi project" → AAPI.
- [x] `site.yml` — task `AFPI | Final Status` → `AAPI | Final Status` (banner realinhado).
- [x] `group_vars/all/all.yml:19` — comentário "Retired into Fedora 44" (removido na seção 4).
- [x] `git init` + commit baseline (`497f521`).

---

## 10. Máquina do trabalho (2026-09-29)

- [x] O AAPI será usado em máquina do trabalho: **não altera mais o hostname** (task e
      `system_hostname` removidos; o CN da chave MOK do VirtualBox usa o hostname atual).
- [x] Aliases pessoais `open-thevoid` / `close-thevoid` (LUKS local) removidos do `zsh_aliases`.

---

## 11. Roteiro de testes na VM (VirtualBox, AlmaLinux 10 + EFI + Secure Boot)

Tudo o que container não cobre. Marcar cada etapa ao concluir; anotar aqui qualquer falha.

### Etapa 0 — Criar a VM (no host)
Sintaxe conferida no VBoxManage 7.2 do host (`Oracle10_64`, `--firmware=efi`, `modifynvram`):
```bash
VM=alma10-aapi; DIR="$HOME/VirtualBox VMs/$VM"
VBoxManage createvm --name=$VM --ostype=Oracle10_64 --register
VBoxManage modifyvm $VM --memory=6144 --cpus=4 --firmware=efi --graphicscontroller=vmsvga --vram=128 --nic1=nat
VBoxManage createmedium disk --filename="$DIR/$VM.vdi" --size=40960
VBoxManage storagectl $VM --name=SATA --add=sata --controller=IntelAhci
VBoxManage storageattach $VM --storagectl=SATA --port=0 --device=0 --type=hdd --medium="$DIR/$VM.vdi"
VBoxManage storageattach $VM --storagectl=SATA --port=1 --device=0 --type=dvddrive \
  --medium="$HOME/Downloads/AlmaLinux-10-latest-x86_64-dvd.iso"
# Secure Boot: chaves padrão (Microsoft + Oracle PK) e ativação
VBoxManage modifynvram $VM inituefivarstore
VBoxManage modifynvram $VM enrollmssignatures
VBoxManage modifynvram $VM enrollorclpk
VBoxManage modifynvram $VM secureboot --enable
```
(Pela interface: Sistema → Habilitar EFI + Habilitar Secure Boot → "Redefinir chaves para o padrão".)
- [x] Instalar com o ambiente **Workstation** (GNOME), usuário administrador (`wheel`).
      Feito com a edição **KDE** (2026-10-01): por isso as tasks GNOME/Ptyxis foram puladas na VM
      e validadas só em container.
- [x] Na VM: `mokutil --sb-state` → `SecureBoot enabled`. Anotar `hostname` e `uname -r`.
- [x] Snapshot limpo: `VBoxManage snapshot alma10-aapi take limpo` (VM desligada).
      Etapa verificada (2026-10-01).

### Etapa 1 — Bootstrap
```bash
git clone https://github.com/phguima/aapi && cd aapi && ./bootstrap.sh
```
- [x] `bootstrap.sh` instala `ansible-core`, `pciutils` e `community.general` sem erro.
      Verificado na VM (2026-10-01), já com a `community.general` fixada em 11.x (`4e2c826`).
- [x] `--check` em máquina limpa (2026-09-30): falha por desenho, não é bug. Em check mode os
      repos (EPEL, RPM Fusion, VirtualBox, Brave, VS Code, gh) só são "simulados", então a 1ª task
      que instala pacote de um deles quebra — na VM foi `Codecs | Swap ffmpeg-free for full ffmpeg`
      com `No package ffmpeg available` (`rpm -qa | grep -i rpmfusion` vazio). O `--check` foi
      movido para a etapa 5, depois do setup completo.

### Etapa 2 — 1ª execução: atualizar e reiniciar se necessário
```bash
ansible-playbook -i inventory.ini site.yml -K --ask-vault-pass 2>&1 | tee run0.log
```
- [x] Se o update exigir reboot, o playbook **para** com "needs a REBOOT before continuing"
      (sem os outros roles, sem o banner final). Se não exigir, segue direto (etapa 3).
- [x] Se parou: reiniciar; `uname -r` → kernel mais recente.
      Verificado numa VM nova (2026-10-01): parou no gate e, após o reboot, kernel atualizado.

### Etapa 3 — 2ª execução: setup completo, registro da chave e VirtualBox
```bash
ansible-playbook -i inventory.ini site.yml -K --ask-vault-pass 2>&1 | tee run1.log
```
- [x] O `update` passa direto (sem reboot pendente) e termina com `failed=0` e o banner
      `AAPI DEPLOYMENT COMPLETED SUCCESSFULLY!`.
- [x] O VirtualBox compila **e assina** o `vboxdrv` já na instalação (há `kernel-devel` do kernel em
      uso). Aparece o aviso pedindo reboot + "Enroll MOK" (senha `alma-aapi`).
- [x] Reboot → tela azul do MokManager → **Enroll MOK** → Continue → senha `alma-aapi` → Reboot.
      (Se não aparecer: `sudo mokutil --list-new` antes do reboot deve listar a chave.)
- [x] `sudo mokutil --test-key /var/lib/shim-signed/mok/MOK.der` → "is already enrolled".
      (`sudo` obrigatório nos dois comandos, confirmado na VM; no `--test-key` porque o `MOK.der`
      fica num diretório `0700` de root.)
- [x] `lsmod | grep vboxdrv` → carregado; `modinfo -F signer vboxdrv` →
      `<hostname> VirtualBox module signing`.
- [x] `systemctl status vboxdrv` ativo; `VBoxManage --version` → 7.2.x; usuário nos grupos
      `vboxusers` e `vboxsf` (`id`, após novo login).
      Etapa verificada na VM (2026-10-01).

### Etapa 4 — Conferência por role
- [x] **Repos:** `dnf repolist` → `crb`, `epel`, `rpmfusion-free-updates`, `rpmfusion-nonfree-updates`,
      `virtualbox`, `brave-browser`, `code`, `gh-cli`; `dnf repolist --enabled | grep -i debug` → vazio.
- [x] **Multimídia:** `rpm -q ffmpeg` (e `ffmpeg-free` ausente). A GPU da VM (VMSVGA) não é Intel,
      então os drivers Intel devem ter sido pulados.
- [x] **Apps:** `rpm -q chromium clamav 7zip ShellCheck vim-enhanced uv brave-browser code gh`;
      `systemctl is-active clamav-freshclam`; `flatpak list --app` com os apps de `flatpak_apps_*`.
- [x] **Shell:** `echo $SHELL` → zsh (novo login); tema `kali-like-alt`; `grep -A3 "BEGIN API" ~/.zshrc`
      com o conteúdo do vault; aliases presentes (e nenhum `thevoid`).
- [x] **Hostname:** igual ao anotado na etapa 0.
- [x] **GRUB:** `grep -E "GRUB_TIMEOUT|GRUB_GFXMODE" /etc/default/grub`;
      `sudo ls -l /boot/grub2/grub.cfg` (`sudo` obrigatório: `/boot/grub2` é `0700` de root)
      com data da execução; menu no boot espera 5 s.
- [x] **Fontes:** `cat /usr/local/share/fonts/roboto/.version` → versão atual;
      `fc-list : family | grep -c '^Roboto'` → 8; `fc-list | grep -i "fira code"`.
- [x] **Ptyxis:** abre com 120x35, cursor sublinhado, Fira Code 10, opacidade 0.95.
      Não testado na VM (KDE). Validado em container (2026-10-01) com sessão D-Bus do usuário e
      `sudo`: os valores chegam ao dconf do usuário. Abrir o Ptyxis de fato fica para um host GNOME.
- [x] **Cedilha** (após logout/login): no editor de texto e no Brave, `'` + `c` → `ç` (e `'` + `C` → `Ç`).
- [x] **AI tools:** `claude --version`; `pipx list` com markitdown, notebooklm-py, pdf2docx.
      Etapa verificada na VM (2026-10-01).

### Etapa 5 — Idempotência
```bash
ansible-playbook -i inventory.ini site.yml -K --ask-vault-pass 2>&1 | tee run2.log
```
- [x] Não para no reboot gate (nada novo desde o boot).
- [x] `changed=` só nas tasks sabidamente não idempotentes: as 3 do Ptyxis
      (`GNOME | Set PTYxis ...`, sem `changed_when`, herdadas do AFPI). Qualquer outra é bug.
      Idempotência verificada na VM (2026-10-01). Na VM KDE as 3 do Ptyxis são puladas.
- [x] 🟡 Opcional depois: dar `changed_when` real às 3 tasks do Ptyxis (comparar com `gsettings get`
      / `dconf read` antes de escrever).
      Feito (2026-10-01): cada valor é lido antes e depois da escrita e só conta como `changed`
      se mudou. Validado em container (sessão D-Bus + `sudo`): 1ª execução `changed=3`, 2ª
      `changed=0`; alterando 2 valores à mão, só esses 2 itens voltam e a seguinte dá `changed=0`.
      Agora a idempotência esperada é `changed=0` em tudo, também no GNOME.
- [x] `--check` com tudo já instalado (repos presentes, então o resultado passa a valer):
      `ansible-playbook -i inventory.ini site.yml -K --ask-vault-pass --check` → esperado
      `failed=0`. Anotar aqui cada task que falhar (só a etapa da Roboto foi validada em check
      mode; tasks que dependem de `register` de comando podem quebrar).
      Verificado na VM (2026-10-01): `failed=0`, nenhuma task quebrou.

### Etapa 6 — Limpeza de kernels e rebuild do `vboxdrv` em outro kernel
- [x] Seguir o roteiro da seção 2 (`kernel_maintenance.yml:40`): testes 1, 2 (kernel em uso) e 3.
- [x] No teste 2, instalar também o `kernel-devel` da versão antiga
      (`sudo dnf install kernel-<ver> kernel-devel-<ver>`). Ao dar boot nela, o `vboxdrv.sh` deve
      compilar e **assinar** o módulo para esse kernel: `lsmod | grep vboxdrv` e
      `modinfo -F signer vboxdrv` (cobre o caso "entrou kernel novo" sem esperar um update real).
- [x] Após instalar o kernel antigo, uma execução **completa** para no reboot gate (esperado: sim,
      o `needs-restarting -r` conta qualquer kernel instalado depois do boot, mesmo mais antigo).
      Os testes com `--tags kernel` não passam pelo gate, que só roda com a tag `update`.
      Etapa verificada na VM (2026-10-01).

### Etapa 7 — Roboto: atualização e GitHub fora
- [x] Simular versão antiga: `echo v0 | sudo tee /usr/local/share/fonts/roboto/.version` e
      `--tags roboto` → reinstala e volta à versão atual.
- [x] Sem rede (`nmcli networking off`), `--tags roboto` → só o aviso, fontes mantidas;
      depois `nmcli networking on`.
      Etapa verificada na VM (2026-10-01).

### Etapa 8 — Secure Boot desligado (opcional)
- [x] Restaurar o snapshot `limpo`, desligar o Secure Boot (`VBoxManage modifynvram alma10-aapi
      secureboot --disable`), rodar o playbook: nenhuma task de MOK roda, sem aviso de reboot, e
      o `vboxdrv` carrega sem assinatura.
      Etapa verificada na VM (2026-10-01).

## 12. Port das melhorias do AFPI (`PORTAR_DO_AFPI.md`)

- [x] Bloco 1, zsh e Antigravity (itens 1, 2, 3, 4 e 8 do `PORTAR_DO_AFPI.md`), feito em 2026-10-04:
      - `zsh_aliases` virou `zsh_aliases_common` (todo `.zshrc`, root incluído) e
        `zsh_aliases_user` (só o usuário: `claudecli`, `agycli`, `antigravity-ide`, `full-update`).
      - Alias `antigravity` → `antigravity-ide`, chamando `{{ antigravity_ide_dir }}/antigravity`
        direto (sem `cd`, log no terminal). O instalador do CLI não apaga mais o alias.
      - `Antigravity | Install Antigravity CLI for the user`: antes do bloco de aliases e só para o
        usuário (`when: item.name == user_name`).
      - Bloco `API CONFIGURATION` só no `.zshrc` do usuário, com `no_log: true`; task nova remove o
        bloco do `.zshrc` do root.
      - `full-update` termina com `dnf needs-restarting -r` (dnf4: sem o `-r` lista processos).
      - Role `apps`, seção `Shortcuts` nova (tags `shortcuts`, `antigravity`): pasta
        `~/.local/share/applications`, ícone extraído do `app.asar`
        (`roles/apps/files/extract_asar_file.py`, copiado do AFPI), `antigravity.desktop` e
        `update-desktop-database`. Pulado quando a IDE não está em `antigravity_ide_dir`.
      Validado (2026-10-04) em container `almalinux:10` (`ansible-core` 2.16, `community.general`
      11.x), `--tags aliases,setup,shortcuts,antigravity`, partindo do formato antigo (bloco de
      aliases com `alias antigravity=…` e bloco das chaves no `.zshrc` do root e do usuário) e com a
      pasta real da IDE montada: `--check` antes não altera os `.zshrc` (`sha256sum`); 1ª execução
      `changed=6` (root só com os aliases comuns e sem o bloco das chaves; usuário com tudo; `agy`
      só do usuário; ícone 512×512 e `.desktop` com `desktop-file-validate` sem erros); 2ª execução
      e `--check` com `changed=0`. O `desktop-file-utils` vem com o `gnome-shell` e o
      `plasma-workspace` (conferido com `dnf install --assumeno`).
- [x] Bloco 2, git e `gh` (itens 5 e 6 do `PORTAR_DO_AFPI.md`), feito em 2026-10-04:
      - `.gitignore` novo (o AAPI não tinha), com `host_vars/`, `*.retry`, `*.pyc` e `.vault_pass`.
      - `bootstrap.sh`, passo 4: pergunta `user.name` e `user.email` (Enter mantém o valor salvo ou
        o do `~/.gitconfig`; vazio = não mexe; e-mail validado; sem terminal não pergunta) e grava em
        `host_vars/127.0.0.1.yml` com PyYAML. Diferente do AFPI: **mescla** com o que já está no
        arquivo, em vez de sobrescrever, e não pergunta o hostname.
      - `all.yml`: `git_user_name`/`git_user_email` vazios e `git_config_defaults`
        (`init.defaultBranch=main`, `pull.ff=only`). Role `common`, tag `git`: `git_config` no
        `{{ user_home }}/.gitconfig` como o usuário; identidade pulada quando vazia.
      - `site.yml`: `GitHub CLI | Check login` (`slurp` do `~/.config/gh/hosts.yml`) e
        `GitHub CLI | Remind to log in` quando não há `github.com:`. README: bootstrap, seção
        "GitHub CLI login" e a tag `git`.
      Validado (2026-10-04) em container `almalinux:10` (`expect` para simular o terminal): bootstrap
      recusa e-mail inválido, grava `Ana "Q" O'Brien`; 2ª execução só com Enter mantém tudo e
      preserva uma chave extra (`antigravity_ide_dir`); sem terminal só avisa; `git status` mostra
      `host_vars/` como ignorado; o `python3-pyyaml` vem como dependência do `ansible-core`.
      Playbook `--tags git`: `--check` antes relata as mudanças sem criar o `~/.gitconfig`; 1ª
      execução grava o `~/.gitconfig` do usuário (dono dele; `/root/.gitconfig` não criado; o git lê
      o nome com aspas certo), 2ª execução e `--check` com `changed=0`; identidade vazia → só os
      padrões; lembrete aparece sem `hosts.yml` e com `hosts.yml` vazio, some com `github.com:`;
      `shellcheck` limpo. `community.general` 11.x tem o `git_config` com `scope: file`.

### Conferência final na máquina do trabalho (ao terminar o port)

Fazer uma vez, depois de portar todos os blocos, com o repo atualizado (`git pull`). Cada bloco
entra aqui ao ser portado.

- [ ] **Bootstrap** (bloco 2): `./bootstrap.sh` pergunta `user.name` e `user.email` (Enter mantém o
      que está no `~/.gitconfig`; e-mail inválido é recusado); `cat host_vars/127.0.0.1.yml` mostra
      os dois; `git status` não lista o `host_vars/` (está no `.gitignore`).
- [ ] **Execução:** `ansible-playbook -i inventory.ini site.yml -K --ask-vault-pass`. Se o reboot gate
      parar o play, reiniciar e rodar de novo. Anotar o `PLAY RECAP` (`failed=0`).
- [ ] **Idempotência:** rodar de novo → `changed=0`; depois `--check` → `failed=0`.
- [ ] **`.zshrc` do root** (bloco 1): `sudo cat /root/.zshrc` → bloco de aliases só com `zshconfig`,
      `ohmyzsh`, `lls`, `llsa`, `clean-cache`; sem o bloco `API CONFIGURATION`; sem `alias
      antigravity=`.
- [ ] **`.zshrc` do usuário** (bloco 1): `source ~/.zshrc`; `alias antigravity-ide` aponta para
      `~/wks/tools/antigravity/antigravity`; `alias full-update` termina com
      `dnf needs-restarting -r`; as chaves de API continuam carregadas (`env | grep -c API`, sem
      mostrar os valores).
- [ ] **Antigravity IDE** (bloco 1): `cd ~ && antigravity-ide` abre a IDE com o log no terminal; pelo
      menu, o Antigravity aparece com o ícone, abre, e a janela fica agrupada no mesmo ícone da
      dock/barra de tarefas (se aparecer um ícone genérico separado, conferir o `app_id` e ajustar
      o `StartupWMClass`).
- [ ] **`full-update`** (bloco 1): termina com a resposta do `needs-restarting -r` (reboot necessário
      ou não).
- [ ] **Limpeza do `agy` do root** (bloco 1, à mão): conferir com `sudo ls /root/.local/bin` e
      `sudo grep -n local/bin /root/.zshrc /root/.bashrc /root/.bash_profile`; depois rodar os
      comandos do item 2 do `PORTAR_DO_AFPI.md`. O `agy` do usuário continua funcionando
      (`agy --version`).
- [ ] **Git** (bloco 2): `git config --global --list` → `user.name`, `user.email`,
      `init.defaultBranch=main`, `pull.ff=only`; `ls -l ~/.gitconfig` com o usuário como dono;
      `sudo ls /root/.gitconfig` → não existe.
- [ ] **GitHub CLI** (bloco 2): sem login, o fim do play mostra `GitHub CLI | Remind to log in`;
      depois de `gh auth login --hostname github.com --git-protocol https --web` e
      `gh auth setup-git`, a execução seguinte não mostra o lembrete.
- [ ] **Fechamento:** marcar os itens acima, apagar o `PORTAR_DO_AFPI.md` (tudo portado), atualizar
      versão e "Validation" no README e criar a tag/release (item 9 do `PORTAR_DO_AFPI.md`).

---

## Ordem sugerida

1. ~~`git init` + commit do estado atual~~ ✅ feito.
2. ~~Seção 1 (bootstrap + CRB/EPEL/RPM Fusion)~~ ✅ feito.
3. ~~Seções 4 e 5 (listas de pacotes, Roboto, VirtualBox)~~ ✅ feito.
4. ~~Seção 3 (remoção de NVIDIA/Steam)~~ ✅ feito.
5. ~~Seções 7 e 2 (6 já feita)~~ ✅ feito.
6. ~~Seção 9 (renomear) + README~~ ✅ feito.
7. ~~Testes na VM AlmaLinux 10 com EFI + Secure Boot (seção 11)~~ ✅ feito (2026-10-01).
   Resta só o opcional 🟡 dos freeworld do VLC/HEIF (seção 4).
8. Port das melhorias do AFPI (seção 12 e `PORTAR_DO_AFPI.md`): blocos 1 (zsh e Antigravity) e 2
   (git e `gh`) ✅ feitos; faltam os opcionais (7 e 9) e a conferência final na máquina do trabalho.
