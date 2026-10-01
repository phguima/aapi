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
- [ ] 🟡 `kernel_maintenance.yml:40` — `repoquery --installonly --latest-limit=-1` funciona no dnf4,
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
- [x] `README.md` ainda cita ASUS (linhas 23, 39, 79-86, 93) — resolvido na reescrita do README.

## 7. GRUB

- [x] Handler `Regenerate GRUB` (`site.yml`) agora grava em `/boot/grub2/grub.cfg`.
      Correção da auditoria: no EL10 `/etc/grub2-efi.cfg` já é symlink para esse arquivo, então em
      UEFI o handler antigo funcionava; a troca deixa explícito e cobre boot BIOS (sem
      `grub2-efi-x64` o symlink não existe e o antigo criaria um arquivo solto em `/etc`).
- [ ] 🟡 O EL usa BLS + `grubby`; parâmetros de kernel devem ir via `grubby`, não `GRUB_CMDLINE_LINUX`
      (hoje o playbook não mexe no cmdline, então só fica o aviso).

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
      Idempotência verificada na VM (2026-10-01).
- [ ] 🟡 Opcional depois: dar `changed_when` real às 3 tasks do Ptyxis (comparar com `gsettings get`
      / `dconf read` antes de escrever).
- [x] `--check` com tudo já instalado (repos presentes, então o resultado passa a valer):
      `ansible-playbook -i inventory.ini site.yml -K --ask-vault-pass --check` → esperado
      `failed=0`. Anotar aqui cada task que falhar (só a etapa da Roboto foi validada em check
      mode; tasks que dependem de `register` de comando podem quebrar).
      Verificado na VM (2026-10-01): `failed=0`, nenhuma task quebrou.

### Etapa 6 — Limpeza de kernels e rebuild do `vboxdrv` em outro kernel
- [ ] Seguir o roteiro da seção 2 (`kernel_maintenance.yml:40`): testes 1, 2 (kernel em uso) e 3.
- [ ] No teste 2, instalar também o `kernel-devel` da versão antiga
      (`sudo dnf install kernel-<ver> kernel-devel-<ver>`). Ao dar boot nela, o `vboxdrv.sh` deve
      compilar e **assinar** o módulo para esse kernel: `lsmod | grep vboxdrv` e
      `modinfo -F signer vboxdrv` (cobre o caso "entrou kernel novo" sem esperar um update real).
- [ ] Após instalar o kernel antigo, uma execução **completa** para no reboot gate (esperado: sim,
      o `needs-restarting -r` conta qualquer kernel instalado depois do boot, mesmo mais antigo).
      Os testes com `--tags kernel` não passam pelo gate, que só roda com a tag `update`.

### Etapa 7 — Roboto: atualização e GitHub fora
- [ ] Simular versão antiga: `echo v0 | sudo tee /usr/local/share/fonts/roboto/.version` e
      `--tags roboto` → reinstala e volta à versão atual.
- [ ] Sem rede (`nmcli networking off`), `--tags roboto` → só o aviso, fontes mantidas;
      depois `nmcli networking on`.

### Etapa 8 — Secure Boot desligado (opcional)
- [ ] Restaurar o snapshot `limpo`, desligar o Secure Boot (`VBoxManage modifynvram alma10-aapi
      secureboot --disable`), rodar o playbook: nenhuma task de MOK roda, sem aviso de reboot, e
      o `vboxdrv` carrega sem assinatura.

---

## Ordem sugerida

1. ~~`git init` + commit do estado atual~~ ✅ feito.
2. ~~Seção 1 (bootstrap + CRB/EPEL/RPM Fusion)~~ ✅ feito.
3. ~~Seções 4 e 5 (listas de pacotes, Roboto, VirtualBox)~~ ✅ feito.
4. ~~Seção 3 (remoção de NVIDIA/Steam)~~ ✅ feito.
5. ~~Seções 7 e 2 (6 já feita)~~ ✅ feito.
6. ~~Seção 9 (renomear) + README~~ ✅ feito.
7. **Pendente:** testes na VM AlmaLinux 10 com EFI + Secure Boot — roteiro completo na **seção 11**.
