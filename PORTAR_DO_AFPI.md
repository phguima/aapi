# Melhorias do AFPI para portar ao AAPI

Levantamento de 2026-10-03: o que entrou no AFPI (`phguima/afpi`) depois da última atualização do
AAPI (2026-10-01) e ainda não existe aqui. Cada item cita os commits do AFPI
(`git -C ../afpi show <hash>`) e o que muda no EL10 (dnf4, `ansible-core` 2.16, sem NVIDIA, sem
troca de hostname). Ao portar um item, testar em container `almalinux:10` (duas execuções e
`--check`), marcar no `TODO.md` e riscar aqui. Apagar este arquivo quando tudo estiver portado.

## 1. Antigravity: alias apagado pelo instalador (bug de idempotência)

**AFPI:** `6d8b996`. **Situação no AAPI:** o bug existe.

O instalador do Antigravity CLI (`agy install`) apaga de `.zshrc` qualquer `alias antigravity=...`.
No AAPI, a task `Antigravity | Install Antigravity CLI for users` roda **depois** do bloco de
aliases (`roles/common/tasks/main.yml`), e o `group_vars/all/all.yml` tem
`alias antigravity="cd ~/wks/tools/antigravity; ./antigravity"`. Resultado: o instalador apaga o
alias na 1ª execução, a 2ª o recoloca e dá `changed`.

O que fazer:
- Renomear o alias para `antigravity-ide`, que o instalador não apaga.
- Mover a task do Antigravity para **antes** do `ZSH | Add custom aliases to .zshrc`, com um
  comentário explicando o porquê.

## 2. Antigravity CLI só para o usuário, não para o root

**AFPI:** `b193c88`. **Situação no AAPI:** é instalado para todos os `zsh_users`, root incluído.

O root não tem `~/wks` nem usa o alias `agycli`, então o `agy` dele (~200 MB) não serve para nada.
No AFPI a task ganhou `when: item.name == user_name` e passou a se chamar
`Antigravity | Install Antigravity CLI for the user`.

A task não remove o que já foi instalado. Na máquina do trabalho, limpar à mão o que o instalador
deixou no root (no `noir` foi exatamente isto; conferir antes com `sudo grep` e `sudo ls`):

```sh
sudo sed -i '\|^export PATH="/root/.local/bin:\$PATH"$|d' /root/.zshrc /root/.bashrc /root/.bash_profile
sudo rm /root/.local/bin/agy && sudo rmdir /root/.local/bin
sudo rm -r /root/.cache/antigravity
```

## 3. `.zshrc` do root só com aliases genéricos e sem as chaves de API

**AFPI:** `854d6ee`. **Situação no AAPI:** o root recebe todos os aliases e o bloco
`API CONFIGURATION` com o `{{ api_keys }}` do vault, com `mode: '0644'`.

O root não usa as chaves, e segredo fora de onde é usado só aumenta a exposição. No AFPI:
- `zsh_aliases` virou duas variáveis no `all.yml`:
  - `zsh_aliases_common` (todo `.zshrc`, root incluído): `zshconfig`, `ohmyzsh`, `lls`, `llsa`,
    `clean-cache`;
  - `zsh_aliases_user` (só o usuário): `claudecli`, `agycli`, `antigravity-ide`, `full-update`
    (no AFPI também `nvidia-run` e os do disco `thevoid`, que não existem no AAPI).
- O bloco de aliases usa
  `block: "{{ zsh_aliases_common }}{{ zsh_aliases_user if item.name == user_name else '' }}"`,
  com o mesmo marcador, para o `blockinfile` substituir o bloco antigo do root.
- O bloco das chaves ganhou `when: item.name == user_name` e `no_log: true` (a convenção de
  segredos do `CLAUDE.md`).
- Uma task nova remove o bloco das chaves do `.zshrc` de quem não é o usuário
  (`state: absent`, `when: item.name != user_name`).

Diferença no AAPI: o marcador do bloco das chaves é `API CONFIGURATION` (não
`NVIDIA AND API CONFIGURATION`), e já existe a task que remove o marcador antigo do AFPI. A task
nova de remoção deve usar o marcador `API CONFIGURATION`. Se o playbook for rodado direto como root,
`user_name` é `root` e ele recebe tudo, como antes.

Validação usada no AFPI: container com `/root/.zshrc` e `.zshrc` do usuário no formato antigo
(chave falsa via `-e 'api_keys="export FAKE_KEY=secret"'`): `--check` não altera os arquivos
(conferir com `sha256sum`), 1ª execução `changed=2`, 2ª e `--check` `changed=0`.

## 4. `full-update` avisa quando precisa reiniciar

**AFPI:** `6d4f9e3`. **Situação no AAPI:** o alias termina no `dnf upgrade`.

No AFPI o alias ganhou `; dnf needs-restarting` no fim. **No EL10 tem que ser
`dnf needs-restarting -r`**: no dnf4, sem o `-r`, o comando lista os processos que precisam
reiniciar em vez de dizer se o sistema precisa de reboot. O `-r` não precisa de `sudo`.

