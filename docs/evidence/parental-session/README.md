# Serviços, áudio e portais — 26/09/2026

**Integração experimental na VM descartável. Não habilita controle parental em
produção e não encerra #6/#102.** Continua a [etapa de teclado e fontes](../parental-input/README.md).

## Implementação

Os executáveis oficiais dos demais SettingsDaemon, PipeWire e portais recebem
tipos específicos. Permanecem no domínio restrito da conta. Isso permite iniciar
os serviços, sem aprovar automaticamente seus auxiliares ou qualquer programa
com tipo genérico `bin_t`.

O portal GNOME recebe do Shell um socket Wayland por SCM_RIGHTS. A política
permite leitura/escrita nesse socket entre os domínios, sem conceder escrita na
memória executável do compositor. A regra upstream `dontaudit` para sockets
ocultava a negação e a sessão perdia sua conexão D-Bus ao ativar o portal.

### WirePlumber

WirePlumber carrega configurações e scripts Lua. O payload oficial recebe um
tipo que a conta não pode executar diretamente. Um lançador nativo, sem setuid
ou capabilities, entra em domínio próprio e aceita somente a configuração e
o perfil fixos. Rejeita argumentos, confere SELinux enforcing e contexto,
verifica árvores root sem escrita por outros, descarta o ambiente recebido e
fixa caminhos de configuração, módulos, scripts, PipeWire e SPA.

