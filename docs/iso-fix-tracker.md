# Correções da máquina física que precisam chegar à ISO

Decisão do mantenedor em 15/09/2026: todo bug encontrado ou corrigido na estação
física deve ser acompanhado na próxima ISO. A validação em uma máquina é evidência
de um cenário; não qualifica outros modelos, GPUs ou firmwares.

Este registro complementa a auditoria [#78](https://github.com/lyra-os-linux/lyraos-desktop/issues/78)
e a [matriz de hardware #69](https://github.com/lyra-os-linux/lyraos-desktop/issues/69).
Registro inicial: reparos de boot de 15/09 e integração NVIDIA relacionada.
Não é uma afirmação de que todo o histórico anterior já foi reconciliado.

## Regra para cada correção

Registrar sintoma e causa, componente responsável, alcance entre hardwares,
fonte/RPM/receita alterados, evidência local, riscos e reversão. Manter separados
os estados **corrigido localmente**, **incorporado nas fontes**, **publicado em
RPM quando aplicável**, **incluído na ISO exata** e **validado na candidata**.
Só concluir o item da ISO após o teste da candidata identificada por checksum.

Quando a causa for específica da estação, registrar isso e verificar que a ISO
limpa não a reproduz. Não copiar diretórios pessoais, resíduos de prévia,
blacklists, UUIDs de discos, chaves privadas, parâmetros de firmware ou drivers
de um modelo para toda a distribuição. A correção deve usar detecção de
capacidade/hardware quando necessária, preservar o comportamento nos demais
equipamentos e oferecer reversão.

## Lote atual

**Decisão de 16/09/2026:** uma única ISO Desktop GNOME, sem NVIDIA pré-instalada;
instalação opcional pelo Vega GTK. Isso substitui o plano de duas variantes.
O Server com llama.cpp + NVIDIA conserva seu planejamento separado.

**Ensaio NVIDIA de 16/09:** instalação real dos dez RPMs assinados, scripts e
verificação de integridade passaram em uma VM Leap/Btrfs limpa. PackageKit/zypp
recusou atualização isolada incompatível para 615, mantendo o conjunto 610.
Dois boots de recuperação Snapper restauraram arquivos/configuração e depois
o inventário anterior à instalação, preservando dados em `/var`. Vega recusou
instalação sem GPU. VM, disco e raízes temporárias foram apagados; estação
inalterada. [Evidência e limites](evidence/nvidia-vm-20260916.json).
Esse ensaio usa boot direto de kernel/initrd: não qualifica GRUB/Secure Boot,
hardware NVIDIA, interface GNOME Software nem o caminho positivo completo do
instalador Vega ou uma ISO exata. Esses gates continuam pendentes.

As alterações abaixo integram o lote `fix/boot-startup-integration` nas fontes
do Desktop. A verificação local não substitui a publicação dos artefatos nem
a qualificação da imagem: nenhuma candidata nova foi construída ou homologada
nesta etapa.

| ID | Bug e correção local | Destino na ISO e alcance | Validação ainda necessária |
| --- | --- | --- | --- |
| BOOT-01 | `regulatory.db` ausente; RPM oficial `wireless-regdb` instalado e recarregado, conexão mantida | Dependência explícita na receita, independente do fornecedor do Wi-Fi; sem forçar país | Live e instalado com Intel e outro fornecedor de Wi-Fi, além de Ethernet e VM sem Wi-Fi; carregamento da assinatura, conexão e retorno de suspensão |
| BOOT-02 | `linuwu_sense` órfão/sem assinatura, `acer_wmi` bloqueado; restaurado driver Acer assinado do kernel | Saneamento **apenas local**; a receita já usa módulos do kernel e não deve instalar Linuwu, forçar Acer ou distribuir esta blacklist | Confirmar ausência do resíduo na ISO; testar Acer e pelo menos um fabricante diferente; hotkeys/rfkill, suspensão e Secure Boot; não prometer controles extras Linuwu/DAMX |
| BOOT-03 | Cinco prévias antigas mantinham UUID Sheliak incompleto; retiradas com backup | Resíduo **apenas local**, fora dos RPMs atuais; não distribuir remoção ampla de diretórios de extensões | Conta nova, atualização de instalação anterior e retorno de perfil; seis componentes ativos, sem depender de arquivos pessoais da estação |
| BOOT-04 | Screencast GJS/GStreamer falhava no GDM; launcher compatível e override no diretório do greeter | Receita GNOME comum, reutilizando o mesmo launcher; nenhuma seleção por GPU | Ativação em D-Bus isolado passou; testar login real, bloqueio/desbloqueio e gravação/reprodução na candidata com Intel, AMD, NVIDIA suportada e VM |
| BOOT-05 | Plymouth tinha `${localstatedir}` não expandido; PID e condição ajustados para `/run/plymouth/pid` | Overrides na receita e inclusão no initrd instalado; preservar exclusão de Plymouth/DRM do initrd live genérico | Boot e desligamento da candidata, splash/tema, passagem ao GDM e entrada de senha se houver volume criptografado suportado; reavaliar override ao mudar pacote upstream |
| BOOT-06 | Exceção do Xwayland ao encerrar o greeter; reproduzida também em VM oficial Leap sem NVIDIA/extensões Lyra | **Pendente upstream**; sinais observados sustentam disputa na ordem de encerramento GDM/Mutter; nenhum workaround aplicado | Seis ciclos login/bloqueio/desbloqueio/logout em VMs passaram, sem reinícios do Shell pessoal. Revisar [reprodução e limites](gdm-greeter-reproduction.md), acompanhar correção upstream e validar candidata/mais GPUs |
| BOOT-07 | Erros ACPI/firmware e aviso de TDX indisponível | **Específico de firmware/capacidade**, sem correção global aplicada; não desabilitar ACPI nem criar requisito de TDX | Comparar versões de firmware e outros fabricantes; energia, suspensão, dispositivos e requisitos mínimos; separar avisos sem impacto de falhas funcionais |
| BOOT-08 | Plymouth usa `KillMode=none` depreciado | **Pendente upstream/qualificação**, mantida a política de término existente | Ensaiar boot, cancelamento, troca de root, passagem ao GDM e desligamento antes de alterar semântica para eliminar o aviso |
| BOOT-09a | Instalador apagava `custom.conf`, deixando o GDM sem backend; arquivo restaurado localmente e limpeza do instalador corrigida | Fontes do instalador e `lyra-system-smoke`; geral para GNOME, independente da GPU | Regressões, leitor GDM isolado e reboot local de 15/09 às 16:18 passaram; consumir o instalador corrigido na nova ISO e validar instalação/primeiro login com conta nova |
| BOOT-09b | Ativação `systemd1` falha no bus privado do greeter | Separação é deliberada no GDM 48; nenhuma alteração de PAM, bus ou lifecycle aplicada | Acompanhar upstream; não classificar a mensagem isolada como falha do gerenciador pessoal nem forçar integração que o GDM evita |
| NVIDIA-01 | Conjunto oficial NVIDIA 610.57.04 + KMP SUSE assinado funciona na GTX 1650 desta estação; integração `lyra-nvidia` instalada e verificada em 16/09, com rejeição de misturas incompatíveis em ensaio isolado | Metapacote publicado em OBS; qualificação da instalação opcional via Vega pendente. ISO GNOME única sem NVIDIA pré-instalada, por decisão de 16/09 | Matriz das GPUs realmente suportadas, sistemas híbridos e dedicados, Secure Boot, novo kernel, atualização/rollback, monitor externo e suspensão; não extrapolar GTX 1650 para todas as placas |
| NVIDIA-02 | Vega não reconhecia a pilha oficial G07; o diagnóstico antigo de verificação podia alterar a política de suspensão. O ensaio instalado também revelou módulos ocultos pelo isolamento das consultas | Vega GTK5.1.39 + vegad5.1.28 corrigidos e instalados localmente; fontes/RPMs ainda sem publicação. Consulta permanece no UID do usuário, sem capabilities, sistema somente leitura e syscalls de módulos bloqueadas | Testar o card na ISO GNOME única, antes/depois da instalação opcional, abertura/refresh sem senha, cancelamento/negação, instalação real e recuperação; não extrapolar dry-run para migração real |

## NVIDIA-03 — CLI/Web e recuperação Server/ext4, 16/09

Vega CLI5.1.23 e Web5.1.23 passam a oferecer diagnóstico público e instalação
NVIDIA com confirmação administrativa, usando vegad5.1.29. Os três RPMs foram
qualificados e instalados localmente; Web permanece desativado. NVIDIA610,
kernel e sessão GNOME da estação preservados. Fontes/RPMs ainda não publicados.
O GNOME continua com Snapper; recuperação Restic offline foi qualificada em
VM apenas para o layout Server/ext4 simples. A receita Server inclui Restic
no live e no instalado. Não adicionar Web como serviço exposto no Desktop.

[Evidência](evidence/nvidia-clients-server-20260916.json): instalação real dos
RPMs, recuperação e interrupção/retomada, dados de serviços/home/ESP preservados,
clientes nos três idiomas, autorização PAM/Polkit com UID real e RPMs verificados.
A próxima ISO deve consumir o vegad novo e testar consultas sem senha, card GTK
existente e instalação opcional. Sem GPU passthrough, GRUB/Secure Boot/CUDA ou
ISO completa neste ensaio. Esses gates e a publicação continuam pendentes.

## Reboot da estação de referência — 15/09, 15:58

Boot `bc429101-7648-4871-93bd-62f5335b2c28`, kernel
`6.12.0-160100.4-default`: persistência local dos reparos BOOT-01 a BOOT-05
confirmada. Zero units de sistema/usuário failed; Acer assinado carregado;
sem erro de regulatory.db, metadata Sheliak ausente, argumento null do screencast
ou caminho inválido do Plymouth. Plymouth iniciou e o GDM ativou o screencast
às 15:58:49. NVIDIA 610, Secure Boot, seis extensões, rede e serviços de áudio
permaneceram ativos. Aparência do splash, gravação e brilho não foram aferidos.

BOOT-06 foi reproduzido às 15:59:04 no Shell do greeter PID1415. O Shell pessoal
PID2122 permaneceu ativo, sem reinícios. BOOT-07 e BOOT-08 também permanecem
abertos. Próximo passo de BOOT-06: comparar integração GDM/sessão e outros
hardwares; não é mais necessário pedir novo reboot apenas para reproduzir.

**BOOT-09 — diagnóstico posterior, separado em dois itens:** a exclusão de
`/etc/gdm/custom.conf` foi localizada em `LIVE_ONLY_ARTIFACTS` do instalador.
O arquivo pertence a `gdm-branding-openSUSE`; sem ele e sem outro backend,
GDM 48.0 emite a assertion. A limpeza agora mantém o arquivo e remove somente
as opções de login automático, preservando opções como Wayland. Quatro novas
regressões Rust e nove cenários do smoke cobrem arquivo ausente, outros display
managers, configuração duplicada, erro de I/O e autologin residual.
O leitor GDM instalado reproduziu uma assertion sem o arquivo e zero com o
arquivo corrigido em namespaces descartáveis, sem contato com a sessão pessoal.

O segundo bus não era um fallback causado por falha: o código do GDM 48.0
envolve explicitamente o greeter em `dbus-run-session`, evitando o gerenciador
systemd por conflitos de identificação de sessão/seat. A implementação não
altera essa arquitetura. BOOT-06 continua aberto: o teste de leitura da
configuração não reproduz nem qualifica o encerramento gráfico do Xwayland.
Detalhes e fonte upstream em [boot-integration.md](boot-integration.md).

Reparo local BOOT-09a aplicado às 16:15 de 15/09: arquivo root:root 0644,
autologin automático e temporizado desabilitados; nenhuma opção de GPU imposta.
GDM PID1347 e Shell pessoal PID2122 mantidos, zero units failed. Recibo/reversão
em `/var/lib/lyra-os-theme/gdm-settings-repair-20260915/manifest.json`.
Naquele momento, ainda sem novo boot, RPM publicado ou ISO construída para esta correção.

Evidências locais: `analysis/2026-09-15/boot-repair/post-reboot/` no workspace
LyraOS. Este resultado não encerra os itens da ISO nem substitui a matriz abaixo.

## Reboot após correção do backend GDM — 15/09, 16:18

Boot `cb9c2669-0c26-412c-8b3f-6614f4307c69`, iniciado às 16:18:22,
kernel `6.12.0-160100.4-default`. BOOT-09a validado na estação: configuração
preservada com hash esperado, flags de autologin desativadas, login pelo serviço
`gdm-password`, sessão Wayland ativa e nenhuma assertion `settings->backends`.
GDM PID1340 ativo; Shell pessoal PID2104 com zero reinícios. Zero units failed
nos gerenciadores de sistema e usuário; seis componentes Lyra ativos,
áudio e rede funcionando, NVIDIA 610.57.04 responde e Secure Boot habilitado.

BOOT-06 reapareceu às 16:18:37 no greeter PID1414, durante seu encerramento;
o Shell pessoal permaneceu ativo. No mesmo instante, `gsd-power` do greeter
PID1609 registrou `backlights != NULL`; observação para o diagnóstico do
encerramento, sem atribuição de causa nem correção de brilho comprovada.
BOOT-09b (`systemd1` no bus privado), ACPI/TDX e depreciação do Plymouth persistem.
O screencast do GDM ativou com sucesso às 16:18:29. Avisos transitórios de
autostart/XSettings ocorreram, mas XSettings está ativo na consulta posterior.

Nenhuma nova alteração no sistema nesta verificação. Evidências locais em
`analysis/2026-09-15/gdm-integration/post-reboot/`. Na conclusão desta coleta,
publicação do instalador e receita, build e qualificação da ISO exata e matriz
de hardware permaneciam pendentes.

## Publicação e comparação GDM — 15/09, após os reboots

O lote foi integrado pela [PR #85](https://github.com/lyra-os-linux/lyraos-desktop/pull/85),
commit `9584dc9`. Instalador `0.1.0-lp161.33.1` publicado no release pelo
[pedido OBS #1378217](https://build.opensuse.org/request/show/1378217), com assinatura
e origem verificadas. Os demais reparos gerais estão na receita KIWI integrada;
não são entregues automaticamente pelo RPM do instalador. BOOT-09a ainda precisa
ser consumido e qualificado na candidata exata.

BOOT-06 foi reproduzido com RPMs oficiais Leap em VM sem NVIDIA ou extensões
Lyra, e também na mesma base com os seis componentes Lyra ativos. Três ciclos
completos de login, bloqueio, desbloqueio e logout passaram em cada cenário;
nenhum reinício do Shell pessoal ou GDM e nenhuma unit de sistema failed.
A exceção apareceu em 3/3 logins Leap e 1/3 com Lyra; amostra pequena e sensível
à ordem de execução, sem conclusão de melhoria pela diferença de contagem.

Uma coleta adicional mostrou o GDM enviando SIGTERM ao grupo do greeter e a
exceção cerca de 4 ms depois. A evidência sustenta investigação upstream de
encerramento GDM/Mutter; não justifica substituir o driver NVIDIA ou mudar
Xwayland/PAM. [Reprodução, sinais e limitações](gdm-greeter-reproduction.md)
registrados; não houve alteração na sessão física. VMs e discos foram removidos
após preservar as evidências. A matriz física e a nova ISO continuam pendentes.

## NVIDIA-01 — integração instalada na estação em 16/09

Instalado `lyra-nvidia-610.57.04-lp161.1.1.noarch` do OBS, com assinatura e
conflitos de arquivos verificados. A transação adicionou somente esse pacote;
nenhum driver, kernel ou componente gráfico mudou. Snapshots antes/depois
preservados. Canais Lyra NVIDIA/fornecedor habilitados com verificação GPG;
dois aliases antigos continuam desabilitados, sem locks de pacote.

Integridade RPM, dependências, NVML e Secure Boot passaram. A simulação de
atualização manteve o conjunto coerente; a de remoção selecionou somente o
metapacote. Shell pessoal com zero reinícios, nenhum serviço de sistema/usuário
em falha. Não houve reboot neste passo.

Em cópia isolada da base RPM, sem rede e com host somente para leitura, a
ausência do metapacote reproduziu a proposta de oito componentes NVIDIA 615
e DKMS mantendo KMP assinado 610. Com o contrato instalado, nenhuma mudança;
solicitações explícitas incompatíveis abortaram sem selecionar transação.
Instalação e verificação dos arquivos reais do metapacote, reinstalação
preservando o repositório desabilitado pelo administrador e remoção preservando
os demais pacotes passaram. Configuração modificada foi salva em `.rpmsave`.
Raízes descartáveis removidas; nenhuma VM criada.

Esse ensaio não qualifica migração de um driver antigo, novo kernel/boot,
rollback do sistema, instalação limpa completa, PackageKit/Vega ou qualquer
ISO. Os scriptlets/triggers dos demais pacotes não foram executados na cópia
isolada. Metadados NVIDIA/Lyra foram atualizados, mas o cache OSS do Leap foi
reaproveitado. A integração na candidata segue pendente em
[#82](https://github.com/lyra-os-linux/lyraos-desktop/issues/82) e #63/#56;
suporte depende da GPU e da presença do módulo para o kernel de destino.

[Evidência consolidada](evidence/nvidia-integration-20260916.json).
Recibos completos e plano de reversão em
`analysis/2026-09-16/nvidia-integration/` no workspace LyraOS.

## Matriz da candidata

- CPU Intel e AMD dentro dos requisitos suportados; não exigir TDX por causa
  de mensagens da estação de referência.
- GPU Intel, AMD, NVIDIA compatível e adaptador virtual; notebook híbrido e
  computador com GPU dedicada nos cenários anunciados.
- UEFI com Secure Boot habilitado e desabilitado. BIOS legado só pode ser
  anunciado após implementação e teste próprios; não inferir suporte deste boot.
- Wi-Fi de fabricantes diferentes, Ethernet, equipamento sem Wi-Fi; teclado,
  áudio, brilho, touchpad e suspensão/retorno conforme as capacidades presentes.
- Live, instalação, primeiro boot com conta nova, novo login, atualização e
  rollback. Executar sobre cada variante publicada, com evidências do checksum
  exato. VM complementa os testes físicos; não comprova driver, energia ou firmware
  que ela não expõe.

O inventário do RPM/overlay precisa comprovar que cada correção geral chegou à
candidata. Os testes devem demonstrar que os ajustes específicos da estação não
viraram requisitos ou defaults para outros hardwares. Nenhum P0/P1 pode ser
encerrado apenas porque deixou de ocorrer no computador do mantenedor.

Detalhes técnicos e limites deste lote: [integração de boot](boot-integration.md).

## NVIDIA-02 — Vega GTK/vegad, validação local em 16/09

Instalados `vega-gtk-5.1.39-0.local1` e `vegad-5.1.28-0.local2`.
Apenas pacotes do Vega mudaram; NVIDIA610.57.04, KMP, kernel e Shell PID2075
preservados. RPMs verificados. O card Hardware e Kernel → Hardware reconhece
a pilha oficial, Secure Boot, versões carregada/em disco e contrato Lyra, com
mensagens PT/EN/ES. Instalação opcional Desktop tem confirmação obrigatória,
Polkit apenas administrativo, recuperação Snapper e plano restrito aos RPMs
qualificados; não migra nem remove drivers antigos automaticamente.

O primeiro teste pela janela instalada encontrou `unknown-boot-kernel`:
`ProtectKernelModules=yes` ocultava `/usr/lib/modules`, inclusive o destino de
`/boot/vmlinuz`. Isso não aparecia no executável de consulta rodando diretamente.
Somente NvidiaStatus/CheckNvidia agora podem ler esses arquivos, preservando
UID/capabilities/NoNewPrivileges/filesystem somente leitura e bloqueando syscalls
de carregar/remover módulos. Não copiar um relaxamento geral do isolamento para
a ISO. Este caso exige teste através do broker realmente empacotado.

Após corrigir, status/check D-Bus aprovados como usuário; interface instalada,
65 segundos de atualização automática e atualização manual aprovados. Dez
checagens das políticas de leitura Vega sem interação e nenhuma janela de
autenticação no intervalo observado. Testes isolados incluem parser real do
Zypper (dry-run), cancelamento/negação, inconsistências e perda do serviço.
Fixtures removidos; nenhuma VM criada.

A integração e esta correção entram na próxima receita, mas **publicação em
Git/OBS e qualificação das ISOs continuam pendentes**. Não declarar instalação
completa/migração/rollback de driver, outro kernel, PackageKit, CUDA/suspensão ou
outro hardware aprovados por esses ensaios. Evidência compacta em
[`evidence/vega-nvidia-20260916.json`](evidence/vega-nvidia-20260916.json);
recibos locais em `analysis/2026-09-16/vega-nvidia/`.

## SHELL-01 — Atores descartados durante o encerramento

- **Sintoma:** Panel/Dock acessavam atores já destruídos durante o encerramento
  do GNOME. O segfault físico de18/09 é contemporâneo, mas a causalidade nativa
  continua não comprovada; não marcar a queda como resolvida por inferência.
- **Escopo:** ciclo de vida geral dos componentes LyraExtension, reproduzido
  com GNOME48.8/llvmpipe sem depender da NVIDIA da estação.
- **Fontes:** [Sheliak#34](https://github.com/lyra-os-linux/lyraos-desktop-sheliak/issues/34),
  [PR35](https://github.com/lyra-os-linux/lyraos-desktop-sheliak/pull/35),2.0.3.
  Liberar providers e recursos antes dos filhos de uiGroup; manter restauração
  na desativação normal e tolerar limpeza repetida/reentrante.
- **Receita:** pacote já selecionado; gate passa a exigir>=2.0.3, rejeitando2.0.2
  e pré-release. RPM publicado e verificado conforme registro abaixo.
- **Evidência:** matriz nativa com componentes isolados, juntos e quatro perfis;
  baseline41–168 acessos inválidos por cenário ativo, correção0.208 checks de
  ciclo e69 de coexistência/restauração. Compositor privado encerrado porSIGTERM
  e callback de disable tardio; não é logoutGNOME Session/rebootVM/ISO.
- **Pendente:** integrar esta alteração, consumir RPM publicado e validar
  logout/reboot na candidata por checksum e em hardware aplicável. DING e o
  segfault nativo não têm resolução geral demonstrada por esse ensaio.
- **Reversão:** reverter fontes e reconstruir pelo staging; manter a candidata
  bloqueada em regressão, sem ocultar avisos ou desativar globalmente extensões.

### SHELL-01 — RPM publicado em20/09/2026

[OBS1379316](https://build.opensuse.org/request/show/1379316) aceito; staging24,
release53, fontes223791a, srcmd5 `ce77f2c05e1c481a51826300a8b807ce`.
RPM `sheliak-2.0.3-lp161.1.1.noarch.rpm`, SHA256 público
`0f5b550ee95bedb469efd31779399d08f1d0dcaa89c656ef7191009ddd38e327`, assinatura
verificada.131 arquivos conferem com bundle qualificado; matriz repetida no
RPM extraído passou208checks/setecenários,zero acessosdisposed e saída normal.
Gates completos staging/release passaram. Evidência portátil em
`docs/shutdown-obs-evidence.json` noPR Sheliak35.208 testesPython doDesktop e
CI35532855573 aprovados no commit5c8d2f5. Integração/ISO/hardware continuam
pendentes; SHELL-01 não é encerrado pela publicação do pacote.
## UPD-01 — Coexistência offline com PackageKit

- **Sintoma:** PackageKit conclui a atualização offline, mas a unit Lyra falha
  ao procurar seu diretório de operações, sem existir um pedido Lyra.
- **Escopo:** integração geral systemd/PackageKit, independente do hardware.
- **Fontes:** [Updater #22](https://github.com/lyra-os-linux/lyraos-desktop-updater/issues/22),
  [PR23](https://github.com/lyra-os-linux/lyraos-desktop-updater/pull/23), versão0.2.5.
  Verificação do proprietário de /system-update antes do lock/estado Lyra;
  estado próprio inválido continua rejeitado.
- **Receita:** pacote já selecionado; gate passa a exigir >=0.2.5 e rejeita
  0.2.4 e pré-release. RPM publicado e qualificado conforme evidência abaixo.
- **Ensaio:** VM mínima descartável com PackageKit/zypp/systemd nativos,
  atualização de RPM inerte e dois reboots;0.2.4 reproduziu ENOENT,0.2.5 passou.
  Casos negativos de estado e recuperação própria também passaram.
- **Pendente:** integrar esta alteração;
  verificar inventário e repetir ciclo na candidata identificada por checksum,
  com interface GNOME e hardware aplicável. Não equivale a upgrade Lyra
  completo para sucessor assinado. Nenhuma ISO foi construída neste ensaio.
- **Risco/reversão:** preservar o processamento de pedidos próprios e o marcador
  externo; não desabilitar a unit. Em regressão, reverter fontes e reconstruir
  pelo staging, mantendo o item aberto e sem reduzir o gate da candidata.

### UPD-01 — publicação verificada em20/09/2026

[OBS1379300](https://build.opensuse.org/request/show/1379300) aceito; release rev12,
fontes8cb542f, srcmd5 `7858b2697376f5c70a42e5796ee2e343`.
RPM público `lyra-upgrade-0.2.5-lp161.1.1.x86_64.rpm`, SHA256
`750ef116be969dc41521404049fef5fec443ae6458e8412e8883470dde3d5b55`;
assinatura7edca82e e download verificados.127 testes Rust passaram em staging
 e release; worker de release idêntico ao extraído do staging e testado na VM.
208 testes Python do Desktop e CI35520704707 passaram para a integração do gate.
Fonte de evidência: docs/packagekit-obs-evidence.json no PR Updater23.
Nenhuma instalação no host nem candidata ISO qualificada; UPD-01 continua aberto.
## FW-01 — Instalador BIOS/UEFI e efivarfs, 19/09/2026

Desktop #89: correção em fontes separa BIOS, UEFI com NVRAM e UEFI sem
variáveis utilizáveis. Cada instalação usa somente o disco confirmado e
mantém boot independente de ESPs de outros discos. Testes de componentes
instalaram e iniciaram discos descartáveis nos três modos, incluindo um
ensaio UEFI Secure Boot com chaves SUSE. Nenhuma alteração no firmware do host.

**RPM/OBS entregue:** `lyra-installer-0.1.0-lp161.34.1`, pedido OBS
1379053 aceito, Git `28a7f1d`, assinatura e origem conferidas.
**Inclusão na ISO e qualificação do checksum exato pendentes.**
Não encerrar este item pelos testes de componentes. Contrato, reprodução e
limites em [firmware do instalador](installer-firmware-requirements.md);
recibos locais em `analysis/2026-09-19/installer-firmware/boot-vm/`.


## VEGA-01 — Atualização do Painel a cada clique, 20/09

O Vega GTK mantinha os cards ao navegar de volta ao Painel ou clicar na aba já
ativa, até o próximo ciclo automático. A correção geral, independente de GPU ou
firmware, está no [Vega PR147](https://github.com/lyra-os-linux/vega/pull/147),
versão 5.1.40, fontes `99b039bc6d6f9bc62c697b9af1668434e1410fee`.
Agrupa cliques e temporizador em uma consulta e no máximo uma repetição, preserva
consultas assíncronas e isola falhas entre os cards. O intervalo automático
continua em 5 minutos por padrão, configurável de 1 a 60 minutos.

O gate da imagem exige `vega-gtk >= 5.1.40`. Testes rejeitam 5.1.37, 5.1.39 e
5.1.40~rc1. O CI das fontes 35533662810 passou, incluindo GTK/D-Bus privados com
rajadas de 50 pedidos e recuperação após falha. OBS1379318 aceito, staging22/release110; RPM público
`vega-gtk-5.1.40-lp161.1.1.x86_64.rpm`, SHA256
`1564ec93722bfd35230570679c08ba585899d38876fcf4475ca8323f2ac321ff`.
Assinatura7edca82e válida; download público idêntico à API; binário de release
idêntico ao staging qualificado. Sete verificações GTK/AT-SPI do RPM e 52 de
perfis passaram; gates completos staging/release aprovados.
[Evidência](https://github.com/lyra-os-linux/vega/blob/fix/dashboard-tab-refresh/docs/dashboard-obs-evidence.json).
Nenhuma alteração do pacote instalado na estação. Inclusão e qualificação na
ISO exata permanecem pendentes.

Na candidata identificada por checksum: abrir Painel, voltar de Software,
clicar na aba ativa, repetir cliques durante consulta lenta, provocar falha e
recuperação do backend e conferir todos os cards. Verificar também o intervalo
configurado, sem senha para as consultas. Não concluir este registro apenas com
testes de fontes ou do RPM. Em caso de regressão, restaurar a revisão OBS anterior
pelo fluxo de rollback via staging e requalificar; não reduzir silenciosamente o
mínimo exigido pela imagem.

## VIRT-01 — QEMU/KVM, Vega e Lyra VMs, Alpha 8

Integração solicitada pelo mantenedor em 17/09. A seleção inicial local incluía
apenas os programas e o grupo libvirt no live; a receita agora declara o backend
QEMU, cliente e rede padrão explicitamente, sem depender de recomendações do
solver, e habilita seus sockets locais durante a construção da imagem.

O acesso sem senha pelo grupo libvirt fica restrito ao liveuser. A conta criada
pelo instalador mantém wheel e a autenticação Polkit administrativa existente.
Não se habilitam TCP/TLS, rede NAT automática, máquinas ou discos no build.
Detalhes e reversão em [virtualization.md](virtualization.md).

Estado em 21/09: 211 testes Python passaram, incluindo três novos contratos.
Ensaio em VM Leap 16.1 descartável aprovou 23 verificações de autorização,
negação, sockets, NAT/DHCP, disco qcow2 e inicialização KVM BIOS/UEFI; limpeza e
desligamento concluídos. Evidência em
[evidence/virtualization-20260921.json](evidence/virtualization-20260921.json).
Nenhuma ISO construída ou qualificada. Depois da auditoria, repetir os cenários
na ISO exata com conta instalada e sessão live, incluindo Vega e Lyra VMs gráficos,
console, DNS/conectividade, instalação de convidado e persistência após reboot.
Não marcar este item concluído apenas pela seleção de pacotes ou pelos contratos.

Qualificação adicional de componente em 21/09: instalação Alpine BIOS, boot sem
ISO, edição de recursos com dados preservados e ambas as opções de remoção
aprovadas. Vega GTK 5.1.44 corrige cortes nos diálogos encontrados no ensaio;
piso atualizado na receita, OBS #1379536 publicado e RPM público verificado
(assinatura, revisão e conteúdo igual ao staging qualificado). Evidência em
`docs/evidence/vm-full-cycle-20260921.json`. VIRT-01 continua aberto para a ISO
exata e GNOME/Wayland; não extrapolar o ensaio Xvfb/BIOS para esses cenários.

## FF-THEME-01 — Tema oficial Firefox, Alpha 8

Issue [Firefox #1](https://github.com/lyra-os-linux/lyra-firefox-ext/issues/1).
Tema estático independente `theme@lyraos.com.br`, claro/escuro conforme sistema,
metadados en-US/pt-BR/es-ES e sem permissões. Paleta aprovada pelo mantenedor
em 21/09/2026. Implementação em Firefox PR2; pacote próprio lyra-firefox-theme.

A receita adiciona o pacote, que expõe o XPI assinado através do diretório
nativo distribution/extensions. Não há política de instalação para o tema:
o ensaio mostrou que normal_installed sobrescreve escolhas existentes.
A distribuição nativa preservou temas em perfis novos/existentes, seleção,
reinício, troca e remoção sem reinstalação. Firefox ESR140.13 verificou a
assinatura Mozilla (signedState=2). Paleta aprovada e metadados trilíngues.

OBS e inventário i18n incluem o pacote; 211 testes da receita passaram.
Publicado por OBS1379465: lyra-firefox-theme-0.1.0-lp161.1.1.x86_64.rpm,
SHA256 465810460a44cc48305ff1355d19f531dc8bca45e2f60509095b52f2f746f002.
Gates completos staging/release passaram; assinatura do RPM e XPI verificados,
download público idêntico à API, rpmlint sem erros/avisos. O repasse real de
Downloads0.1.2 com tema ativo passou, incluindo arquivo final e recuperação.
[Evidências do componente](https://github.com/lyra-os-linux/lyra-firefox-ext/tree/feat/alpha8-theme/theme/evidence).

Ainda pendente: qualificação da candidata exata, incluindo escala/teclado,
repasse Downloads e upgrade de versão quando aplicável. Nenhuma ISO gerada.
Reversão: retirar o pacote da receita e selecionar outro tema; preservar
perfis, dados e integração Downloads. A issue permanece aberta até a candidata.

### 21/09 — Substituição explícita de virt-manager

Mantenedor solicitou remover virt-manager da distro e incluir Lyra VMs.
Receita passa a exigir lyra-vms >= 0.1.0, virt-viewer e vega-gtk >= 5.1.41.
Pacote lyra-vms adicionado ao inventário obrigatório OBS. Vega 5.1.41 e Lyra VMs
0.1.0 publicados pelas requests #1379483/#1379484, com RPMs públicos assinados
e binários iguais aos testados. A qualificação da candidata permanece pendente;
não gerar ISO antes da auditoria. Evidência em lyra-vms-staging-20260921.json.


## PREP-01 — Preparação inicial dos repositórios

A receita e a verificação de conteúdo da imagem exigem vegad >= 5.1.32 e
Vega GTK >= 5.1.45. Isso evita uma candidata com o antigo job que atualizava
pacotes automaticamente ou sem a interface de estado e recuperação.
As issues vegad #56–#64 foram encerradas nas PRs #65–#73; SDK #7 e Vega #155
completam a revisão de chaves desconhecidas por fingerprint e identidade.

RPMs finais publicados pelas requests OBS [1380263](https://build.opensuse.org/request/show/1380263)
e [1380264](https://build.opensuse.org/request/show/1380264). Fontes, assinaturas,
proveniência, scripts e conteúdo conferidos; payload final idêntico ao staging.
[Evidências portáveis](evidence/preparation-rpms-20260924.json).

VM Leap 16.1: instalação dos RPMs e upgrade passaram, incluindo estados
concluído/pendente/isento, repositórios reais com Packman, 120 atualizações
pendentes sem upgrade automático de pacotes, falha de rede/Retry autorizado,
recuperação automática do lock RPM e persistência no reboot. Interface do RPM
GTK via Broadway mostrou os estados reais. Tumbleweed teve build e inspeção;
a execução foi qualificada somente no Leap.

Continua pendente na ISO exata: live sem preparação, instalação pelo Lyra
Installer, primeiro login GDM/Wayland, diálogo Polkit e recuperação pela UI.
Não marcar PREP-01 concluído com o ensaio de componentes. Reversão: bloquear
novas candidatas e corrigir no staging; não reduzir os pisos para reintroduzir
o job antigo de atualização automática.

## GRUB-04 — Preferência local sobrescrita após atualização (25/09)

Na estação física, uma atribuição GRUB_THEME=openSUSE apareceu após o include
da preferência Lyra, anulando-a. Reparo local recolocou a preferência por último,
com backup, geração em candidato, grub2-script-check e preservação das seis
linhas kernel/initrd. Não houve reboot nem alteração de pacote nesta correção.

Fontes corrigidas em Theme PR17/PR18, commit
`26fb9e67c88b2dbc4f3bfa0d5a339f48a00cb9db`: preferência `%config(noreplace)`,
atribuição antes do include final, remoção restaura o backup; dependência
`plymouth-dracut` e geração do GRUB após o initrd. Receita exige tema >=1.9.4.

RPM staging `1.9.4-lp161.2.1`: 10 verificações de instalação limpa e 22 de
upgrade/branding/configuração/remoção passaram na VM Leap16.1; assinatura
conferida, seis comandos kernel/initrd preservados. Evidência e limitações em
`docs/evidence/grub-rpm-20260925.json`. O lint mantém 2 erros e 4 avisos
explicitados nessa evidência.

O overlay omite `plymouth` e `lyra-plymouth` somente quando o dracut recebe
`kiwi-live` em `add_dracutmodules` (arquivo temporário 02-livecd.conf do KIWI).
O KIWI remove esse arquivo antes de empacotar o sistema, preservando Plymouth
nos initrds do sistema instalado. A omissão XML de initrd não é usada: o
builder ISO do KIWI 10.2.33 não a aplica. A verificação do initrd extraído da
ISO continua obrigatória.

A validação nativa encontrou atributos `version` de pacote não aceitos pelo
schema. Foram removidos, mantendo os pisos no verificador executado durante
a configuração da imagem (incluindo lyra-vms e lyra-firefox-theme). O CI agora
valida o XML com o schema do KIWI 10.2.33 oficial da base.

Item permanece aberto: boot visual BIOS/UEFI, atualização na candidata exata
e comportamento após substituição integral de `/etc/default/grub` ainda não
foram qualificados. Nenhuma ISO foi gerada neste ensaio.


## DL-01 — arquivo apagado após repasse do Firefox (19/09/2026)

- **Sintoma/causa:** Firefox 140 ESR e Lyra Downloads 0.1.1 usando a mesma
  pasta podiam concluir o repasse sem preservar o arquivo. A pausa do Firefox
  remove o placeholder; o cancelamento posterior ainda pode apagar esse
  caminho, agora aberto pelo aria2.
- **Alcance:** geral da integração de downloads, independente de GPU/firmware;
  não copiar configurações ou dados do perfil pessoal para a ISO.
- **Fontes:** Downloads `03fd5780a37f10d62d174bdbcafeed42e82acb39`, versão 0.1.2.
  Native host marca repasses automáticos para reservar o nome do Firefox e o
  backend escolhe nome numerado livre antes de iniciar aria2. Downloads manuais
  mantêm o comportamento. XPI assinado 0.1.1 permanece compatível.
- **Evidência local:** 45 testes Rust, aria2 real e Firefox instalado em perfil
  temporário; arquivo final com bytes exatos, estado restaurado após suspensão
  da extensão, cancelamento confirmado antes da recuperação e duplicata tardia
  recusada. A recuperação injeta o estado de uma resposta perdida; não simula
  queda de processo. Permissões do perfil de teste concedidas pelo controlador.
- **RPM/estação:** 0.1.2-lp161.1.1 publicada e instalada após
  [SR 1379046](https://build.opensuse.org/request/show/1379046), revisão OBS
  `c509218b46a5eb8a385571ec4c9d5713`. RPMs públicos assinados, origem e
  integridade instaladas conferidas; backend/host em execução na 0.1.2, fila
  vazia preservada. Gate completo de staging/release aprovado. O ensaio com
  binários instalados preservou os bytes e passou na recuperação.
- **Risco/reversão:** repasse automático usa sufixo numérico no nome final;
  sem mudança de schema SQLite. Para interromper captura, desativar a opção na
  extensão e baixar pelo Firefox. Reverter para 0.1.1 reintroduz a perda do
  arquivo; não usar essa reversão com captura automática habilitada.
- **Receita:** os três pacotes estão selecionados explicitamente. O verificador
  executado por `kiwi/config.sh` exige os três pacotes >= 0.1.3, preservando
  o piso posterior da integração e das traduções; recusa pacote ausente, versão antiga ou pré-release abaixo
  desse piso antes de finalizar a imagem. A dependência do RPM nativo mantém
  backend/host na mesma versão. Isso não substitui assinatura/proveniência nem
  comprova que uma ISO foi construída.
- **ISO exata:** pendente. Confirmar Downloads e integração nativa >= 0.1.2,
  XPI assinado 0.1.1, dependência exata entre backend e host, captura em pasta
  compartilhada, integridade do arquivo, recuperação e atualização de instalação
  anterior. Ensaiar em VM e outro hardware aplicável. Registrar checksum da
  candidata e evidências antes de marcar inclusão/qualificação como concluídas.

Evidência portátil: [downloads-handoff-20260919.json](evidence/downloads-handoff-20260919.json).
Relatórios locais: `analysis/2026-09-19/host-downloads-0.1.2/` (correção) e
`analysis/2026-09-19/obs-0.1.2/` (publicação e ensaio dos RPMs).

Integração em 25/09: preservados os pisos 0.1.3 já presentes no main. As
versões 0.1.2/0.1.1 acima identificam os RPMs do ensaio histórico, não o
inventário final da candidata. Revalidar o repasse no artefato exato.
