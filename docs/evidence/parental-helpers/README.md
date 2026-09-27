# Auxiliares GNOME — 27/09/2026

**Integração experimental na VM descartável. Não habilita controle parental
em produção nem encerra #6/#102.** Continua a etapa de
[serviços, áudio e portais](../parental-session/README.md).

## Fronteira dos auxiliares

Notificações, ScreenSaver e Screencast usam GJS. Cada serviço recebe uma entrada
nativa fixa e um domínio SELinux próprio. A entrada confere UID de teste,
enforcing, contexto e `AT_SECURE`; rejeita argumentos, verifica os recursos e
ancestrais de root sem escrita por outros, limpa o ambiente e fixa os caminhos.
O executável real `gjs-console` recebe um tipo que a conta não pode executar.
O symlink oficial `gjs` permanece intacto. Não há setuid ou capabilities nas
entradas.

O motor JavaScript exige `execmem` mesmo com `GJS_DISABLE_JIT=1`; libffi também
usa um memfd executável para callbacks. Essas permissões ficam nos domínios
privados. A conta não recebe `execmem`, execução/escrita nos tipos privados ou
`ptrace` dos auxiliares. A evidência deve combinar consultas da política com
atributos, um controle positivo da consulta e recusas nativas de escrita e
mapeamento executável. Os arquivos dessas recusas são fixtures com UID/mode
compatíveis, não uma simulação completa de passagem de descritores.

GTK envia ao compositor um descritor O_RDWR de cursor Wayland. O Shell confiável
pode escrever no tipo privado de memória do gravador para recebê-lo. O gravador
também recebe o memfd de captura do compositor; essa escrita fica entre os
domínios confiáveis. A conta continua sem essas permissões. Shell, gravador e
PipeWire pertencem à mesma fronteira de confiança para esses buffers.
Não demonstra isolamento mútuo entre esses componentes.

## Gravação e base da VM

A VM antiga não tinha `gstreamer-plugins-good`, já previsto na receita Desktop.
Foram instalados o pacote oficial e dez dependências obrigatórias, com verificação
das assinaturas. O registro está em `vm-prerequisites.json`. Isso é preparação
da VM, não mudança na receita ou instalação no host.

A combinação GJS 1.84.2 / GNOME Shell 48.8 / GStreamer 1.28.5 reproduziu a falha
`Gst.init_check(null)` também fora do domínio restrito. O ensaio reutiliza os dois
arquivos do [launcher de compatibilidade já existente](../../gnome-screencast.md).
Os recursos oficiais GNOME não são alterados na versão final da fixture.

