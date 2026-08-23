# ADR 0011: o Lyra Upgrade passa a viver em repositório próprio

- Estado: aceita
- Data: 2026-08-23
- Relacionada: [ADR 0009](0009-server-edition-own-repository.md) e
  [ADR 0010](0010-welcome-own-repository.md), que registravam `upgrade/`
  como exclusivo deste repositório (Desktop) — este ADR reverte esse ponto
  específico. As decisões de arquitetura do próprio Lyra Upgrade (ADR 0007)
  permanecem aqui, junto ao restante do histórico de decisões do projeto.

## Contexto

O Lyra Upgrade (`upgrade/`) era um workspace Rust completo vivendo como
subdiretório deste repositório. O mantenedor decidiu extraí-lo para um
repositório GitHub próprio, seguindo o mesmo padrão já usado para a edição
Server (ADR 0009) e para o Welcome (ADR 0010).

## Decisão

O Lyra Upgrade passa a viver em
[`lyra-os-linux/lyraos-desktop-updater`](https://github.com/lyra-os-linux/lyraos-desktop-updater),
com histórico git preservado via `git filter-repo` para todo o conteúdo de
`upgrade/`, para `tests/test_upgrade_packaging.py` e
`tests/test_upgrade_ui.py`, para os dois contratos normativos que só o
Lyra Upgrade referenciava (`docs/lyra-upgrade-architecture.md` e
`docs/lyra-upgrade-state-machine.md`), e para o `LICENSE` deste repositório
(o Lyra Upgrade não tinha cópia própria; passou a ter uma no novo
repositório). No novo repositório, o conteúdo de `upgrade/` passou a viver
na raiz, o que exigiu ajustar `Cargo.toml` (URL do `repository`),
`README.md` (links de doc e comando de teste), os dois arquivos de teste
migrados e `packaging/make-obs-sources.sh` (arquiva o commit inteiro em vez
de `$COMMIT:upgrade`, e lê versão e lockfile a partir da raiz do
repositório).

`docs/release-signing-key.asc` **não** foi movido: é a chave canônica de
assinatura de release do Lyra OS, documentada em `docs/release-gate.md` e
na ADR 0005, e usada mais amplamente do que só pelo Lyra Upgrade. Ela foi
duplicada no novo repositório (mesma decisão deliberada já registrada na
ADR 0009 para o ferramental compartilhado entre Desktop e Server: aceitar o
risco de drift entre cópias em troca de simplicidade, sem extrair para um
terceiro repositório comum).

Neste repositório (Desktop), `upgrade/`, os dois arquivos de teste e os
dois contratos normativos foram removidos, e `/upgrade/packaging/output/`
saiu do `.gitignore`. O pacote `lyra-upgrade` continua listado em
`obs/projects.toml` sob o mesmo projeto OBS — a origem do código muda, a
publicação não. Diferente do instalador e do Welcome,
`kiwi/test/build-and-run-vm.sh` nunca teve um modo de compilação local do
Lyra Upgrade, então nada precisou mudar lá.

## Consequências

- Mudar o Lyra Upgrade deixa de ser possível num único commit junto com o
  Desktop; passa a exigir um PR no novo repositório.
- `docs/release-signing-key.asc` agora existe em dois repositórios; uma
  rotação de chave precisa atualizar os dois manualmente.
- `installer/` continua exclusivo deste repositório — só o Welcome e o
  Upgrade saíram; o restante das ADRs 0009 e 0010 permanece válido.
