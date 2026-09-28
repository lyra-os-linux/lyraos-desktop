# Admissão nativa em login e SSH — 28/09/2026

Esta etapa testa uma política conservadora para as entradas de terminal da
conta supervisionada: **recusar login local, comandos SSH, SFTP e túneis novos**.
A sessão gráfica e seus aplicativos aprovados continuam sendo uma frente
separada. A regra só foi aplicada e removida na VM descartável; não foi ativada
na distribuição, no host ou em contas reais.

## Integração com a base

`policy.py` reaproveita os vínculos de nome/UID/GID validados na
[etapa de identidade](../parental-identity/README.md). Gera duas linhas `account`:
`pam_succeed_if` só pula `pam_deny` quando nome, UID e GID não coincidem com
nenhuma conta supervisionada. Coincidência parcial ou erro de consulta não
produz esse salto. O bloqueio é `requisite` e precede a pilha do fornecedor,
preservada integralmente. Autenticação, senha e sessões da conta comum seguem
usando os módulos originais; não há módulo C novo para essas duas entradas.

A fase `account` é necessária porque SSH permite operações sem abrir shell.
Com `UsePAM yes`, o OpenSSH aplica a autorização PAM também à autenticação por
chave; o [manual oficial portable](https://github.com/openssh/openssh-portable/blob/master/sshd_config.5)
documenta esse contrato. Os módulos utilizados são os oficiais
[`pam_succeed_if`](https://man7.org/linux/man-pages/man8/pam_succeed_if.8.html) e
[`pam_deny`](https://man7.org/linux/man-pages/man8/pam_deny.8.html).

O ensaio cria overrides temporários para `/etc/pam.d/login` e `sshd` a partir
dos arquivos do fornecedor em `/usr/lib/pam.d/`. Não altera `common-*`, nem
troca autenticação por `pam_permit` ou usa `login -f`.

## Resultado nativo

[24 cenários verificados](result.json): 23 controles de admissão/recuperação e
**uma reprodução de limitação de revogação**, descrita abaixo. O resultado
`passed` significa que os resultados esperados do ensaio foram observados,
não que a proteção de toda a conta foi aprovada.

| Ensaio | Resultado |
| --- | --- |
| Baseline sem a regra, ambas as contas | Login com senha e comando SSH por chave executam e terminam normalmente |
| Login nativo com regra | Conta supervisionada recusada; comum abre shell e encerra com código0 |
| Comando SSH e SFTP | Supervisionada recusada na fase PAM account; comum executa e transfere arquivo |
| `ssh -N -L`, sem sessão de shell | Novo túnel supervisionado recusado; túnel comum transporta dados |
| SELinux permissive | Bloqueio de novas entradas permanece; conta comum preservada |
| GID primário alterado | Supervisionada continua recusada; comum preservada |
| Overrides removidos | Login, SSH, SFTP e túnel da baseline voltam a funcionar |

Foram usados `login` real em pseudoterminal com senha, cliente/servidor OpenSSH
reais e autenticação por chave. O sshd executou no domínio `sshd_t`, com escuta
somente em `127.0.0.1:22`, `UsePAM yes` conferido por `sshd -T` e chave de host
fixada no `known_hosts` do teste. As contas fictícias tinham UID31000/GID41000
e UID31001/GID41001. A primeira foi vinculada à regra de admissão; seus processos
de baseline permanecem no domínio comum. Isso isola a recusa de entrada e não
qualifica execução de aplicativos supervisionados.

O journal da execução final registra cinco recusas explícitas por configuração
PAM account. Senhas e chaves privadas foram geradas dentro da VM e eliminadas
com a fixture; não foram copiadas para o host ou versionadas. O resultado contém
somente transcrições sem senha, fingerprints públicos e contexto de execução.

A suíte Python completa passou com **249 testes**, incluindo quatro novos
contratos de geração/composição e recusa de entrada inválida.
[Proveniência e hashes dos fontes](provenance.json) foram conferidos contra os
arquivos enviados ao guest.

## Limitação reproduzida: conexões anteriores

Um túnel autenticado **antes** de instalar a regra continuou transportando dados
depois da mudança. A regra é de nova admissão; não revoga conexões já existentes.
O ensaio encerrou explicitamente esse cliente antes dos cenários seguintes.
Isso é uma lacuna conhecida, não um caso de segurança aprovado.

Antes de usar essa integração para criar/migrar/remover supervisão, o ciclo
autorizado precisa encerrar ou rejeitar conexões/processos anteriores e tratar
autenticações em andamento. A [barreira de transições](../parental-transitions/README.md)
ainda não foi integrada aos processos nativos do sshd/login. Varredura de UIDs
e ausência de sessão no logind não devem ser presumidas suficientes para
eliminar todos os processos privilegiados de uma autenticação em andamento.

## Ajustes do ensaio e restauração

O primeiro harness não reconhecia o prompt `>` do openSUSE; foi corrigido para
executar o comando e aguardar a saída normal do login. Outra rodada acionou as
penalidades padrão do OpenSSH após várias recusas do mesmo endereço, afetando
o controle positivo. A proteção **permaneceu habilitada**: a rodada final lê a
duração efetiva e espaça as tentativas negativas em seis segundos. Em produção,
contas no mesmo IP ainda compartilham a política de penalidades do servidor;
este ensaio não promete disponibilidade contra abuso desse mecanismo.

A cópia da VM precisou dos seis pacotes oficiais de SSH/dependências, instalados
do Leap16.1 pelo zypper. Eles permanecem na cópia para próximos testes. A rede
NAT usada na instalação voltou a ficar sem endereço/rota; o serviço SSH padrão,
habilitado pelo scriptlet, foi desabilitado. O servidor exclusivo do ensaio foi
parado, overrides PAM, contas, homes, chaves e arquivos temporários removidos.
O resultado confirma restauração do PAM do fornecedor, preservação das contas
originais e retorno ao SELinux permissive da baseline. A VM foi desligada.

O harness exige root, marcador `lyra.parental-identity-test=1` e disco
`lyra-admission-test`. O login usa PTY, não o getty da ISO nem um console físico.
O boot é direto de kernel. Nenhuma candidata, RPM Lyra, configuração do host ou
publicação OBS foi alterada.

## Ainda necessário

- Integrar GDM e systemd-user, depois cron, lingering, D-Bus e demais serviços
  capazes de iniciar processos para a conta. Esses caminhos não foram cobertos
  pela recusa em `login`/`sshd`.
- Resolver revogação e autenticações concorrentes antes das transações de
  identidade. Criação/migração/remoção, reutilização de IDs e troca simultânea
  de todos os identificadores continuam não suportadas.
- Exigir `UsePAM yes` no servidor efetivo e verificar variantes de configuração;
  outro servidor ou processo privilegiado pode ignorar essa pilha. Atualizações
  de pacotes/PAM, reboot e rollback da integração não foram qualificados.
- Manter autorização administrativa, recuperação e estado verificado no Vega
  dentro do contrato completo; nenhum desses fluxos foi criado nesta etapa.

O controle parental continua item1/7. #6/#102 permanecem abertas e a
[fronteira aprovada](../../parental-protection-boundary.md) continua sendo o
critério para produção.
