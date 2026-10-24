# Foco de desenvolvimento: GNOME

> [!NOTE]
> Substituída em 23/10/2026 pela
> [ADR 0017](adr/0017-resume-kde-xfce-without-date.md), que retomou KDE Plasma e
> XFCE, e depois pela [ADR 0018](adr/0018-abandon-kde-xfce.md), que os abandonou
> em 24/10/2026. Este texto fica como registro da decisão de 11/09.

Decisão do mantenedor em 11 de setembro de 2026: a partir desta data, o trabalho
ativo de desenvolvimento, integração, validação e publicação de pacotes será
restrito ao GNOME e aos componentes comuns necessários a essa edição.

KDE, XFCE, Vega Qt, Vega XFCE e integrações específicas dessas variantes ficam
pausados. Esta decisão substitui a orientação anterior de GNOME prioritário
com KDE/XFCE em segundo plano. Retomar essas variantes exige uma nova decisão
do mantenedor.

Os componentes comuns continuam elegíveis quando necessários ao GNOME: por
exemplo, instalador, atualizador, daemon Vega, temas, ícones e bibliotecas
compartilhadas. Sua manutenção não implica retomar interfaces específicas de
outros ambientes. O catálogo OBS continua descrevendo os pacotes existentes;
a presença de uma variante no inventário não autoriza novas promoções dela.

Pacotes e publicações existentes de outras variantes permanecem preservados.
A decisão não pede sua remoção, desinstalação ou substituição automática.

A próxima imagem GNOME deve incorporar as correções atuais, os perfis Lyra
Clássico/Central/Flutuante e as seis extensões do pacote Sheliak, incluindo Lyra
Desktop Icons. Veja a [integração e qualificação](desktop-icons-and-macos.md).
