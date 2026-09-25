# XWayland e prontidão da sessão restrita — 25/09/2026

**Ensaio de componentes; não habilita proteção parental de produção.**
Continua [a etapa de callbacks](../parental-callbacks/README.md).
O cliente X11 público conseguiu consultar o desktop em enforcing; o cliente
interno conseguiu gravar e ler uma propriedade. A sessão completa continua
reprovada: houve duas inicializações do Shell na mesma captura e os serviços
GNOME ainda falham. #6/#102 permanecem abertas. Não altera receita ou RPMs.

## Falhas reproduzidas e alterações experimentais

1. O XWayland original tentava executar `/bin/sh -c ...` para compilar o
   teclado. O [patch](xkb-direct-exec.patch) acrescenta `PopenArgv` e executa
   `xkbcomp` diretamente com argumentos separados, sem busca pelo PATH.
   Preserva a API `Popen` dos outros chamadores e o comportamento dos pipes.
2. O Mutter enviava um memfd privado selado como O_RDWR. SELinux recusava
   recebê-lo porque o tipo também protege callbacks executáveis do Shell.
   O [patch](mutter-readonly-fd.patch) reabre esse descritor O_RDONLY|O_CLOEXEC,
   mantém um cache com fechamento na destruição e não retorna RW na falha.
   O caminho MAPMODE_SHARED permanece inalterado.
3. O socket X11 pertence ao Mutter antes de ser herdado. A negação de `accept`
   fazia o servidor repetir a tentativa e inundava a auditoria. A política
   temporária permite essa operação de XWayland sobre sockets do domínio Shell.
4. O launcher descartava `NOTIFY_SOCKET`, impedindo a prontidão da unidade
   Type=notify. O [launcher atualizado](trusted-shell.c) preserva somente o
   valor exato `/run/user/<uid>/systemd/notify`; quatro destinos inválidos são
   recusados. A política permite a notificação ao domínio do gerenciador do
   usuário. Esse domínio ainda é compartilhado com a conta restrita; não há
   aqui uma alegação de mediação por método ou admissão integral da conta.

[As negações de inicialização](startup-denials.json) registram as duas últimas
causas. Houve perda de auditoria nas capturas anteriores; elas demonstram as
negações observadas, mas não uma auditoria completa.

A [política do ensaio](exercise.py) usa domínios próprios para XWayland e
xkbcomp, na cadeia Shell → XWayland → compilador. A conta não pode executar
diretamente esses dois binários. Keymaps e log têm tipos não executáveis.
Não foi concedida escrita à conta ou ao XWayland na memória privada do Shell.

## Proveniência e validação

Os [fontes oficiais](source.json) tiveram assinaturas verificadas. O SRPM
XWayland 2.2 disponível possui o mesmo DISTURL do binário instalado 2.1;
isso não prova identidade entre os binários. Foram aplicados os 17 patches
SUSE do XWayland, os quatro do Mutter e o gvdb do SRPM. As duas árvores
preparadas foram reproduzidas byte a byte antes dos ensaios.

- Oito [testes da implementação real de Popen/Pclose](popen-tests.json):
  metacaracteres literais, pipes de leitura/escrita, executável ausente, falha
  do filho, parâmetros inválidos, API antiga e ausência de busca pelo PATH.
- [Testes do arquivo upstream do Mutter](mutter-tests.json): falha/retry,
  conteúdo, flags e seals, COW privado, compatibilidade compartilhada,
  mil aberturas sem vazamento, destruição e arquivo vazio. Também passou
  o teste upstream `src/tests/anonymous-file.c`.
- Três [provas reais de SCM_RIGHTS](descriptors.json): RW recusado com e sem
  selo; RO recebido/lido, escrita EBADF e mapeamento executável EACCES.
  São programas instrumentados temporários, não launchers distribuíveis.
- [Controles nativos da rodada final](native-controls.json): 14 verificações
  de execução/conta comum, dez falhas de configuração e as três provas de
  descritores passaram. A [sessão](session.json) registra os três comandos
  X11 com retorno zero, contextos dos processos, unidades e limites.
- A [auditoria final](audit.json) registrou delta zero no contador de eventos
  perdidos e não atingiu os limites da coleta. Continua contendo negações
  esperadas dos testes e bloqueios reais ainda não resolvidos.
