# ADR 0020: abandonar a compatibilidade com aplicativos Android e Windows

- Estado: aceita
- Data: 2026-10-26
- Substitui: [ADR 0016](0016-defer-android-windows-next-release.md)

## Contexto

A [ADR 0015](0015-optional-android-windows-compatibility.md) tratou Android e
Windows como recursos opcionais, fora da ISO, com um piloto de Bottles. A
[ADR 0016](0016-defer-android-windows-next-release.md) retirou o tema do ciclo
16.1 e o deixou para uma release futura, com as issues #14 a #19 abertas.

O Lyra é uma distribuição pequena e cuidadosa. A avaliação de 2026 mostrou o
custo do tema: Bottles em Flatpak pede permissões amplas, o Waydroid não tem
alvo mantido para o Leap 16.1 nem cadeia de imagem Android homologada, e cada
camada traria runtimes, permissões e matrizes de compatibilidade para manter
a longo prazo.

## Decisão

Em 26/10/2026 o mantenedor abandonou a compatibilidade com aplicativos Android
e Windows. O Lyra OS não terá suporte de produto a esses aplicativos em nenhuma
release planejada:

- nenhum empacotamento de runtimes, Bottles, Wine ou Waydroid pelo Lyra;
- nenhuma integração no Vega nem associação de `.exe`, `.msi` ou `.apk`;
- as issues #14 a #19 foram fechadas como fora do escopo;
- o coletor de evidências do piloto de Bottles
  (`scripts/bottles-pilot-evidence.py`) e seu teste saem do repositório.

Quem quiser usar Wine, Bottles ou Waydroid pode instalá-los por conta própria,
pelos repositórios do openSUSE ou pelo Flathub, sem suporte do Lyra.

## Consequências

- O tema só volta com uma nova ADR, que repita a avaliação de base,
  permissões, supply chain e manutenção.
- As ADRs 0015 e 0016 ficam como registro histórico das avaliações.
