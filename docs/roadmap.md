# Roadmap do Lyra OS

## Escopo ativo e evidência

O lançamento de 05/11/2026 é o Desktop GNOME 16.1, a única edição Desktop.
KDE Plasma e XFCE foram abandonados em 24/10/2026
([ADR 0018](adr/0018-abandon-kde-xfce.md)). A decisão de 16/09/2026 prevê uma única ISO GNOME,
sem NVIDIA pré-instalada, e instalação opcional pelo Vega GTK.
A [situação do GNOME](status-gnome.md) registra o que foi integrado e o que
continua pendente de qualificação. O estágio canônico está em `release.toml`.

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
  controlado entre releases do Lyra Upgrade. O Desktop 16.1 não oferece
  suporte de produto a aplicativos Android ou Windows; em 26/10/2026 essa
  trilha foi abandonada ([ADR 0020](adr/0020-abandon-android-windows.md)). A integração parental só avança quando os
  gates jurídico e técnico do ciclo atual estiverem satisfeitos.
- **Alpha 8 (publicação em 17/10, limite 30/10) — gate e estabilização:**
  plano fixo aprovado em 07/10 na [#28](https://github.com/lyra-os-linux/lyraos-desktop/issues/28):
  somente instalação nova (sem upgrade a partir da Alpha 7), testes só em VM,
  sem controle parental; gate com `i18n` e sem `hardware-matrix` nem
  `upgrade-rehearsal`; ECA Digital e congelamento funcional são declarações nas
  notas de versão. Não recebe feature nova, salvo exceção explícita do
  mantenedor; em 08/10 a paleta Lyra e o tema Lyra do Firefox viraram padrão da
  imagem. Em 07/10, o controle parental saiu do escopo devido à evasão Flatpak
  #102; nenhuma proteção parental é anunciada nessa candidata. Se a candidata
  falhar, candidata 2 em 22/10 e publicação em 27/10.
- **RC 1 (publicação até 31/10/2026) — candidata de lançamento:** por decisão
  do mantenedor em 14/10, o ciclo sai da Alpha 8 diretamente para a RC 1
  (`16.1-rc.1`), sem Beta. Mesmo gate da Alpha 8 mais a assinatura destacada do
  checksum (ADR 0005). Congelamento estrito: somente correções de bugs,
  travamentos, segurança e performance crítica; funcionalidades novas esperam
  a 16.2. Um defeito não trivial gera a RC 2. Publicada (`v16.1-rc.1`).
- **RC 2 (aberta em 24/10/2026):** o mantenedor levou à candidata o vegad
  5.1.39, com a zona correta no status do firewall (vegad#83) e o sinal
  `Snapshots.ClearProgress` na introspecção. Em 25/10 decidiu incluir também o
  controle parental básico (ADR 0019); como nenhuma ISO da RC 2 tinha sido
  publicada, ela traz esse recurso. Repete o gate da RC 1 mais o gate #9; um
  defeito não trivial gera a RC 3. Notas em
  [`releases/lyra-os-desktop-16.1-rc.2.md`](releases/lyra-os-desktop-16.1-rc.2.md).
- **RC 3 (decisão de 30/10/2026) — candidata final:** sai antecipada, com o
  Vega 5.8.0 (diagnóstico de saúde, segurança, Liberar espaço, rede, boot,
  Pedir ajuda e verificação semanal, como exceção ao congelamento aprovada
  pelo mantenedor), a Welcome 0.5.0 e as correções acumuladas. Repete o gate
  da RC 2. Notas em
  [`releases/lyra-os-desktop-16.1-rc.3.md`](releases/lyra-os-desktop-16.1-rc.3.md).
- **16.1 estável (19/11/2026):** a mesma ISO da RC 3, congelada e promovida
  por tag, sem rebuild; as atualizações do Leap 16.1 GA chegam pelo
  repositório `update`.

A Beta 1 não começa por calendário com P0/P1 ou entrega obrigatória pendente.
O Lyra OS 16.1 oferece somente inglês dos Estados Unidos (`en-US`), português
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

## ISO GNOME única e cronograma independente

Em 16/09/2026, o mantenedor retirou a variante Desktop com NVIDIA pré-instalada.
A entrega é uma ISO GNOME única, com NVIDIA opcional após instalar o sistema
pelo Vega GTK. A construção/qualificação continua em
[#63](https://github.com/lyra-os-linux/lyraos-desktop/issues/63) e
[#56](https://github.com/lyra-os-linux/lyraos-desktop/issues/56).
O [plano NVIDIA](nvidia-iso.md) registra dependências e limites.

O conjunto escolhido usa RPMs oficiais NVIDIA, KMP assinado SUSE e integração
`lyra-nvidia` no OBS. Acompanhar versões, segurança e compatibilidade em
[#82](https://github.com/lyra-os-linux/lyraos-desktop/issues/82); a decisão de
15/09 substituiu a espera por correção do conjunto antigo até a RC1. O cronograma
do Lyra permanece independente do Leap. Nenhuma data dispensa os gates.

Sequência: issues de implementação/correção GNOME → auditoria #78 → construção
e testes locais da ISO única → Alpha 8 após os gates. A auditoria ampla está
adiada. Retirar a segunda imagem não elimina testes NVIDIA de instalação,
Secure Boot, atualização, hardware ou recuperação. O Server com llama.cpp +
NVIDIA permanece em seu planejamento próprio (Server #21).

## Melhorias permitidas nas Betas da 16.1

Por decisão do mantenedor em 14/10/2026, o Desktop 16.1 (antes numerado 1.1)
não terá estágio Beta:
a candidata seguinte à Alpha 8 é a RC 1, publicada até 31/10/2026. A exceção
que autorizava melhorias programadas nas Betas da 16.1 está encerrada; desde a
RC 1 vale o congelamento estrito, e os gates não são reduzidos para cumprir
calendário.

Correções de bugs, regressões, segurança, desempenho e traduções continuam
prioritárias. Melhorias não podem deixar P0/P1 aberto para a etapa seguinte.
Novos aplicativos e mudanças amplas de arquitetura ainda exigem decisão
explícita. A Beta 3 também faz QA linguístico e corrige catálogos.

A meta da versão estável, as entregas recentes e os critérios de saída estão em [política de versões](release-versioning.md), no [estado do GNOME](status-gnome.md)
e no [release gate](release-gate.md).

## Idiomas em ciclos futuros

A ampliação para outros idiomas começa somente depois da Lyra OS 16.1. A
infraestrutura criada na 1.0 deve aceitar novos catálogos com fallback para
`en-US`, mas isso não autoriza publicar traduções adicionais antes de uma
release futura que as qualifique.
Cada novo idioma terá inventário, revisão humana, fallback e gate linguístico
próprios antes de ser oferecido pelo instalador.
