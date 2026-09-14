# Variantes GNOME padrão e NVIDIA — decisão de 14/09/2026

O mantenedor decidiu oferecer duas variantes GNOME, inspiradas na escolha de
download do Pop!_OS. Esta decisão substitui o cancelamento anterior da imagem
NVIDIA e o plano de ISO única. **A variante NVIDIA ainda precisa ser implementada
e qualificada**; este documento não anuncia uma imagem pronta.

| Variante | Composição pretendida | Validação específica |
| --- | --- | --- |
| Padrão | Sem a pilha NVIDIA pré-instalada; drivers gráficos da base e instalação opcional pelo Vega GTK | Live/instalação em Intel/AMD suportados e instalação posterior NVIDIA |
| NVIDIA | Kernel, KMP, bibliotecas e firmware NVIDIA compatíveis no live e no sistema instalado | GPU NVIDIA física suportada, offload híbrido, Secure Boot e recuperação |

Ambas usam a mesma base Leap 16.1, aplicativos próprios RPM e build KIWI local.
KDE/XFCE continuam fora deste ciclo. Acompanhar implementação em
[#63](https://github.com/lyra-os-linux/lyraos-desktop/issues/63) e qualificação em
[#56](https://github.com/lyra-os-linux/lyraos-desktop/issues/56).

## Contrato a implementar e qualificar

- Reutilizar a receita GNOME com seleção explícita de variante, evitando cópias
  divergentes. Identificar variante no artefato e no manifesto, preservando
  identidade comercial e gates de `release.toml`.
- Auditar os inventários: impedir NVIDIA indireta por recomendações na padrão;
  preservar Mesa, firmware e drivers necessários a Intel/AMD e à operação híbrida.
- Selecionar a família do driver conforme hardware e base qualificados. Os
  nomes G06 históricos abaixo não definem o conjunto G07 observado atualmente.
- Usar origens RPM confiáveis e compatíveis com o Leap; conferir kernel, KMP,
  bibliotecas, firmware e dependências reais dos metapacotes em conjunto.
- Preservar a composição do live até a instalação sem rede e o primeiro boot;
  a variante NVIDIA não deve precisar baixar o driver para concluir a instalação.
- Manter o Vega GTK na padrão para instalação opcional e reconhecer corretamente
  o conjunto já instalado na NVIDIA, sem declarar sucesso por mera presença RPM.
- Produzir checksum, inventário RPM, SBOM e evidências próprios de cada imagem,
  ligados à mesma revisão de receita. ISO local; OBS para os RPMs.
- Validar live, instalação, primeiro boot, update/reboot e rollback em ambas.
  Na NVIDIA, incluir hardware físico, assinatura/Secure Boot ligado/desligado,
  renderização/offload, Wayland, monitor externo, DPMS e suspensão/retomada.
  VM com GPU virtual não qualifica execução do driver físico.
- Conferir atualizações por Vega/vegad, Zypper e GNOME Software/PackageKit.
  Uma transação parcial pode quebrar o driver que funcionava na ISO; validar
  o estado final e preservar uma rota de recuperação em ambiente descartável.
- Rejeitar cada artefato afetado por P0/P1 ou falta de evidência. O sucesso
  de uma imagem não homologa a outra; não anunciar ambas como prontas se uma
  ainda estiver bloqueada. A variante amplia a matriz e o custo de manutenção.

## Limite da espera por upstream

A [issue #82](https://github.com/lyra-os-linux/lyraos-desktop/issues/82) centraliza
o acompanhamento semanal até a **preparação da RC1 do Lyra**, ainda sem data
fixada. O cronograma é independente do lançamento final do Leap. Preparar
diagnóstico e alternativas nas revisões; se a correção upstream não chegar,
corrigir a integração ao nosso alcance e validar antes de gerar a candidata.
Não prometer corrigir código interno do driver ou fazer mudança ampla às pressas.

Em 14/09, módulo/KMP 595.91.07 com bibliotecas 595.99.02 ainda produzem erro
NVML de incompatibilidade. Esse conjunto não está aprovado para pré-instalação.
O mantenedor mantém as atualizações liberadas, sem recriação automática de
locks. A decisão não instala pacotes nem reinicia a estação. Falhas graves de
uso ou boot podem exigir análise antecipada. A cadência está registrada, sem
agendamento automático configurado.

## Contrato histórico do fluxo Vega G06

Os registros abaixo preservam ensaios e políticas anteriores; não comprovam
qualificação na base e no conjunto G07 atuais. Qualquer reaplicação precisa
conferir versão, propriedade dos arquivos e reversão. A política vigente de
atualizações liberadas prevalece sobre as retenções propostas nesse histórico.

- detectar conservadoramente GPU G06 suportada e bloquear hardware incerto;
- exigir confirmação explícita;
- verificar o estado do Secure Boot;
- criar snapshot Snapper somente leitura antes da primeira mudança;
- usar exclusivamente pacotes RPM do repositório oficial NVIDIA para Leap;
- instalar `nvidia-open-driver-G06-signed-kmp-meta` e
  `nvidia-userspace-meta-G06` em conjunto;
- rejeitar instalação parcial ou versões desalinhadas, auditando todos os
  RPMs G06 efetivos e não apenas os metapacotes;
- executar `dracut --force`, orientar o reinício e preservar rollback;
- após o reboot, verificar módulo ativo, `nvidia-smi`, Wayland e conectores
  DRM antes de declarar sucesso;
- qualificar suspensão por versão e topologia gráfica, bloqueando-a de forma
  reversível quando houver regressão conhecida;
- reconciliar a política no início do `vegad`, inclusive após atualizações que
  não tenham sido iniciadas pela tela NVIDIA.

## Descobertas preservadas

Testes anteriores encontraram um caso real em que o módulo assinado estava na
versão `580.159.03`, enquanto `nvidia-video-G06`, `nvidia-gl-G06` e
`nvidia-common-G06` permaneciam em `570.172.08`. O firmware GSP esperado não
existia e a saída HDMI ligada à GPU dedicada falhou. Os metapacotes de KMP e
userspace em lockstep corrigiram o cenário.

Logo, atualizar apenas o KMP não é suportado. Kernel, módulo, userspace e
firmware precisam permanecer compatíveis; uma atualização de kernel sem KMP
publicado deve ser bloqueada antes da transação.

Em 16/08/2026, o notebook híbrido Acer Nitro AN515-57 reproduziu uma segunda
classe de falha com a pilha `580.159.03`: durante a suspensão, o módulo NVIDIA
falhou em `mmuWalkUnmap`/`gpuSanityCheckRegisterAccess`, manteve o GNOME Shell
preso no kernel e provocou soft lockups. SMART, log NVMe, contadores Btrfs e um
scrub completo não encontraram erro de armazenamento. Essa combinação fica em
quarentena de suspensão e hibernação até uma versão posterior passar pelo gate.

A quarentena usa exclusivamente o drop-in gerenciado
`/etc/systemd/sleep.conf.d/90-lyra-nvidia-quarantine.conf`. O Vega só remove o
arquivo se o marcador de propriedade estiver presente, e o remove
automaticamente quando uma versão qualificada substitui a versão afetada.

## Gate histórico G06

- GPU NVIDIA real, incluindo o notebook híbrido disponível;
- Secure Boot ligado e desligado;
- instalação, reboot, `nvidia-smi`, Wayland e monitor externo;
- suspensão e retomada controladas, sem soft lockup, erro NVRM, falha de freeze
  ou incremento inesperado de desligamentos inseguros;
- aplicação e remoção automática da quarentena em versões bloqueada/aprovada;
- atualização conjunta de kernel/driver;
- falha parcial injetada e rollback para uma baseline inicializável;
- evidência revisável sem credenciais.

O fluxo não é declarado suportado enquanto qualquer item acima estiver sem
evidência ou houver P0/P1 aberto.
