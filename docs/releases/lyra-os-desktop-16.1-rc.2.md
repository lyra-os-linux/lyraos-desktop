# Lyra OS 16.1 RC 2 “Odisseia” — notas de lançamento

Segunda candidata de lançamento do Lyra OS Desktop 16.1 sobre **openSUSE Leap
16.1**. A RC 1 (`v16.1-rc.1`) foi publicada; em 24/10/2026 o mantenedor
decidiu levar à candidata duas correções do vegad em vez de deixá-las para
uma atualização depois do lançamento. Como o conteúdo da imagem muda, a RC 2
é uma nova candidata e repete o gate. Em 25/10/2026 o mantenedor decidiu
adiar a versão estável para incluir o **controle parental básico**
([plano](../parental-controls-plan.md), [ADR 0019](../adr/0019-basic-parental-controls.md)).
Como nenhuma ISO da RC 2 tinha sido publicada, a RC 2 passa a trazer também
esse recurso. A RC 2 foi publicada em **28 de outubro de 2026**; a versão
estável está prevista para **5 de novembro de 2026**, com **26 de novembro de
2026** como limite. Fora a
exceção abaixo, vale o congelamento estrito da RC 1: só correções de bugs,
travamentos, segurança e performance crítica em pacotes já distribuídos.

A identidade técnica é `16.1-rc.2`, tag `v16.1-rc.2`, arquivo
`LyraOS-Desktop-16.1-rc.2-x86_64.iso`, publicado em
[SourceForge](https://sourceforge.net/projects/lyra/files/releases/16.1/rc2/desktop/).

| Campo | Valor |
| --- | --- |
| Build | #10, 27/10/2026 |
| Commit | `f5d4dc67cd200e3fdf25fbda11b9465e935afa90` |
| SHA-256 | `9592becd756cfec6d58f5589f2da0d560ac175051df26790c90b08308c238873` |
| Gate | completo e aprovado em 27/10/2026 |
| Decisão | GO do mantenedor em 28/10/2026 |

## Exceção ao congelamento

O controle parental básico é funcionalidade nova depois da RC 1. Entra por
decisão explícita do mantenedor (25/10/2026), com qualificação em VM, gate
próprio ([gate #9](../parental-controls-gate.md)) e reversão por pacote. A
retirada do Flatpak e do LinuxToys da instalação padrão faz parte da mesma
decisão (26/10/2026). Detalhes e limites:
[qualificação 16.1](../parental-controls-upstream-qualification.md).

## Mudanças desde a RC 1

- Firewall no Vega: o vegad 5.1.39 informa a zona que realmente filtra o
  tráfego da máquina (`public`, ligada à interface de rede), e não a zona
  `docker` predefinida que o firewalld lista mesmo sem a interface `docker0`
  ([vegad#83](https://github.com/lyra-os-linux/vegad/issues/83),
  [vegad#85](https://github.com/lyra-os-linux/vegad/pull/85)). As regras do
  firewall não mudam; só o nome da zona exibido estava errado.
- Contrato D-Bus: a introspecção de `org.lyraos.Vega1.Snapshots` passa a
  declarar o sinal `ClearProgress`, como no contrato de `lyra-vega-dbus`
  ([vegad#86](https://github.com/lyra-os-linux/vegad/pull/86)).
- Vega: o vega-gtk 5.2.0 troca a interface GTK pelo port Tauri, com as
  mesmas funções ([vega#159](https://github.com/lyra-os-linux/vega/pull/159)).
  Isso é uma exceção ao congelamento, aprovada pelo mantenedor.
- NVIDIA em notebooks híbridos: o vegad 5.1.40 instala o driver Vulkan da GPU
  integrada junto com o driver NVIDIA, e o `lyra-nvidia` habilita o RTD3
  fine-grained. Assim a GPU NVIDIA desliga quando fica ociosa
  ([vegad#78](https://github.com/lyra-os-linux/vegad/issues/78),
  [vegad#89](https://github.com/lyra-os-linux/vegad/pull/89)).
- Drivers Vulkan: a imagem traz `libvulkan_intel` e `libvulkan_radeon`. Antes,
  eles só entravam pela detecção de hardware do zypper, que o build e o
  instalador não executam, e o GTK 4 caía para GL ou renderizava na GPU
  NVIDIA ([#185](https://github.com/lyra-os-linux/lyraos-desktop/pull/185),
  [#186](https://github.com/lyra-os-linux/lyraos-desktop/pull/186)).
- Energia: o `tuned-ppd` fornece os perfis de energia do GNOME, que antes não
  apareciam ([#167](https://github.com/lyra-os-linux/lyraos-desktop/issues/167)).
- Sessão: `XDG_DATA_DIRS` deixa de terminar com barra, o que gerava avisos de
  serviço D-Bus duplicado a cada login
  ([#169](https://github.com/lyra-os-linux/lyraos-desktop/issues/169)).
- Instalador: o rótulo de versão vem da própria imagem; a ISO anterior da RC 2
  mostrava "RC 1" ([#183](https://github.com/lyra-os-linux/lyraos-desktop/pull/183)).
- Firewall no Vega, de novo: no Desktop, o polkit do firewalld negava a
  leitura da zona ativa ao processo de consulta do vegad, e o Vega mostrava a
  zona vazia. O vegad 5.1.41 faz essa leitura no serviço principal
  ([vegad#90](https://github.com/lyra-os-linux/vegad/pull/90)). O defeito foi
  achado no gate desta candidata e também existia na RC 1.
- Bluetooth sem adaptador: o vegad esperava o `bluetoothctl` para sempre, e a
  página Bluetooth do Vega mostrava um esqueleto por 60s e depois um erro
  cru. O Painel e a página Serviços marcavam o `bluetooth.service` como
  "habilitado, mas parado". O vegad 5.1.44 responde na hora que não há
  adaptador e não conta serviços pulados por condição como falha, e o
  vega-gtk 5.3.2 mostra "Nenhum adaptador Bluetooth encontrado" e deixa de
  pintar de alerta o serviço indisponível
  ([vegad#93](https://github.com/lyra-os-linux/vegad/pull/93),
  [vegad#94](https://github.com/lyra-os-linux/vegad/pull/94),
  [vega#161](https://github.com/lyra-os-linux/vega/pull/161),
  [vega#163](https://github.com/lyra-os-linux/vega/pull/163)). O defeito foi
  achado no gate desta candidata e existia desde o vegad 1.3.3.
- "Atualizar tudo" no Vega deixava para trás a atualização que precisava de
  uma dependência nova de outro repositório: o vegad atualiza um repositório
  por vez, e o zypper descartava o pacote sem erro. O vegad 5.1.45 conclui
  essas atualizações numa passada final com todos os repositórios
  ([vegad#95](https://github.com/lyra-os-linux/vegad/pull/95)).
- Rede no Vega com acento: o vegad rodava o `nmcli` sem locale, e a conexão
  cabeada padrão de uma instalação em português aparecia como "Conex?o
  cabeada 1"; configurar IP estático nela falhava, porque esse nome não
  existe. O vegad 5.1.46 roda o `nmcli` em UTF-8
  ([vegad#96](https://github.com/lyra-os-linux/vegad/pull/96)). O defeito foi
  achado no gate do build #8 e já existia na RC 1.
- Sessão live: a tela travava depois de 5 minutos parada e não havia senha
  para destravar, porque a conta da live entra sem senha. Quem saía de perto
  durante a instalação perdia a sessão. A live desliga o bloqueio e o
  apagamento de tela só para a conta da live; o sistema instalado mantém o
  padrão do GNOME. O defeito foi achado no gate do build #9 e já existia na
  RC 1.
- A imagem exige vega-gtk 5.3.2 e vegad 5.1.46 ou posteriores
  (`check-gnome-image.py`).
- Segurança: só o grupo `wheel` usa `sudo` com a própria senha. O instalador
  deixava qualquer conta virar root com a própria senha. A imagem passa a usar
  a política `sudo-policy-wheel-auth-self` do openSUSE, e o `lyra-release`
  corrige instalações existentes pelo zypper
  ([#191](https://github.com/lyra-os-linux/lyraos-desktop/pull/191),
  [#192](https://github.com/lyra-os-linux/lyraos-desktop/pull/192)).
- Controle parental básico: conta supervisionada criada no Vega (página
  Usuários), regras no aplicativo "Controle parental" do GNOME (navegadores,
  aplicativos, instalação e classificação etária). A conta supervisionada não
  administra o sistema, não entra por TTY nem SSH, não usa o Alt+F2 e não vê os
  terminais nem o Vega; os menus e a busca do Sheliak respeitam as regras.
  Componentes: `lyra-parental-controls` 0.1.0, vega-gtk 5.3.x, vegad 5.1.42+ e
  Sheliak 2.0.6. O controle é básico e não resiste a uma criança com
  conhecimento técnico.
- Flatpak deixa de vir instalado. Ele é habilitado na página Software do
  Vega, com aviso para contas supervisionadas, e o Flathub aparece junto.
  Instalações existentes mantêm o Flatpak.
- Depois do build, por atualização: o vegad 5.1.47 pede a senha de
  administrador uma vez para uma fila de Flatpaks, em vez de uma por Flatpak
  ([vegad#97](https://github.com/lyra-os-linux/vegad/pull/97)). A ISO traz o
  5.1.46; o 5.1.47 chega pela primeira atualização do zypper ou do Vega.
- LinuxToys deixa de vir instalado. Continua disponível no repositório do
  Lyra.
- Escopo: KDE Plasma e XFCE foram abandonados; o GNOME é a única edição
  Desktop ([ADR 0018](../adr/0018-abandon-kde-xfce.md)). Nenhum pacote da ISO
  muda por isso.

O vegad 5.1.39 foi promovido ao canal de release do OBS pelo SR 1392226,
depois de testado numa VM Leap 16.1 contra o 5.1.38. O vegad 5.1.40 seguiu
pelo SR 1392433, testado em VM contra o 5.1.39 e no notebook híbrido da
issue, e o 5.1.41 pelo SR 1392496, testado em VM com a política polkit do
Desktop. O vega-gtk 5.2.0 entrou pelo SR 1392280. O vegad 5.1.44 seguiu
pelo SR 1393050, testado numa VM do Desktop sem Bluetooth; a 5.1.43 ficou
só no staging, porque o teste mostrou que ela não cobria o serviço que
nunca chega a iniciar. O vegad 5.1.45 foi testado na mesma VM com dois
repositórios locais em que a atualização de um depende do outro, e o
5.1.46 na VM do gate do build #8, com IP estático na conexão padrão.

Várias ISOs da RC 2 foram construídas e nenhuma publicada: o gate de uma
delas achou o defeito do firewall, e a decisão do controle parental veio
depois. A RC 2 publicada é a reconstrução com o lote completo.

## Escopo e limites

Os mesmos da [RC 1](lyra-os-desktop-16.1-rc.1.md#escopo-e-limites):

- Só instalação nova. Uma instalação RC 1 recebe o vegad, o vega-gtk, a
  correção do `sudo` e o controle parental (o vega-gtk exige o
  `lyra-parental-controls`) pela atualização normal do zypper, sem
  reinstalar. As demais mudanças da imagem (`tuned-ppd`, drivers Vulkan,
  `XDG_DATA_DIRS`, Flatpak e LinuxToys fora da instalação padrão) não chegam
  por atualização.
- Controle parental básico: não filtra sites e não resiste a uma criança com
  conhecimento técnico; com o Flatpak habilitado, a criança pode instalar e
  abrir apps Flatpak ([#102](https://github.com/lyra-os-linux/lyraos-desktop/issues/102)).
- RAID, LVM, particionamento manual e instalação lado a lado continuam fora
  do cenário coberto.
- Idiomas: `en-US`, `pt-BR` e `es-ES`, com `en-US` como fallback explícito.

## Problemas conhecidos

- Na sessão live, instalar software pelo Vega pede uma senha que a conta da
  live não tem, e a instalação não acontece. O Instalador do Lyra não é
  afetado, nem o sistema instalado. Já existia na RC 1; a correção
  ([#211](https://github.com/lyra-os-linux/lyraos-desktop/pull/211)) entra na
  versão final.

## Qualificação obrigatória

A RC 2 repete o gate da RC 1 (`../release-gate.md`) na ISO exata, em VM
QEMU/KVM:

- sessão live;
- instalação UEFI com NVRAM e Secure Boot;
- BIOS legado e UEFI sem variáveis EFI;
- primeiro boot;
- rollback;
- `i18n`;
- o resultado `obs-repositories` do health check de release.

No sistema instalado, o status do firewall no Vega precisa mostrar a zona
`public`, o seletor de perfil de energia do GNOME precisa aparecer e o Vega
5.3.2 precisa abrir todas as páginas. `installed-gate.sh sudo-policy` e
`parental` precisam passar, assim como o roteiro manual do
[gate #9](../parental-controls-gate.md). Um defeito não trivial interrompe a
promoção e gera a RC 3; os critérios não são reduzidos para preservar a data.

Resultado: o build #10 passou em todos os itens acima em 27/10/2026. Na
UEFI com Secure Boot passaram sessão live (online e offline), instalador,
primeiro boot, Secure Boot, `sudo-policy` e `parental`; também passaram
BIOS legado, UEFI sem NVRAM, rollback e `i18n`. Do roteiro manual do gate #9
foram executados os itens 1 e 3, por decisão do mantenedor; os demais já
tinham passado no build #7, com o mesmo controle parental. Na live, a tela
ficou 6 minutos parada sem bloquear.

## Integridade

Arquivo esperado: `LyraOS-Desktop-16.1-rc.2-x86_64.iso`. Para verificar:

- o checksum, com `sha256sum -c LyraOS-Desktop-16.1-rc.2-x86_64.iso.sha256`;
- a assinatura destacada `LyraOS-Desktop-16.1-rc.2-x86_64.iso.sha256.asc`,
  com a chave oficial de release (impressão digital `01B6 3EED BE6B 0791 26A0
  116E FA73 53A1 31EC EFEB`, publicada em `docs/release-signing-key.asc`).

## Versão final

A versão estável `16.1` será reconstruída a partir dos pacotes GA do openSUSE
Leap 16.1 (3 de novembro de 2026), com o mesmo conteúdo Lyra da RC 2, e
passará por um gate reduzido antes da publicação, prevista para 5 de
novembro de 2026, com 26 de novembro de 2026 como limite.
