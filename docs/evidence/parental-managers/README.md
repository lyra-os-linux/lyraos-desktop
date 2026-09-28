# Admissão nativa no systemd-user e no GDM — 28/09/2026

A barreira da [etapa de transições](../parental-transitions/README.md) foi
ensaiada nas pilhas reais `systemd-user` e `gdm-autologin` da VM descartável.
**33 cenários passaram: 19 no systemd e 14 no GDM.** Não há ativação na receita,
pacote publicado ou proteção integral da conta qualificada. #6/#102 continuam
abertas.

## O que mudou

Os harnesses compõem a pilha PAM vendor com o seletor de identidade e o guard
persistente já existentes, sem alterar autenticação ou `common-*`. A conta
supervisionada precisa de identidade exata, estado ativo e SELinux enforcing.
A conta comum pula o módulo experimental, inclusive quando ele está ausente.
O módulo C e o controlador de transições não precisaram de novas permissões
SELinux para ler ou travar o estado nestes processos nativos.

No systemd, o processo nativo `(sd-pam)` conserva o descritor da trava depois
do exec do gerenciador. O reload definido pelo vendor, que reexecuta o
gerenciador, também conservou a trava. No GDM, tanto o worker de root quanto
o `(sd-pam)` da conta conservaram descritores do mesmo arquivo; os PIDs e
descritores foram conferidos por dispositivo/inode em `/proc`.

Uma tentativa de transição com a sessão ativa persiste `blocked` e retorna
ocupado. A sessão existente continua viva: **bloquear admissão não revoga
sessões**. Encerrar os gerenciadores libera as travas, mas não reabre a conta.
Uma operação explícita de recuperação verifica identidade e ausência de
processos antes de publicar `active` novamente.

## Resultados

| Verificação | systemd-user | GDM autologin |
| --- | --- | --- |
| Conta supervisionada inicia no contexto restrito | Passou | Passou, sessão ELF mínima |
| Sessão ativa impede a transição e conserva o processo | Passou | Passou |
| Encerramento libera as travas, mantendo bloqueio persistente | Passou | Passou |
| Recuperação explícita permite nova entrada | Passou | Passou |
| Estado ausente ou módulo PAM ausente | Recusa supervisionada; comum preservada | Mesmo resultado |
| SELinux permissive | Recusa supervisionada; comum preservada | Mesmo resultado |
| Estado corrompido | Recusa supervisionada; comum preservada | Não repetido nesta entrada |
| Reexec nativo do gerenciador | Trava preservada | Não se aplica ao ensaio |

[Resultado systemd](systemd-result.json), [resultado GDM](gdm-result.json) e
[proveniência](provenance.json). A recusa systemd exige `ExecMainStatus=224`
(falha PAM); a do GDM exige mensagem do guard ou falha de carga do módulo
na conversa `gdm-autologin`, além de ausência do executável de sessão. Os
controles positivos antes/depois evitam confundir uma sessão quebrada com
negação bem-sucedida. A suíte Python do repositório passou com **249 testes**.

## Condições do ensaio

- Base Leap16.1, kernel `6.12.0-160100.4-default`, systemd
  `257.13-160100.2.5`, GDM `48.0-160100.2.1`, PAM
  `1.7.2+git12-160100.2.1`; versões/DISTURLs registrados na proveniência.
- Disco descartável `lyra-admission-test`, marcador de kernel
  `lyra.parental-identity-test=1`, boot direto de kernel; nenhuma ISO ou
  instalação UEFI foi qualificada aqui.
- Contas de teste existentes: `parentaltest` UID1003/GID1004 e `ordinaryuser`
  UID1002/GID1003. Nenhuma conta real ou senha do mantenedor foi utilizada.
- O GDM usou temporariamente o **worker de diagnóstico com o patch dos hooks
  de root**, proveniente da [etapa GDM](../parental-gdm/README.md). Não é o
  worker oficial sem alterações nem um RPM de produção reconstruído.
- [session.c](session.c) apenas permanece viva. A fixture substitui
  temporariamente os dois arquivos de sessão GNOME para selecionar esse ELF.
  Não testa compositor, aplicativos, portais ou autenticação por senha.
- [launcher.cil](launcher.cil) permite a execução/verificação dos executáveis
  da fixture, uso do terminal e comunicação necessária ao launcher GDM. Reusa
  permissões de comunicação do diagnóstico anterior. Não permite escrita no
  estado da barreira, execução genérica de `bin_t` ou shell.

O primeiro diagnóstico gráfico falhou na verificação `TryExec` e, depois,
no acesso ao terminal herdado. O harness foi ajustado com permissões explícitas
para a fixture; a matriz final completa passou. Ajustes do harness systemd
trataram unidade já descarregada ao chamar `reset-failed` e o byte NUL retornado
pelo kernel no contexto SELinux. Essas primeiras rodadas não contam como
aprovação; os resultados vinculados são das rodadas finais, com limpeza.

Os harnesses restauraram PAM, configuração GDM, entradas de sessão, arquivos
AccountsService, rótulo do launcher e bytes oficiais do worker. Removeram módulo
PAM, estado, executável e módulo CIL temporários. GDM e gerenciadores estão
parados; a VM voltou a permissive. O hash oficial do worker restaurado é
`40e1387811b74adcde44b8a34f03db1d032190867e1c5f4092bb9aa1362fdab8`.

Para reproduzir, preparar a mesma política experimental anterior e o worker
documentado, copiar `../parental-transitions/{transition.py,pam-guard.c}`
para `/root/{transition.py,transition-pam-guard.c}` e
`../parental-identity/bindings.py` para `/root/identity-bindings.py`. Copiar
`session.c` e `launcher.cil` para `/root/manager-session.c` e
`/root/lyra-manager-launcher.cil`. Executar os dois harnesses como root
exclusivamente nessa VM, um por vez. Eles recusam disco/marcador incorretos,
sessões ativas e colisões com seus arquivos temporários.

## O que continua pendente

O teste do GDM é de **autologin**, não da conversa `gdm-password`, desbloqueio
ou autenticação em andamento. Gerenciador systemd ativo não significa sessão
GNOME funcional: a política experimental ainda produz negações em helpers e
autostart; os resultados registram essas mensagens sem considerá-las resolvidas.

Ainda faltam integração/qualificação de cron, lingering, D-Bus e serviços
`User=`, revogação de conexões e processos anteriores, cadastro/migração/remoção
com autorização administrativa, reutilização de IDs, UI verificada e
update/rollback. Handles anteriores à instalação da pilha podem manter a
configuração antiga. `/proc` sozinho não impede produtores externos de criar
novos processos depois da varredura.

As novas evidências não autorizam hot-enrollment ou retirada de supervisão,
não resolvem o túnel SSH anterior à política e não permitem anunciar controle
parental ativo no produto. O próximo passo é qualificar a conversa GDM com
senha e fechar as entradas e a revogação restantes antes do ciclo de contas.