As variáveis explícitas de diretório desativam a busca nos diretórios do usuário,
conforme a fonte oficial 0.5.15 examinada e a [documentação de localização](https://pipewire.pages.freedesktop.org/wireplumber/daemon/locations.html).
O serviço mantém `NoNewPrivileges` e `MemoryDenyWriteExecute` da unidade oficial.
O domínio não recebe `execmem`, shell ou execução de dados. A identidade UID 1003
é própria da fixture; isso ainda não é um contrato de identidade de produção.

### Documentos e FUSE

O auxiliar oficial `fusermount3` entra em um domínio privado; não é usado o
domínio genérico `mount_t`. As capabilities necessárias ao auxiliar setuid
ficam nesse domínio e não na conta. A política autoriza montagem FUSE somente
no tipo dedicado aos diretórios runtime chamados `doc`. Não concede montagem
em diretórios genéricos, execução de shell ou escrita genérica em arquivos.

A fonte exata openSUSE `fuse3-3.16.2-160100.2.1` foi conferida: o auxiliar verifica
o usuário real e o acesso ao destino antes de restaurar os privilégios efetivos
para montar. `dac_read_search` permite atravessar o runtime privado nessa etapa;
`dac_override` não é concedido. A alteração SUSE renomeia a configuração para
`fuse3.conf`, sem remover as verificações. [Proveniência e assinaturas](sources.json).

O teste exporta um ELF, lê os bytes pelo caminho FUSE e exige recusa tanto de
`execve` quanto de `mmap(PROT_EXEC)`. Uma unidade temporária usa o próprio
`fusermount3 -u -z` em `ExecStopPost` para limpar uma montagem desconectada após
falha do portal, sem permitir a operação de bind sobre `/` usada pelo caminho
upstream de auto-unmount. O diagnóstico confirmou recuperação após SIGKILL, com uma única montagem
FUSE e novo ID após reinício; a rodada completa ainda precisa ser qualificada.

### Dados e recuperação

Somente os diretórios exatos de Fontconfig, estado do WirePlumber e bancos de
permissões do portal recebem escrita como dados não executáveis. A recuperação
durável preserva conteúdo, proprietário, modo, contexto e tempos dos arquivos
preexistentes; remove novos nomes e restaura diretórios originalmente ausentes.
Não segue links nem remove árvores inesperadas recursivamente. Para o cache
LocalSearch, a fixture exige que a árvore exata `~/.cache/tracker3` esteja ausente
antes do ensaio. Sua remoção usa `shutil.rmtree` resistente a ataques por symlink,
após parar a conta e conferir os pais. Dados preexistentes nesse caminho fazem
o ensaio recusar a preparação.

[SIGKILL e timeout](recovery-tests.json) passaram com alteração de arquivos
preexistentes, criação de dados novos e mudança de modo dos diretórios. A árvore
do índice foi removida e o alvo externo de um symlink foi preservado. A
[verificação final](verified-final.json) confirmou 23 RPMs íntegros, rótulos
restaurados e ausência dos lançadores, drop-ins e dados temporários. O
snapshot rejeita recuperação pendente e continua aceitando o formato da etapa
anterior. A fixture restaura todos os executáveis e drop-ins temporários.

### Seletor de arquivos GNOME

O backend GNOME delega o seletor ao Nautilus, que também faltava à VM mínima.
O pacote oficial 48.7 foi instalado com dependências obrigatórias. Seu executável
permanece no domínio da conta; auxiliares de autorun não são aprovados.
A tentativa inicial caiu após uma negação `execmem` no caminho de renderização.
Uma entrada D-Bus nativa temporária escolhe o renderizador Cairo do GTK apenas
para a conta da fixture. Outros usuários seguem o executável e ambiente normais.
Isso evita conceder memória executável à conta; desempenho gráfico e catálogo
completo de extensões ainda não estão qualificados.

A conta pode enumerar diretórios de dados pessoais, além da leitura de arquivos
já existente na política experimental. Acesso continua sujeito ao DAC. Os testes
cancelam uma janela e selecionam um arquivo fictício exato com teclado via QMP.
A presença da [janela](chooser-session23.png), sozinha, não conta como seleção
aprovada; o probe exige a resposta D-Bus e a URI exata.

### Indexação LocalSearch

O Nautilus ativou o indexador oficial, ausente das rodadas anteriores. A política
em desenvolvimento aprova exatamente CLI, indexer, control e extractor nativos,
no domínio da conta. Não aprova writeback, sandbox Python ou execução de módulos
em locais graváveis. A fonte openSUSE exata foi conferida em [sources.json](sources.json).
O cache tem tipo próprio sem execução; arquivos temporários SQLite usam um
RuntimeDirectory privado. O Landlock upstream do extrator não permite ler
`/etc/ld.so.cache`; na fixture, isso impediu descobrir a libz instalada em
`/usr/lib64/zlib-ng-compat`. O drop-in fixa esse diretório oficial em
`LD_LIBRARY_PATH`, com propriedade root e ausência de escrita por outros
verificadas. SELinux e Landlock continuam ativos. O ensaio exige encontrar
`chooser.txt` pelo conteúdo de texto no endpoint
real de busca e negar `execve` e `mmap(PROT_EXEC)` sobre um ELF no cache.
A rodada completa confirmou busca pelo conteúdo do arquivo e cache sem execução.

### Pré-condições da VM

Após um reinício, o initramfs mínimo recriou `/run/udev` como `var_run_t`.
O logind negou leitura dos registros de entrada e Mutter reportou ENODEV,
impedindo teclado/mouse. A correção na fixture foi `restorecon -RF /run/udev`,
restaurando `udev_var_run_t` da política oficial. O controlador verifica os
rótulos antes do ensaio. Nenhuma permissão para `var_run_t` foi adicionada.

## Resultado

A rodada completa **session23 passou** no [qualificador](qualify.py), que rejeita
rodadas de diagnóstico reduzido. [Resumo](summary-session23.json),
[sessão nativa](session-session23.json), [auditoria](audit-session23.json),
[preparação e controles negativos](progress-session23.json) e
[restauração](restoration-session23.json).

- Teclado Wayland, atalho aprovado e atalho de shell negado; nove chamadas dconf,
  controles AT-SPI e XWayland passaram.
- Oito modos de portal passaram, incluindo cancelamento e seleção da URI exata.
- Exportação FUSE preservou leitura dos bytes e recusou `execve` e mapa executável.
- PermissionStore preservou dados após restart. O portal de documentos recuperou
  de SIGKILL com montagem única e novo ID.
- PipeWire drenou o fluxo silencioso; WirePlumber usou ambiente fixo no domínio
  próprio e recusou execução direta do payload/argumentos do lançador.
- LocalSearch encontrou `chooser.txt` pelo texto `evidence`. Seu cache também
  recusou execução e mapa executável de ELF.
- Zero unidades persistentes em falha na amostra, serviços verificados sem
  reinícios inesperados e zero perda/limitação da auditoria. Há recusas de
  auxiliares transitórios nos logs; isso não qualifica toda a sessão.

O teste de áudio abre um fluxo PulseAudio servido pelo PipeWire, escreve e drena
19.200 bytes silenciosos. Não prova reprodução por alto-falantes físicos ou
captura de microfone. Os 221 testes Python do repositório passaram.

## Reprodução e limites

Requer a VM marcada e os builds/probes das etapas anteriores. Foram instaladas
dependências oficiais de PipeWire, WirePlumber e portal GNOME que faltavam à VM
mínima; a receita da ISO já as declara. `libpulse-devel` é dependência do probe.
Executar `python3 run.py TAG /caminho/LyraOS`. Tags iniciadas por `diag` fazem
diagnóstico reduzido; `qualify.py` rejeita esse modo como qualificação completa.
A coleta ocorre somente após o fim da recuperação. Teclas e screenshots usam
apenas o QMP da VM marcada.

O estado `active` dos daemons não prova impressão, compartilhamento, WWAN ou
outros periféricos. Auxiliares GJS de notificações/screensaver/screencast e
outros executáveis ainda têm recusas observadas. Acessibilidade integral,
aplicativos aprovados, entradas alternativas da conta, evasão, Vega, identidade
persistente, empacotamento e atualização/rollback continuam pendentes. Não
promover OBS/ISO nem habilitar o recurso com esta evidência de componentes.
