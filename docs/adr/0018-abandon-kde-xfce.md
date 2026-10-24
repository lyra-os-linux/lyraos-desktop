# ADR 0018: abandonar as edições KDE Plasma e XFCE

- Estado: aceita
- Data: 2026-10-24
- Substitui: [ADR 0017](0017-resume-kde-xfce-without-date.md)

## Contexto

A [ADR 0017](0017-resume-kde-xfce-without-date.md) retomou KDE Plasma e XFCE
em 23/10/2026, com lançamento sem data e direto na 16.1 RC 1. As duas edições
abriram a RC 1, mas nenhuma ISO chegou a ser construída ou qualificada. O
Desktop GNOME 16.1 está em RC, com publicação estável prevista para
05/11/2026.

## Decisão

Em 24/10/2026 o mantenedor abandonou as edições KDE Plasma e XFCE. O Lyra OS
Desktop passa a ter uma única edição, a GNOME.

- Os repositórios `lyraos-desktop-kde`, `lyraos-desktop-xfce`, `vega-qt`,
  `vega-xfce`, `lyraos-desktop-kde-theme` e `lyraos-desktop-xfce-theme` são
  arquivados no GitHub, em modo somente leitura, e saem do catálogo do
  `lyra-ecosystem`.
- Os pacotes `vega-qt` e `vega-xfce` são removidos dos projetos OBS
  `home:rodrigosbrito:vega` e `home:rodrigosbrito:vega:staging`. A ISO GNOME
  não instala nenhum dos dois.
- Retomar qualquer uma dessas edições exige uma nova decisão.

## Consequências

- `obs/projects.toml`, o inventário de i18n e seus testes deixam de listar
  `vega-qt` e `vega-xfce`.
- READMEs, roadmap e documentação viva deixam de mencionar as edições como
  planejadas ou retomadas. ADRs, handoffs e evidências anteriores ficam como
  registro histórico.
- Componentes comuns (instalador, atualizador, `vegad`, contrato D-Bus, temas e
  ícones) não precisam mais preservar compatibilidade com KDE ou XFCE. As
  proteções que impedem o tema e os ícones de alterar sessões de outros
  ambientes continuam valendo. Qualquer limpeza de código motivada por esta
  decisão espera a publicação do GNOME 16.1 e segue as regras de RC até lá.