```sh
alias full-update="flatpak update -y; sudo npm update -g; sudo dnf upgrade --refresh -y; dnf needs-restarting -r"
```

## 5. Identidade do git perguntada no `bootstrap.sh`

**AFPI:** `b115eb3` (bootstrap), `d4f17c3` (role `common`), `112b94a` (docs). **Situação no
AAPI:** o playbook não mexe no `~/.gitconfig`.

No AFPI:
- O `bootstrap.sh` pergunta `user.name` e `user.email`. Enter mantém o valor salvo ou o do
  `~/.gitconfig`; vazio significa não mexer; o e-mail é validado. Grava em
  `host_vars/127.0.0.1.yml` (por máquina, fora do git), lido e escrito com PyYAML por causa de
  nomes com aspas. Sem terminal (`stdin` não é tty), não pergunta.
- `all.yml`: `git_user_name: ""`, `git_user_email: ""` e `git_config_defaults`
  (`init.defaultBranch: main`, `pull.ff: only`).
- Role `common`, tag `git`: `community.general.git_config` com `scope: file` e
  `file: "{{ user_home }}/.gitconfig"`, `become_user: "{{ user_name }}"`. A identidade é pulada
  quando vazia.

Adaptações no AAPI:
- O bootstrap do AAPI **não** pergunta o hostname (o hostname nunca muda). Portar só a parte do
  git, com as funções `host_var` e `ask` do AFPI, e gravar só `git_user_name`/`git_user_email`.
- O AAPI **não tem `.gitignore`**. Criar um com `host_vars/` antes, senão o arquivo com o nome e o
  e-mail vai para o repo público.
- O PyYAML (`python3-pyyaml`) é dependência do `ansible-core` no EL10, então já está instalado
  depois do passo 1 do bootstrap. Conferir no container.
- O AAPI fixa o `community.general` em 11.x (`ansible-core` 2.16). O `git_config` com
  `scope: file`/`file:` já existe nessa série, mas conferir no container.
- README: a explicação do bootstrap e a tag `git` na tabela de tags.

## 6. Lembrete de login do `gh` no fim do play

**AFPI:** `2c6231d`. **Situação no AAPI:** instala o `gh` e não diz nada sobre o login.

Duas `post_tasks` no `site.yml`, antes do `Final Status`, com `tags: [always]`:
- `GitHub CLI | Check login`: `ansible.builtin.slurp` do `{{ user_home }}/.config/gh/hosts.yml`
  com `failed_when: false`.
- `GitHub CLI | Remind to log in`: `debug` com os comandos
  `gh auth login --hostname github.com --git-protocol https --web` e `gh auth setup-git`, quando
  `'github.com:' not in (gh_hosts.content | default('') | b64decode)`.

Ler o `hosts.yml` em vez de rodar `gh auth status` é proposital: o token fica no keyring, e o
`gh` rodado via sudo não tem a sessão D-Bus do usuário, então diria "não logado" mesmo logado.
Checar o conteúdo, e não só se o arquivo existe, porque depois de um `gh auth logout` o arquivo
pode ficar sem a entrada. README: uma seção "GitHub CLI login" com os dois comandos.

## 7. (Opcional) Reboot gate que também compara os kernels

**AFPI:** `3a5fc3a`. **Situação no AAPI:** o gate usa só `dnf needs-restarting -r`.

No `noir`, o `needs-restarting` do dnf5 respondeu rc 0 logo depois de instalar um kernel novo,
porque o RTC estava em hora local (dual boot com Windows) e o horário de boot do systemd ficou
errado. O AFPI passou a parar também quando `uname -r` difere do `kernel-core` mais novo instalado.

Na máquina do trabalho, sem dual boot, o problema não deve aparecer, e o dnf4 calcula o horário de
boot de outro jeito. Vale portar só como robustez: é uma checagem barata e não depende do relógio.

## 8. (Opcional) Tags de versão e releases

**AFPI:** tag `v2.7.0` e release no GitHub (2026-10-03). **Situação no AAPI:** a versão só existe
no README (`1.0.0 (port of AFPI 2.6.0)`), sem tags.

```sh
git tag -a v1.0.0 -m "AAPI 1.0.0" <commit da versão> && git push origin v1.0.0
gh release create v1.0.0 --repo phguima/aapi --title "AAPI 1.0.0" --notes-file <notas>.md
```

Depois de portar os itens acima, faz sentido uma `1.1.0`.

## Não se aplica ao AAPI

- **NVIDIA numa execução só, RTD3 e o widget de GPU do Plasma** (`33c1d00` e os achados do
  `TODO.md` do AFPI): o AAPI não tem NVIDIA.
- **Hostname perguntado no bootstrap** (`5adfe25`): no AAPI o hostname nunca muda.
- **Remover os kmods do akmods junto com os kernels antigos** (`a49e5d4`): o VirtualBox do AAPI vem
  da Oracle e não gera pacotes `kmod-*`.
- **ZapZap** (`9da9e63`): escolha pessoal de app. Portar só se quiser na máquina do trabalho.
