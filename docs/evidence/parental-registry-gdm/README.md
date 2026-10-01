# Registro por geração no GDM com senha — 01/10/2026

Continuação do [manager nativo e lingering](../parental-identity/README.md).
O [resultado](result.json) registra **22 checks nativos PASS** em VM descartável.
Não qualifica proteção da conta inteira, GNOME completo ou uma ISO candidata.

## Integração exercitada

O ensaio reaproveita o cliente do [GDM com senha da PR140](../parental-password/README.md),
o worker de diagnóstico e a sessão ELF mínima. Usa o protocolo peer real do
greeter e `pam_unix` da pilha vendor, sem substituir a autenticação por
`pam_permit` nem chamar libpam via ctypes. O cliente é iniciado pelo controlador
privilegiado e assume UID/GID do GDM; não testa a UX do greeter, teclado ou
confinamento de um greeter comprometido.

As pilhas `gdm-password` e `systemd-user` recebem o mesmo guard, tupla Unix e
geração aleatória do registro root-only. O módulo e o escritor são idênticos
aos fontes já testados no manager nativo. As credenciais são aleatórias, geradas
apenas dentro da VM e enviadas por stdin; o shadow original é restaurado. Antes
de exportar, o harness verifica que nenhum segredo está no resultado.

`launcher.cil` conserva as permissões anteriores do launcher e acrescenta um
tipo dedicado apenas para os arquivos do registro de fixture. O módulo concede
a `xdm_t` e `init_t` leitura e lock, sem novas permissões de escrita ou criação
nesse tipo. Os caminhos root-only são rotulados pelo controlador com `chcon`
antes das admissões; o escritor ainda não implementa gerenciamento de rótulos
para produto. A política e os arquivos temporários são retirados no final.

## Resultados e limites

| Caso | Resultado observado |
| --- | --- |
| Senha correta e geração ativa | Sessão mínima no UID/contexto supervisionado |
| Sessão aberta | Worker GDM e sd-pam mantêm descritores do inode do lock; `begin` retorna Busy e preserva registro, journal e sessão |
| Encerramento controlado | Leases liberados; nenhuma sessão mínima remanescente |
| `transitioning`, tombstone e geração antiga no PAM após enrollment | Senha correta autentica/autoriza, mas abertura é recusada; desfecho completo do worker registrado |
| Geração nova | Só entra após atualizar explicitamente os argumentos PAM |
| Registro ausente/corrompido, módulo ausente e SELinux permissive | Supervisionada recusada; conta comum entra nos controles correspondentes |
| Autenticação em andamento | Prompt recebido com geração ativa; controlador publica `transitioning`; resposta correta enviada depois; abertura recusada |
| Recuperação após autenticação pendente | Tombstone e enrollment explícito com geração nova permitem nova conversa |
| Senha incorreta | Falha de autenticação; conversa posterior com senha correta abre |

Os oito controles de recusa de abertura exigem causa exata no mesmo worker,
tentativa de `SESSION_OPENED`, retorno a `NONE`, parada pelo manager, sinal
`session-start-failed` e saída do worker. A observação continua por dois segundos
sem parar GDM e exige ausência de payload ou sucesso posterior. Um warning
de dlopen, inclusive de módulo opcional, não satisfaz esse critério. A senha
incorreta tem critério separado de falha de autenticação. O verificador passou
oito testes de regressão; a suíte do repositório passou **270 testes Python**.

O teste do prompt mantém o guard instalado desde o início da conversa. Não
qualifica enrollment de uma conta sem guard nem handles que carregaram a pilha
antiga antes da instalação. Também não revoga conexões antigas, não termina
automaticamente a sessão e não muda a identidade Unix real: novas gerações são
publicadas somente no registro experimental.

O worker continua sendo o build de diagnóstico com o patch de hooks de root
da [etapa GDM](../parental-gdm/README.md), e a sessão é um ELF que fica em
`pause()`. Não houve rebuild de RPM de produção, sessão GNOME supervisionada
completa, teste de desbloqueio/reautenticação ou qualificação ISO. O kernel
registrou perdas de audit por backlog; portanto, estes logs não são um inventário
completo de AVCs. Os checks usam eventos explícitos do GDM/PAM e estado dos
processos, sem inferir aprovação pela ausência de uma negação no audit.

## Restauração e retomada

O resultado confirma restauração do shadow, bytes dos overrides PAM, arquivos
GDM/AccountsService/desktops, hashes vendor, worker oficial e rótulo do launcher.
Módulo PAM, registro, sessão ELF, backup e política CIL foram removidos.
GDM e managers das duas fixtures e do greeter ficaram inativos/PID0, sem
processos das contas; SELinux voltou a permissive. A [verificação independente](restored.json)
confirma ausência de sessões/registro/módulo/política e hash do worker oficial.
A VM foi desligada normalmente. [Proveniência](provenance.json) liga os fontes,
artefatos e IDs reais das execuções.

Próximo: reconciliar registro por geração com a barreira persistente antes de
quiescência e isolamento por conta. O lock atual é global e `Busy` deixa `active`,
sem fechar novas admissões. A fixture anterior das PRs137–140 já exercitou
bloqueio persistente. Revogação SSH, cron/timers, D-Bus, serviços `User=`, ciclo
autorizado de contas e update/rollback continuam pendentes. #6/#102 e o item
parental da Alpha 8 permanecem abertos.

## Reprodução

Usar a cópia marcada com `lyra.parental-selinux-test=1`,
`lyra.parental-identity-test=1` e serial `lyra-admission-test`, com o build GDM
da fixture anterior. Nunca executar junto com outros ensaios da mesma VM.
Transferir via `analysis/2026-09-28/parental-identity/host.py push`:

| Fonte nesta árvore | Caminho guest |
| --- | --- |
| `exercise.py` | `/root/registry-gdm-exercise.py` |
| `evidence.py` | `/root/registry-gdm-evidence.py` |
| `launcher.cil` | `/root/lyra-registry-gdm.cil` |
| `../parental-identity/pam-registry-guard.c` | `/root/identity-pam-registry-guard.c` |
| `../parental-identity/registry-transaction.py` | `/root/identity-registry-transaction.py` |
| `../parental-transitions/transition.py` | `/root/transition.py` (inventário de processos somente) |
| `../parental-managers/session.c` | `/root/manager-session.c` |
| `../parental-password/client.py` | `/root/password-client.py` |

```sh
python3 analysis/2026-09-28/parental-identity/vm.py virtualization cmd \
  python3 /root/registry-gdm-exercise.py
```
