# Roadmap do Lyra OS

## Escopo ativo e evidência

O foco da versão final 1.1 é exclusivamente o GNOME e seus pacotes. KDE e XFCE
estão em segundo plano; não há estabilização conjunta das três edições nem
prazo comum de lançamento. A proposta de ISO NVIDIA dedicada está cancelada.
A [situação do GNOME](status-gnome.md) registra o que foi integrado e o que
continua pendente de qualificação. O estágio canônico está em `release.toml`.

## Flavor KDE experimental — planejamento futuro

Fica planejado um flavor KDE experimental, separado da edição Desktop GNOME,
que continua sendo a edição oficial e recomendada do Lyra OS. O flavor começa
com uma Alpha formada somente pela pilha KDE da base, sem pacotes próprios do
Lyra; em etapas posteriores recebe primeiro os wallpapers e depois um Vega
nativo em Qt. O Welcome não faz parte do flavor, e uma integração própria de
atualização permanece apenas como possibilidade a avaliar.

Essa trilha não está ativa no ciclo de entrega GNOME. O escopo, a ordem das
etapas e a separação prevista dos repositórios estão em
[`kde-experimental-flavor.md`](kde-experimental-flavor.md).

## Lyra Enterprise Linux

Fica registrada a decisão de criar futuramente o **Lyra Enterprise Linux**
nas edições **Desktop** e **Server**, ambas baseadas no **SUSE Linux
Enterprise**. Esta decisão não altera o escopo nem a base dos ciclos atuais do
Lyra OS; planejamento, versões e cronograma serão definidos separadamente.

## Lyra OS Desktop Alpha 4 a Alpha 8

A Alpha 4 foi publicada em 14/08/2026 como snapshot antecipado da
infraestrutura de i18n, do Lyra Installer em `en-US`/`pt-BR`/`es-ES` e da
primeira onda de pacotes em `pt-BR`/`en-US`.

- **Alpha 5 (14–28/08) — estabilização e contratos:** corrige primeiro os
  bloqueadores herdados do instalador e do release e especifica o Lyra
  Upgrade. Para o ECA Digital, fecha enquadramento jurídico, auditoria da
  referência BigLinux, qualificação upstream, UX no Vega, ADR e baseline de
  governança LTS. Os três idiomas e o fluxo NVIDIA pelo Vega foram implementados; a
  qualificação na candidata atual, incluindo hardware, continua obrigatória.
- **Alpha 6 (28/08–11/09) — atualização e integração:** entrega o core,
  preflight, estado durável e serviço privilegiado do Lyra Upgrade para
  atualizações dentro da mesma release, com interface nos três idiomas,
  console sanitizado, recuperação e rollback. Integra também as novas telas do
  Welcome e a pilha ALSA explícita da imagem. O upgrade entre releases segue
  para a Alpha 7; o serviço parental permanece no ciclo atual, condicionado à
  revisão jurídica e à qualificação técnica.
- **Alpha 7 (11–25/09) — rebase e upgrade:** migra a base do Desktop
  para o openSUSE Leap 16.1 Beta 1 e requalifica pacotes, ABI, Secure
  Boot, instalação, atualização, rollback e hardware. Também conclui o fluxo
  controlado entre releases do Lyra Upgrade. O Desktop 1.1 não oferece
  suporte de produto a aplicativos Android ou Windows; essa trilha volta a ser
  avaliada somente em uma release futura definida pelo projeto. A integração parental só avança quando os
  gates jurídico e técnico do ciclo atual estiverem satisfeitos.
- **Alpha 8 (25/09–13/10) — gate e estabilização:** automatiza update, upgrade,
  reboot, rollback e a matriz do ECA Digital; não recebe feature nova e depois
  corrige somente defeitos até a decisão da Beta 1.

A Beta 1 não começa por calendário com P0/P1 ou entrega obrigatória pendente.
O Lyra OS 1.1 oferece somente inglês dos Estados Unidos (`en-US`), português
do Brasil (`pt-BR`) e espanhol da Espanha (`es-ES`), com `en-US` como padrão e fallback.
Os componentes próprios possuem catálogos e testes nos três idiomas. A
validação completa da ISO nos três idiomas deve ser registrada por candidata.
Outros idiomas entram apenas em ciclo futuro.

O gate da funcionalidade exige detecção conservadora de hardware compatível,
confirmação explícita, Secure Boot verificado, snapshot Snapper antes da
mudança, pacotes meta que mantenham KMP, userspace e firmware em lockstep,
`dracut`, reinício orientado e rollback documentado. O fluxo não pode ser
declarado suportado com um P1 aberto; a pendência da Alpha 4 fica registrada
explicitamente na Alpha 5.

## NVIDIA em uma única ISO Desktop

A ISO NVIDIA dedicada foi cancelada. A instalação opcional via Vega foi
concluída na Desktop Alpha 5 e é o único fluxo proprietário: detecção do
hardware real, confirmação, verificação de Secure Boot, snapshot Snapper,
pacotes KMP/userspace em lockstep, `dracut`, reinício, validação e rollback.
A implementação desse fluxo não substitui a qualificação do driver, suspensão,
monitor externo e rollback no hardware suportado da candidata atual.
As descobertas técnicas preservadas em [`nvidia-iso.md`](nvidia-iso.md) são
históricas e alimentam esse fluxo; não representam uma segunda imagem.

## Melhorias permitidas nas Betas da 1.1

A Desktop Beta 1 mantém 13/10/2026 como meta; Alpha 5, Alpha 6, Alpha 7 e
Alpha 8 continuam etapas obrigatórias do Desktop. Por decisão do mantenedor,
as Betas da 1.1 podem receber melhorias programadas quando o ganho esperado
compensar o risco. Cada mudança precisa de justificativa, análise de impacto,
testes de regressão e plano de reversão; os gates não são reduzidos para
cumprir calendário. A RC1 encerra essa exceção e inicia o congelamento estrito.

Correções de bugs, regressões, segurança, desempenho e traduções continuam
prioritárias. Melhorias não podem deixar P0/P1 aberto para a etapa seguinte.
Novos aplicativos e mudanças amplas de arquitetura ainda exigem decisão
explícita. A Beta 3 também faz QA linguístico e corrige catálogos.

A meta da versão estável, as entregas recentes e os critérios de saída estão em [política de versões](release-versioning.md), no [estado do GNOME](status-gnome.md)
e no [release gate](release-gate.md).

## Idiomas em ciclos futuros

A ampliação para outros idiomas começa somente depois da Lyra OS 1.1. A
infraestrutura criada na 1.0 deve aceitar novos catálogos com fallback para
`en-US`, mas isso não autoriza publicar traduções adicionais antes de uma
release futura que as qualifique.
Cada novo idioma terá inventário, revisão humana, fallback e gate linguístico
próprios antes de ser oferecido pelo instalador.
