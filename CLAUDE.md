# AAPI — instruções para o Claude

AAPI (Ansible AlmaLinux Post-Install): port do AFPI (`phguima/afpi`, Fedora) para **AlmaLinux 10**.
Repo público `phguima/aapi`, branch única `main`, GPL-3.0. O usuário conversa em português.

O alvo é uma **máquina do trabalho**. Por isso, por decisão de 2026-09-29:
- o hostname **nunca** é alterado;
- não há suporte a NVIDIA, Steam e ASUS ROG (removidos);
- o VirtualBox vem do repositório da Oracle e funciona com Secure Boot;
- o `mok_password` fica em `group_vars/all/all.yml`, e não há vault desde 2026-10-04: `api_keys` é
  `""` no `all.yml`. Um vault opcional em `group_vars/all/secrets.yml` (no `.gitignore`) pode
  defini-lo; se existir, o Claude não tem a senha: não tentar abrir.

Melhorias de arquitetura feitas aqui (reboot gate, MOK idempotente, `is_secure_boot`, Ptyxis com
`changed` real…) foram levadas para o AFPI. Ao portar algo entre os dois, adaptar o que é de cada
distro: o EL10 usa **dnf4** (4.20), CRB + EPEL + RPM Fusion EL e `ansible-core` 2.16.

## Estado do trabalho

`TODO.md` (em português) tem **só o que falta**. O histórico (auditoria do port, roteiro da VM,
port do AFPI e como cada item foi validado) foi tirado dele em 2026-10-04 e fica no git:
`git show e4de25f:TODO.md`. O usuário costuma pedir "mostre o todo" e espera um status
**compacto por seção**. Ao concluir um item, removê-lo do `TODO.md` e registrar a validação na
mensagem do commit; tarefa nova entra no `TODO.md` até ser feita.

Status em 2026-10-01: tudo feito, inclusive o roteiro de testes na VM (seção 11, EFI + Secure
Boot). Resta só o item opcional 🟡 dos codecs freeworld do VLC/HEIF, bloqueado até o EPEL
alcançar as versões do RPM Fusion. A VM de teste era **KDE**: o que é só do GNOME (Ptyxis) foi
validado só em container.

Entre 2026-10-03 e 2026-10-04 foram portadas as melhorias do AFPI até a versão 2.9.0 (seção 12
do `TODO.md` histórico; a lista `PORTAR_DO_AFPI.md` foi apagada e também fica no git), conferidas
na VM e publicadas como **v1.1.0** (tag e release). Algo novo a portar do AFPI entra no `TODO.md`.

## Git

- Começar com `git fetch` + `git pull --ff-only`. Conferir de novo antes de cada push.
- Commit e push **só quando o usuário pedir**. Commits em inglês, Conventional Commits com escopo
  (`feat(update): …`, `fix(desktop): …`, `docs(todo): …`).
- Se o `git push` for bloqueado pelo classificador do modo automático (aconteceu antes de
  2026-09-30), pedir ao usuário para rodar `! git -C <caminho do repo> push`.

## Testes — em container, nunca no host

Validar em container podman `docker.io/library/almalinux:10`, **duas vezes** (idempotência:
`changed=0` na 2ª) e também com `--check`, antes de commitar. Nunca rodar o playbook no host.

- O container puro não tem o que uma instalação Workstation já traz (ex.: `vlc-libs`, `libheif`).
  Preinstalar os pacotes relevantes para a mudança, senão bugs passam (a falha de depsolve do
  `@multimedia` em 2026-09-30 passou assim).
- Tasks só do GNOME: simular a sessão com um usuário comum com D-Bus de sessão,
  `XDG_CURRENT_DESKTOP=GNOME` e o playbook via `sudo` (o `env_setup` usa o `SUDO_USER`).
- As receitas detalhadas (Secure Boot falso via `/sys/firmware`, `mokutil` falso, wrapper de
  `dnf needs-restarting`, `:z` vs `:Z`, `-e` em JSON para booleanos, `-e api_keys` para testar o bloco de API)
  estão no `CLAUDE.md` do AFPI e valem aqui também, trocando a imagem e o dnf5 pelo dnf4.
- O que depende de hardware (build real do `vboxdrv`, enroll no MokManager, reboot) vai para a VM.

## VM de teste

O usuário roda as conferências na VM (roteiro de referência: seção 11 do `TODO.md` histórico) e
manda os resultados como screenshots em
`~/Pictures/Screenshots`. Os nomes dos arquivos mudam: listar o diretório e pegar os mais novos.

## Particularidades do AlmaLinux 10

- `bootstrap.sh` instala `ansible-core` (o pacote `ansible` não existe no EL10) e fixa
  `community.general` em 11.x, a última série compatível com o `ansible-core` 2.16.
- CRB + EPEL precisam vir antes de qualquer outro pacote (role `update`).
- `community.general.dnf_config_manager` funciona aqui (dnf4), ao contrário do Fedora.
- Sem `@multimedia`: as versões freeworld do RPM Fusion costumam exigir `vlc-libs`/`libheif` mais
  novas que as do EPEL e quebram a transação inteira.
- Roboto não é empacotado para o EL10: vem da última release do upstream (role `desktop`).
