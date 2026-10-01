# Revogação SSH por logind sob barreira geracional — 01/10/2026

**24 controles nativos passaram** na VM descartável. A barreira v2 impede
novas autorizações SSH; `loginctl terminate-user` encerra os transportes
existentes da conta afetada, preservando conexões da outra conta e o listener
compartilhado. A saída de seis processos SSH, incluindo três monitores root,
foi verificada por pidfds. Não há reinício global de SSH nem sinais próprios
contra processos root.

## Integração experimental

[O adapter PAM](pam-account-guard.c) usa a leitura, identidade explícita,
barreira e lease por geração do [protótipo v2](../parental-registry-barrier/README.md),
agora na fase `account`. O override de `sshd` o instala como `requisite`
antes da pilha vendor preservada. `UsePAM yes` é conferido na configuração
efetiva; a escuta da fixture fica exclusivamente em `127.0.0.1:22`.

O lease é adquirido antes de decidir a autorização e mantido no handle PAM
até `pam_end`. Nesta versão do OpenSSH ele permanece no monitor root
`sshd-session` e no processo da conexão após autenticar. Isso cobre o transporte
que pode abrir vários canais; não depende de haver um shell naquele momento.
A barreira passa a negar a fase account de handles iniciados anteriormente
que ainda aguardavam a senha, desde que o adapter já estivesse instalado.

O adapter admite a associação ativa **somente para construir a baseline e
exercitar transportes antigos**. Não é a regra de produto: a política anterior
continua sendo recusar integralmente login/CLI/SSH/SFTP/túneis da conta
supervisionada. O teste não aprova habilitar essas entradas na distribuição.
O adapter account também não faz a validação de contexto de execução do guard
de sessão gráfica. Os payloads baseline são unconfined, não aplicativos
confinados nem sessões parentais de produção.

[A rotina de revogação](revoke.py) exige barreira já publicada. Identifica
holders do lease correto, confere executáveis oficiais root-owned, identidade
e escopos `user-<uid>.slice/session-*`, e fixa as referências com pidfds.
Só então chama a operação nativa de logind; exige saída de todos os holders e
liberação do lease. Falha conserva a barreira e interrompe o ensaio. Essa
rotina é exclusiva da VM, não um serviço autorizado de migração de contas.

## O que foi observado

| Cenário | Resultado |
| --- | --- |
| Baseline por chave e senha real | Comandos executam e encerram normalmente |
| `ssh -N -L` de ambas as contas | Encaminha dados; os transportes aparecem em sessões PAM/logind |
| Publicação da barreira com conexões abertas | Busy conserva negação, mas o túnel antigo ainda transporta dados |
| ControlMaster antigo sob a barreira | Ainda consegue abrir um comando antes de revogar o transporte |
| `loginctl terminate-user` da conta afetada | Encerra túnel, comando persistente e ControlMaster; seis pidfds ficam prontos |
| Conexões comuns e listener compartilhado | Continuam ativos; túnel comum permanece funcional durante toda a transição |
| Senha iniciada antes da barreira | Cliente permanece vivo após logind; senha correta posterior é recusada na fase account |
| Comando, SFTP, túnel e tentativa de usar o mux antigo | Recusados após revogação, com causa exata PAM account |
| Publicação de geração nova com configuração PAM antiga | Continua recusada |
| Enrollment explícito e atualização da associação PAM | Nova autenticação e novo túnel da baseline voltam a funcionar |

As seis negativas exigem uma nova causa do módulo fixture e a mensagem de
negação PAM account do OpenSSH, em ordem, dentro do trecho de journal de cada
tentativa. As tentativas são sequenciais; a outra conta mantém transportes
ociosos. Retorno255, perda de socket ou penalidade de IP sozinhos não bastam.
As penalidades upstream continuam habilitadas; o teste lê sua duração efetiva
e espaça negativas em seis segundos.

