# ADR 0009: a edição Server passa a viver em repositório próprio

- Estado: aceita
- Data: 2026-08-23
- Substitui: a decisão de 2026-08-11 registrada em `docs/server-edition.md`
  ("mesmo repositório Lyra, não um repositório novo")

## Contexto

Em 2026-08-11 o mantenedor decidiu manter a edição Server no mesmo
repositório do Desktop, reaproveitando `scripts/image-build.py`,
`release.py`, os testes e o `kiwi/config.xml` com profiles KIWI
(`desktop`/`server`) para diferenciar as duas imagens. Essa decisão foi
revertida em 2026-08-23: o mantenedor optou por separar as duas edições em
repositórios GitHub distintos.

## Decisão

A edição Server passa a viver em
[`lyra-os-linux/lyraos-server`](https://github.com/lyra-os-linux/lyraos-server),
com histórico git preservado para os arquivos que já eram exclusivos do
Server (overlay `kiwi/server/`, `scripts/server-*`, `image-build-server.toml`,
`release-server.toml`, `docs/server-edition.md`, notas de release do Server e
seus testes dedicados). Este repositório (Desktop) passou, na mesma data, a
viver em [`lyra-os-linux/lyraos-desktop`](https://github.com/lyra-os-linux/lyraos-desktop)
— ambos privados, sob o org GitHub `lyra-os-linux`.

O `kiwi/config.xml` deixou de usar o sistema de `<profiles>` do KIWI: cada
repositório agora tem seu próprio `config.xml` completo, sem o atributo
`profiles=`. O ferramental antes compartilhado (`scripts/image-build.py`,
`release.py`, `release-artifacts.py` e os testes que cobriam os dois perfis
lado a lado) foi duplicado nos dois repositórios em vez de extraído para um
terceiro repositório comum — decisão deliberada que aceita o risco de drift
entre os dois em troca de simplicidade; revisitar só se isso doer na
prática.

## Consequências

- Mudanças na base compartilhada (política de assinatura, evidência de
  release, versão do kernel, repositórios OBS) agora precisam ser replicadas
  manualmente nos dois repositórios quando aplicável a ambos.
- O ciclo de release do Server já era independente do Desktop
  (`release-server.toml` próprio, cadência própria); isso não muda.
- `installer/`, `upgrade/` e `welcome/` continuam exclusivos deste
  repositório — a edição Server nunca dependeu deles.