O registro de plugins e caches fica em um diretório privado, não executável,
removido com o runtime. A conta não pode alterar o registro. Plugins vêm do
diretório oficial; a descoberta ocorre no processo, sem aprovar um scanner
executável genérico. `ORC_CODE=backup` escolhe o caminho sem geração de código
[previsto pelo Orc](https://raw.githubusercontent.com/GStreamer/orc/main/orc/orccompiler.c).
O PipeWire pode consultar o link `/proc/<pid>/root` do gravador para verificar a
identidade do cliente. Metadados temporários do gravador continuam dados sem
permissão de execução.

## PipeWire

O servidor PipeWire e o servidor Pulse compatível passam a usar uma entrada
nativa fixa e domínio privado. O perfil anterior mantinha ambos no domínio da
conta; ao iniciar a gravação, a recepção dos buffers do Shell pedia escrita na
memória privada do compositor. Essa permissão fica agora no servidor confiável,
sem ser estendida aos aplicativos da conta.

As entradas fixam a configuração oficial, módulos e plugins SPA, rejeitam
argumentos e limpam o ambiente. A ativação por socket preserva apenas PID e
quantidade de descritores conferidos por `getsockname` contra os paths esperados.
As restrições oficiais `NoNewPrivileges` e `MemoryDenyWriteExecute` permanecem.
O servidor não recebe `execmem` nem execução da memória do compositor/gravador.
A comunicação PipeWire e a API upstream continuam precisando de ensaios de abuso
antes de qualquer afirmação de proteção integral.

## Testes e limites

A qualificação exige criar uma notificação, negar a outro cliente o fechamento
do ID e permitir ao dono fechá-la; consultar e ativar o bloqueio de tela;
gravar três segundos; decodificar o arquivo até EOS e conferir duração. A
verificação de decodificação é um cliente da fixture fora da conta restrita,
não uma aprovação de GJS genérico para a conta. A imagem QMP confirma a tela de
bloqueio; não qualifica senha, autenticação ou uma política parental de horários.
A chamada nativa de gravação não cobre o fluxo Print Screen, seleção de área,
gravação prolongada ou múltiplos monitores.

Os testes anteriores de teclado, atalhos, dconf, AT-SPI, XWayland, áudio,
WirePlumber, busca e portais continuam obrigatórios. O qualificador recusa
rodadas de diagnóstico abreviado.

Os auxiliares ainda leem dados amplamente conforme a política experimental.
A interface upstream de Screencast aceita opções de pipeline e caminhos de
saída: o launcher fixo não transforma essa API em uma lista fechada de operações.
Abuso dessa interface, catálogo de aplicativos, acessibilidade integral,
entradas alternativas de sessão e integração Vega seguem pendentes.

Os logs da unidade de teste ficam em `/var/log/lyra-parental-fixture`, com
rótulo oficial e diretório de root. Logs em `/root` impediam o systemd de
iniciar `ExecStopPost` quando a sessão era interrompida em enforcing.

A recuperação restaura os arquivos e rótulos anteriores e remove entradas,
drop-ins e dados gerados. O perfil UID 1003 e os paths fixos pertencem apenas à
fixture marcada. Não constituem empacotamento nem identidade de produção.

## Reprodução

Requer a VM descartável marcada e os builds/probes das etapas anteriores.
As versões instaladas estão em `runtime-packages.json`; `sources.json` registra
as fontes conferidas na etapa anterior, não a fonte exata de todos os auxiliares.
Os diagnósticos que justificam as permissões estão em `causes.json`.

Após reiniciar essa VM mínima, conferir os rótulos oficiais de `/run/udev`
(`restorecon -RF /run/udev` se necessário) e parar `auditd` antes da preparação.
GDM e a conta de teste também devem estar inativos; a fixture recusa um estado
incompatível. Essas pré-condições pertencem ao ensaio, não ao sistema instalado.

```sh
python3 run.py helpers2 /caminho/LyraOS
python3 qualify.py helpers2
```

`run.py` depende do controlador local em
`analysis/2026-09-25/parental-gdm/`; teclas e imagens são enviadas somente pelo
QMP da VM. Tags `diag*` e `fault*` usam diagnóstico reduzido, rejeitado pelo
qualificador completo. A coleta espera a recuperação terminar.

O probe de bloqueio aguarda `GetActive=true`, pois a resposta de `Lock` pode
preceder o término da animação. Uma resposta imediata ainda inativa não é
aceita como sucesso; há prazo finito e falha se o estado não for confirmado.

Para os ensaios de recuperação, `faultKill*` envia SIGKILL ao processo principal
após confirmar enforcing. `faultTimeout*` suspende os processos da unidade no
mesmo ponto e aguarda o `RuntimeMaxSec=300` configurado ao iniciar o serviço.
É o systemd que encerra a unidade e executa `ExecStopPost`. O qualificador de
recuperação exige os resultados `signal` e `timeout`, restauração de 101 arquivos,
ausência de recuperação pendente e stderr vazio. Não basta o comando de injeção
retornar sucesso.

## Resultado funcional

A rodada completa **helpers2 passou** no [qualificador](qualify.py).
[Resumo](summary-helpers2.json), [sessão nativa](session-helpers2.json),
[auditoria](audit-helpers2.json), [preparação e limites](progress-helpers2.json)
e [restauração](restoration-helpers2.json).

- Notificação criada, fechamento por cliente alheio recusado e fechamento pelo
  dono aceito; ScreenSaver consultado e bloqueio confirmado por estado D-Bus
  e [imagem QMP](locked-helpers2.png).
- Gravação produzida pela API nativa e decodificada até EOS, com duração verificada.
  Os três auxiliares usaram os domínios privados e o ambiente fixado.
- Escrita e mapeamento executável das três memórias privadas recusados à conta;
  escrita no registro de plugins também recusada. As 29 consultas de limites
  da política passaram, com controle positivo da consulta.
- PipeWire/Pulse ativos nos domínios privados com configuração fixa e hardening
  preservado; payloads diretos e argumentos adicionais dos lançadores recusados.
- Regressões anteriores de teclado, atalhos, dconf, AT-SPI, XWayland, áudio,
  WirePlumber, busca, portais e recuperação do portal de documentos passaram.
- Zero unidades persistentes em falha na amostra e zero perda/limitação de
  auditoria. Os AVCs restantes não significam qualificação integral da sessão.

A [verificação final](verified-final.json) confirmou 25 RPMs íntegros, rótulos
restaurados e ausência da política experimental, entradas, drop-ins e dados
temporários. O módulo base da fixture permanece. GDM, conta de teste e auditd
ficaram inativos, com SELinux permissive fora do ensaio.

## Recuperação qualificada

As rodadas `faultKill2` e `faultTimeout3` passaram no
[qualificador de recuperação](qualify-recovery.py): ambas confirmaram enforcing
antes da falha, encerraram com o motivo esperado e restauraram 101 arquivos,
sem recuperação pendente nem stderr. [Resultados completos](recovery-tests.json).

```sh
python3 run.py faultKill2 /caminho/LyraOS
python3 run.py faultTimeout3 /caminho/LyraOS
python3 qualify-recovery.py faultKill2 faultTimeout3
```

Usar tags novas ao repetir os ensaios na mesma VM, para não reutilizar unidades
transitórias em falha nem concatenar logs de rodadas diferentes. Esses resultados
substituem a tentativa anterior de alterar `RuntimeMaxSec` durante a execução,
recusada pelo systemd da VM; aquela tentativa não conta como timeout validado.