O teste corrige uma inferência do harness anterior: **sem shell não significa
sem sessão PAM/logind**. O campo `no_session` da antiga fixture descrevia a
intenção de `-N`, mas não inventariava logind. A nova fixture registra as sessões
e os cgroups reais. Sua primeira rodada também revelou que excluir contas logo
após solicitar terminate-user corre antes do encerramento do user manager;
a limpeza agora para explicitamente managers/runtime e aguarda processos.
Isso é correção da observação e limpeza do ensaio, não um bug upstream resolvido.

## Reprodução e integridade

Exige exclusivamente a VM com marcadores `lyra.parental-selinux-test=1`,
`lyra.parental-identity-test=1`, serial `lyra-admission-test`, disco
`/tmp/lyra-parental-identity-20260928/system.raw`. Executar sem otimização Python;
as assertions são pré-condições do ensaio, não controles de produto.

| Fonte | Destino guest |
| --- | --- |
| `pam-account-guard.c` | `/root/ssh-pam-account-guard.c` |
| `registry.cil` | `/root/lyra-ssh-registry.cil` |
| `revoke.py` | `/root/ssh_revoke.py` |
| `exercise.py` | `/root/ssh-revocation-exercise.py` |
| `restore-check.py` | `/root/ssh-revocation-restore-check.py` |
| `../parental-registry-barrier/writer.py` | `/root/barrier-writer.py` |

Executar exercise e depois restore-check sequencialmente. Senhas e chaves são
geradas apenas no guest; senha via stdin/PTY com eco desabilitado. Fingerprints
públicos e transcripts não contêm senhas/chaves privadas. Remover fixtures
antes de desligar. O módulo C compila com `-Wall -Wextra -Werror`.

[Resultados](result.json), [restauração independente](restored.json) e
[proveniência com IDs/hashes](provenance.json) vinculam a rodada final.
O verificador offline passou:

```sh
python3 docs/evidence/parental-ssh-revocation/verify-evidence.py
python3 -m unittest discover -s tests -p 'test_*.py'
```

A suíte existente passou com **270 testes**. A VM retornou a Permissive;
sshd padrão permaneceu disabled/inativo. Contas/grupos/homes/chaves/configuração
PAM/registro/módulo/CIL temporários removidos, sessão e processos ausentes,
listener e managers da fixture parados. VM OFF e QEMU terminou com código0.
Nenhuma mudança no host, receita, OBS ou ISO.

## Limites e próximo ensaio

O resultado vale para OpenSSH10.3p1-160100.2.4, systemd257.13-160100.2.5 e
PAM1.7.2+git12-160100.2.1 na cópia de VM, com PAM/logind efetivos e pilha
preservada. Outra configuração que omita PAM ou registro de sessões exige
qualificação própria. Um handle iniciado sem o adapter não foi migrado.
ControlMaster foi encerrado como transporte, não convertido em outra geração.

Revogação de transportes e liberação de leases não comprovam quiescência de
toda a conta, produtores root, cron/timers, D-Bus, serviços `User=` ou processos
que escapem de seus escopos. Não houve mudança de IDs, retirada de supervisão,
recuperação automática, candidata ISO, update/rollback ou teste de resistência
a invasão. Não há inventário completo AVC; `complete_kernel_audit=false`
permanece, apesar de não haver avisos de backlog nesta rodada.

Próximo: qualificar os produtores persistentes e sua negação/revogação por
conta. ADR, autorização/recuperação, serviço de ciclo de vida, UI/Polkit e
privacidade continuam pendentes. #6/#102 seguem abertas.

Referências de integração: [OpenSSH UsePAM](https://github.com/openssh/openssh-portable/blob/master/sshd_config.5),
[ciclo PAM upstream](https://github.com/openssh/openssh-portable/blob/master/auth-pam.c)
e [operação terminate-user no manual systemd](https://github.com/systemd/systemd/blob/main/man/loginctl.xml).
As conclusões acima vêm da versão efetivamente executada, não da branch master.