- [Builds completos](builds.json) de diagnóstico de XWayland e Mutter na VM.
  XWayland apresentou avisos upstream de cast e combinação crypto3/crypto56;
  não são RPMs qualificados. O RPATH do Mutter foi ajustado ao diretório oficial.

O sucesso do cliente X11 não aprova estabilidade da sessão: XSettings ficou
em auto-restart, outros SettingsDaemon falharam e persistem negações para
registro GDM, AccountsService, Polkit, dconf e permission-store. Também faltam
aplicativos reais, acessibilidade, clipboard, compartilhamento de tela,
aceleração gráfica, buffers compartilhados e proteção de todas as entradas da
conta. O kernel reporta uma permissão `io_uring` desconhecida pela política;
a compatibilidade kernel/política permanece pendente.

## Recuperação do ensaio

Uma versão anterior excedeu o timeout enquanto `ausearch` percorria registros
acumulados. O snapshot em memória foi perdido. A VM foi recuperada com hashes
conferidos contra o banco RPM; esse ensaio interrompido não foi aprovado.

[fixture_recovery.py](fixture_recovery.py) agora grava bytes, hashes, donos,
modos, rótulos e timestamps em backup persistente antes das alterações.
Recusa novo ensaio enquanto há recuperação pendente. `ExecStopPost` executa
uma recuperação independente, inclusive se o processo principal morrer.
[Os testes](recovery-tests.json) provocaram SIGKILL e RuntimeMaxSec e
verificaram a restauração real do binário e a remoção do arquivo criado.
Após desligamento abrupto da VM, executar a recuperação antes de novo ensaio;
o script não instala uma unidade de recuperação no boot.

A [coleta](audit_capture.py) agrega registros com leitura limitada, informa
truncamento e compara o contador de perdas. O limite de backlog cresce
somente durante o ensaio e é restaurado. Os subprocessos do coletor têm
limite de tempo e encerramento do grupo; os journals são limitados em tamanho.

A [verificação final](restored.json) passou: nove pacotes com `rpm -V` limpo,
fixtures e módulo temporário ausentes, GDM/gerenciador do usuário/auditd
inativos e backlog original. SELinux volta ao modo permissivo da VM fora dos
ensaios. As dependências de build permanecem instaladas; não se afirma que
todo o inventário inicial foi restaurado.

## Reprodução

Extrair os SRPMs verificados; usar `prepare-source.py` e `prepare-mutter.py`
com `--sources DIRETORIO_EXTRAIDO --output DIRETORIO_NOVO`. Executar
`test-popen.py ARVORE_XWAYLAND` e `test-mutter.py ARVORE_MUTTER`.

O ensaio gráfico exige a VM marcada `lyra.parental-selinux-test=1` e os
pré-requisitos PAM/SELinux/GDM das etapas anteriores. Copiar para `/root`:

- `trusted-shell.c`, `fixture_recovery.py`, `audit_capture.py` e `test-recovery.py`;
- `config-faults.py` como `trusted-shell-config-faults.py`;
- `fd-probe.c` como `xwayland-fd-probe.c`;
- `session.py` como `restricted-xwayland-session.py`;
- `exercise.py` como `xwayland-exercise.py`.

Os scripts de build esperam `/root/xwayland-patched.tar.gz` e
`/root/mutter-patched.tar.gz`, com diretórios `xwayland-patched` e
`mutter-patched`. Instalar na VM as dependências dos specs, `libxcvt`,
`python3-docutils`, `Mesa-libGLESv3-devel` e `chrpath`.

Executar `python3 /root/test-recovery.py` antes do ensaio. Usar unidade
transitória independente do timeout do canal de controle:

```sh
systemd-run --unit=lyra-xwayland-test \
  -p RuntimeMaxSec=240 -p TimeoutStopSec=180 \
  -p StandardOutput=append:/root/xwayland-result.json \
  -p StandardError=append:/root/xwayland-stderr.log \
  '-p' 'ExecStopPost=/usr/bin/python3 /root/fixture_recovery.py' \
  /usr/bin/python3 /root/xwayland-exercise.py
```

Esperar a unidade terminar e conferir que não existe
`/root/lyra-xwayland-recovery/active.json`; executar `verify-final.py`.
Logs ficam em `/root/trusted-shell-{session,audit,config-faults}.json`.
Qualquer código zero do ensaio significa coleta/restauração concluída;
avaliar os resultados de clientes, unidades e auditoria separadamente.
