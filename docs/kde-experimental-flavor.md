# Flavor KDE experimental

## Status e relação com a edição oficial

O Lyra OS terá futuramente um flavor KDE experimental. A edição Desktop com
GNOME continua sendo a edição oficial, recomendada e responsável pelos gates
completos de produto do Lyra OS. O flavor KDE não substitui a edição GNOME,
não altera o escopo da versão 1.1 e terá ciclo, artefatos e expectativas de
suporte próprios.

O objetivo inicial não é reproduzir no Plasma todas as integrações existentes
no GNOME. O flavor deve começar pequeno, próximo do openSUSE e ganhar
componentes do Lyra gradualmente, somente depois que a etapa anterior estiver
funcional.

## Sequência de desenvolvimento

### Alpha 1 — somente KDE

A primeira Alpha serve para validar o KDE Plasma sobre a base escolhida pelo
Lyra OS. Ela usa somente pacotes fornecidos pelos repositórios da base e não
inclui nenhum pacote desenvolvido pelo projeto Lyra.

O escopo inclui:

- openSUSE Leap e a pilha KDE Plasma disponível na base;
- SDDM e uma sessão Plasma com os padrões upstream;
- rede, áudio, Bluetooth, vídeo e armazenamento da base;
- aplicativos KDE e demais aplicativos selecionados diretamente dos
  repositórios upstream;
- construção e inicialização da imagem experimental.

O escopo não inclui:

- tema ou wallpapers do Lyra;
- Vega, seja GTK ou Qt;
- Welcome;
- Sheliak ou uma substituição KDE;
- Fina, Beam, Sulafat, Fish personalizado ou outros pacotes próprios;
- paridade visual ou funcional com a edição GNOME oficial.

A condição de imagem somente live ou instalável será decidida durante o
planejamento desta Alpha. A decisão não deve introduzir silenciosamente um
pacote próprio ou um instalador temporário apenas para antecipar a instalação.

### Alpha 2 — wallpapers

Depois que a imagem KDE básica estiver funcional, a etapa seguinte adiciona
os wallpapers e a identidade visual mínima do Lyra. O Plasma e seu layout
continuam próximos dos padrões upstream; não há compromisso inicial de criar
painel, widgets, decoração de janelas ou experiência equivalente à edição
GNOME.

O suporte KDE do tema será mantido em um repositório próprio, derivado por
duplicação do projeto de tema quando esta etapa começar. O pacote GNOME
existente não será transformado em um pacote híbrido com condicionais para os
dois desktops.

### Alpha 3 — Vega Qt

Somente depois da etapa de wallpapers será iniciado um Vega nativo em Qt para
o flavor KDE. Ele será mantido em um repositório próprio, criado por duplicação
do projeto Vega para permitir que interface, dependências, integração com o
Plasma e ritmo de desenvolvimento evoluam independentemente da edição GNOME.

O primeiro Alpha KDE não inclui `vega-gtk` como solução provisória. A
arquitetura e o grau de compartilhamento futuro entre o Vega GTK e o Vega Qt,
inclusive daemon e contratos D-Bus, serão decididos quando a etapa Qt for
planejada; não constituem requisito para criar a imagem KDE básica.

## Componentes deliberadamente adiados

O flavor não terá Welcome. Um componente próprio de atualização poderá ser
incluído futuramente, mas ainda não é uma entrega confirmada. Até essa decisão,
o planejamento deve considerar os mecanismos de atualização fornecidos pela
base e não prometer uma interface Lyra de atualização no KDE.

Também ficam fora do escopo inicial:

- personalização profunda do Plasma ou do SDDM;
- port de Sheliak;
- conjunto completo de aplicativos do ecossistema Lyra;
- paridade de suporte, hardware e release com a edição GNOME;
- compromisso de data para promoção a flavor estável.

## Separação dos projetos

A direção planejada é manter projetos distintos para a imagem, o tema KDE e o
Vega Qt, sem modificar o papel dos repositórios usados pela edição oficial:

```text
lyraos-desktop          edição GNOME oficial
lyraos-desktop-kde      imagem do flavor KDE experimental
lyraos-desktop-kde-theme identidade visual e wallpapers do flavor KDE
vega-qt                  interface Qt do Vega
```

Os nomes definitivos dos pacotes serão escolhidos quando cada etapa começar. A
separação deve deixar claro para usuários e mantenedores que o flavor KDE é
experimental e que sua evolução não bloqueia releases da edição GNOME.
