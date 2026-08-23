# ADR 0010: o Lyra Welcome passa a viver em repositório próprio

- Estado: aceita
- Data: 2026-08-23
- Relacionada: [ADR 0009](0009-server-edition-own-repository.md), que já
  havia registrado `welcome/` como exclusivo deste repositório (Desktop) na
  época da separação do Server — este ADR reverte esse ponto específico.

## Contexto

O Lyra Welcome (`welcome/`) era um app Rust/Tauri completo, com LICENSE e
README próprios, vivendo como subdiretório deste repositório. O mantenedor
decidiu extraí-lo para um repositório GitHub próprio, seguindo o mesmo
padrão já usado para a edição Server (ADR 0009).

## Decisão

O Lyra Welcome passa a viver em
[`lyra-os-linux/lyraos-desktop-welcome`](https://github.com/lyra-os-linux/lyraos-desktop-welcome),
com histórico git preservado via `git filter-repo` para todo o conteúdo de
`welcome/` e para `tests/test_welcome.py`. No novo repositório, o conteúdo
de `welcome/` passou a viver na raiz (não em um subdiretório), o que exigiu
ajustar `tests/test_welcome.py` (`WELCOME = ROOT`) e
`packaging/make-obs-sources.sh` (arquiva o commit inteiro em vez de
`$COMMIT:welcome`, e lê a versão a partir da raiz do repositório).

Neste repositório (Desktop), `welcome/` e `tests/test_welcome.py` foram
removidos, e `kiwi/test/build-and-run-vm.sh` perdeu o modo
`--published-welcome` / compilação local do Welcome: a VM de teste agora
sempre usa o RPM `lyra-welcome` publicado no OBS, do mesmo jeito que já
acontecia para o Server. O pacote `lyra-welcome` continua listado em
`obs/projects.toml` sob o mesmo projeto OBS — a origem do código muda, a
publicação não.

## Consequências

- Mudar o Welcome deixa de ser possível num único commit junto com o
  Desktop; passa a exigir um PR no novo repositório e, quando aplicável,
  esperar a próxima publicação do RPM no OBS antes de validar em
  `kiwi/test/build-and-run-vm.sh`.
- `installer/` e `upgrade/` continuam exclusivos deste repositório — apenas
  o Welcome saiu, o restante da ADR 0009 permanece válido.
