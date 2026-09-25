# Teclado, atalhos e dados de fontes — 25/09/2026

**Implementação experimental em VM. Não habilita controle parental em produção.**
Continua [acessibilidade](../parental-a11y/README.md); #6/#102 permanecem abertas.

## Implementação

A política temporária permite os executáveis oficiais `gsd-keyboard` e
`gsd-media-keys` em um tipo específico, mantendo ambos no domínio restrito.
O transporte D-Bus para localed/hostnamed e a leitura de eventos de dispositivo
permitem descobrir layout, tipo de máquina e hotplug; cada serviço continua
responsável por autorizar métodos privilegiados.

O auxiliar oficial `gio-launch-desktop` recebe outro tipo. Quando chamado
pela conta, permanece restrito. Quando chamado pelo domínio do Shell, uma
transição obrigatória o coloca no domínio da conta antes de executar o alvo.
O programa oficial faz `execvp`; aprová-lo não aprova implicitamente seu destino.
Um probe temporário no domínio do Shell verifica destino autorizado e recusa de
shell, Python, cópia, carregador ELF e memória executável anônima no receptor.
O probe é instrumentação removida após o ensaio, não lançador de produto.

### Compatibilidade Wayland

Apenas aprovar os serviços reproduziu quedas com `Error reading events from
display`. Clientes anteriores a `wl_keyboard` versão 7 recebem uma cópia
O_RDWR do mapa de teclado. Esse memfd herdava o mesmo tipo da memória executável
do Shell, cuja escrita pela conta é corretamente proibida.

O [patch incremental do Mutter](mutter-shared-data.patch), aplicado após os
patches da etapa XWayland, usa o caminho upstream de arquivo temporário no
runtime para cópias `MAPMODE_SHARED`. O arquivo é criado com nome exclusivo,
CLOEXEC e desvinculado imediatamente; na VM recebe `user_tmp_t`, tipo de dados
não executável. A cópia é privada de cada cliente. Buffers selados de leitura
privada mantêm o comportamento da etapa anterior. Não foi concedida escrita
à conta em `lyra_parental_shell_memory_t`.

O teste compila o código real e verifica escrita compartilhada sem alteração
do original, fechamento de descritores, ausência de vazamentos em 1000 aberturas,
falha sem runtime, arquivo já desvinculado e CLOEXEC. O teste upstream passa
com e sem memfd. Trata-se de build da biblioteca, não de um RPM qualificado.

### Cache de fontes

Somente `~/.cache/fontconfig` e seus arquivos recebem o tipo dedicado
`lyra_parental_fontcache_t`. São permitidos dados, hardlinks temporários e
renomeação atômica, conforme o Fontconfig oficial. Não há execução desse tipo
nem escrita genérica em todo o cache/home ou no cache do sistema.

Um probe força a geração de cache de fontes reais. Outro grava ELF nesse
mesmo diretório e confirma recusa de execução e de mapeamento executável.
O snapshot conserva os arquivos preexistentes, conteúdo, proprietário, modos,
contextos e tempos; a recuperação remove somente nomes novos. Não segue links
nem remove diretórios recursivamente. Falha por SIGKILL e timeout também exercita
a restauração de cache alterado. Diretórios inesperados interrompem a recuperação
para diagnóstico, sem apagar conteúdo desconhecido.

## Qualificação

A [rodada input6](summary.json) passou: Keyboard e MediaKeys ativos, sem
reinícios; atalho aprovado executado no domínio restrito, shell negado com AVC,
digitação `a` recebida pelo GTK Wayland e cache real com 22 fontes gerado.
As seis provas de transição do Shell, nove chamadas dconf, AT-SPI 0/1/0,
15 controles de execução/conta comum, dez falhas de configuração e quatro provas
de descritores passaram. Auditoria sem perdas adicionais ou corte. Os 221 testes
Python do repositório passaram. A recuperação verificou quinze RPMs limpos,
contextos originais e ausência de fixtures. Restam 14 unidades de usuário com
falha (12 SettingsDaemon, portal e permission-store); a sessão integral continua
pendente. SIGKILL e timeout passaram na versão final da recuperação.
O harness usa teclas físicas via QMP somente na VM marcada. O teste configura
Super+Shift+F9 primeiro para um programa aprovado e depois para bash. O positivo
precisa produzir seu marcador; o negativo precisa de marcador ausente **e** AVC
de execução recusada. Outra janela GTK3 nativa Wayland recebe a tecla `a`.
O driver sai do Overview antes de digitar; a mensagem de prontidão, sozinha,
não conta como entrega de teclado bem-sucedida.

A VM mínima não tinha layout X11 definido. O ensaio cria temporariamente
`00-keyboard.conf` com `us`, confere a preferência inicializada pelo daemon e
remove a configuração. A fonte SUSE altera o fallback upstream quando o layout
está ausente; essa diferença está em `gnome-settings-daemon-initial-keyboard.patch`.
Não é uma decisão de impor teclado americano ao produto.

Os testes anteriores de dconf, AT-SPI, X11, registro GDM, Polkit, execução,
configuração inválida e descritores são repetidos. Serviços de áudio e o backend
portal GNOME ainda não estavam instalados nesta VM mínima: não confundir essa
limitação da fixture com a receita da ISO, que os declara.

## Reprodução e limites

Reusar a VM marcada e os pré-requisitos de XWayland/dconf/a11y. Aplicar
`mutter-shared-data.patch` em `/root/mutter-patched` depois dos patches anteriores;
`build-mutter.py` compila o mesmo alvo e ajusta RPATH. Copiar os probes C desta
etapa para `/root`, a recuperação, `exercise.py` como `xwayland-exercise.py` e
`session.py` como `restricted-xwayland-session.py`. Usar unidade transitória com
RuntimeMaxSec=300, TimeoutStopSec=180 e ExecStopPost da recuperação. O driver local pode ser executado como `python3 run.py TAG /caminho/LyraOS`,
reusando `analysis/2026-09-25/parental-gdm/vm.py` e `control.py`; chama somente
os sockets da VM descartável. `qualify.py TAG` valida os artefatos brutos antes
de gerar o resumo. A coleta
não deve ser feita antes de desaparecer `active.json` da recuperação.

Ainda faltam os demais serviços GNOME, portais, entradas alternativas da conta,
catálogo de aplicativos aprovados, evasão, integração com Vega e recuperação de
produção. Contextos persistentes, migração, RPM/OBS e atualização/rollback não
são resolvidos pela rotulagem temporária. Não concluir o item parental inteiro
nem declarar a ISO qualificada com esta evidência de componentes.
