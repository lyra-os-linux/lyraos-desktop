# ADR 0012: o empacotamento do LinuxToys passa a viver em repositório próprio

- Estado: aceita
- Data: 2026-08-23
- Relacionada: [ADR 0009](0009-server-edition-own-repository.md),
  [ADR 0010](0010-welcome-own-repository.md) e
  [ADR 0011](0011-upgrade-own-repository.md), que registraram o mesmo
  padrão de extração para outros componentes.

## Contexto

Diferente do Welcome e do Upgrade, `packaging/linuxtoys/` nunca foi
código-fonte do Lyra: é só a definição do pacote RPM que reempacota o
[LinuxToys](https://linux.toys/), projeto de terceiros, para os
repositórios OBS assinados do Lyra — um `_service` que baixa e verifica o
tarball de release do GitHub upstream, o `.spec`, um patch que desativa o
auto-update embutido do LinuxToys e um changelog. Cinco arquivos, dois
commits de histórico. O mantenedor decidiu extrair esse empacotamento para
um repositório GitHub próprio, seguindo o mesmo padrão do Welcome e do
Upgrade.

## Decisão

O empacotamento do LinuxToys passa a viver em
[`lyra-os-linux/lyraos-desktop-linuxtoys`](https://github.com/lyra-os-linux/lyraos-desktop-linuxtoys),
com histórico git preservado via `git filter-repo` e o conteúdo de
`packaging/linuxtoys/` movido para a raiz do novo repositório. Diferente do
Welcome e do Upgrade, não havia script de build próprio nem dependência de
`LICENSE` deste repositório — o `_service` do OBS busca o tarball e a
licença do upstream diretamente, sem tocar em nada deste repositório — então
a extração não exigiu reescrever nenhum caminho relativo. Foram adicionados
um README (o diretório original não tinha um, por viver dentro de um
repositório maior) e um `.gitignore` mínimos, e a checagem de contrato que
vivia embutida em `tests/test_image_build.py` (que o `.spec` mantém
`Requires: git` e a mensagem de erro do `%check`, e que o patch mantém a
mensagem de auto-update desativado) virou seu próprio teste no novo
repositório.

Neste repositório (Desktop), `packaging/linuxtoys/` e essas três asserções
foram removidos. `obs/projects.toml` e `kiwi/config.xml` não mudam: o
pacote `linuxtoys` continua no mesmo projeto OBS e na mesma imagem — a
origem do empacotamento muda, a publicação não.

## Consequências

- Atualizar a versão do LinuxToys ou revisar o patch de auto-update deixa
  de ser possível num único commit junto com o Desktop; passa a exigir um
  PR no novo repositório.
- `installer/` continua exclusivo deste repositório; `packaging/` ainda
  guarda `lyra-fish-productivity`, que não foi tocado por esta decisão.
