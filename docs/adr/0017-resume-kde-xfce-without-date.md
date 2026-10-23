# ADR 0017: retomar KDE Plasma e XFCE com lançamento sem data

- Estado: aceita
- Data: 2026-10-23
- Substitui: a decisão de foco exclusivo no GNOME de 11/09/2026
  ([docs/gnome-focus.md](../gnome-focus.md))
- Relacionadas: [lyraos-desktop-kde#1](https://github.com/lyra-os-linux/lyraos-desktop-kde/issues/1)
  e [lyraos-desktop-xfce#1](https://github.com/lyra-os-linux/lyraos-desktop-xfce/issues/1)

## Contexto

Em 11/09/2026 o mantenedor restringiu o trabalho ativo ao GNOME e pausou KDE,
XFCE, Vega Qt, Vega XFCE e as integrações específicas dessas variantes. Retomá-las
exigia uma nova decisão. As edições KDE e XFCE pararam na Alpha 7, e seus
repositórios ainda descreviam uma estabilização conjunta das três edições até
28/09/2026, prazo que já passou.

O Desktop GNOME 16.1 está em RC, com publicação estável prevista para
05/11/2026.

## Decisão

KDE Plasma e XFCE são retomados. Cada edição será lançada **quando estiver
pronta, sem data definida**.

- O desenvolvimento recomeça a partir da Alpha 7 de cada edição e percorre
  Alpha, Beta e RC com os mesmos critérios e gates da edição GNOME. Nenhuma
  promoção acontece por data.
- Vega Qt, Vega XFCE e as identidades visuais KDE e XFCE voltam a ser trabalho
  ativo na medida em que essas edições precisarem deles.
- O GNOME 16.1 segue seu próprio cronograma e não espera pelas outras edições.
  Não há paridade de recursos prometida nem lançamento conjunto.
- Até a publicação estável do GNOME 16.1, mudanças em componentes comuns
  (instalador, atualizador, `vegad`, contrato D-Bus, temas, ícones) motivadas
  por KDE ou XFCE seguem as regras de RC do GNOME: só correções de bugs,
  travamentos, segurança e performance crítica.

## Consequências

- Os READMEs, o roadmap e os registros de escopo deixam de descrever KDE e XFCE
  como pausados ou em segundo plano.
- `docs/gnome-focus.md` e `docs/status-gnome.md` permanecem como registros
  datados; cada um aponta para esta ADR.
- O catálogo do `lyra-ecosystem` continua registrando as duas edições e seus
  consumidores; a retomada não altera contratos.
- Componentes comuns precisam continuar funcionando nas três edições. Quando um
  ajuste servir só a KDE ou XFCE e não couber nas regras de RC do GNOME, ele
  espera a publicação do GNOME 16.1.
