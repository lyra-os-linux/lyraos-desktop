# Versionamento de releases do Lyra OS

## Política oficial

Desde a decisão do mantenedor em 13/10/2026, a versão do Lyra OS segue a
versão do openSUSE Leap usado como base: o Lyra OS construído sobre o Leap
`16.1` é o Lyra OS `16.1`. O formato é `MAJOR.MINOR[.PATCH]`.

- `MAJOR.MINOR`: idêntico ao Leap base (`16.1`, `16.2`, ...);
- `PATCH`: correção, manutenção ou respin da mesma release, de uso
  exclusivo do Lyra (o Leap não tem patch level).

Uma versão nova do Leap determina a próxima versão minor do Lyra. Datas
pertencem ao roadmap ou ao `BUILD_ID`, nunca à versão comercial.

Até 18/10/2026 o Desktop e o Server eram numerados `1.1`, com versionamento
independente do Leap. Nenhum artefato `1.1-rc.1` ou `1.1` estável foi
publicado; o ciclo que estava em RC foi renumerado para `16.1` antes da
primeira candidata assinada. Tags, ISOs e notas `1.1-alpha.*` já publicadas
permanecem como registro histórico e não são renomeadas.

## Geração atual

- geração: **Lyra OS 16 — Odisseia**;
- primeira versão estável planejada: **Lyra OS 16.1 — Odisseia**;
- base tecnológica da 16.1: **openSUSE Leap 16.1**;
- arquitetura inicial: **x86_64**.

O codename identifica toda a geração: qualquer release `16.x` continua sendo
Odisseia. Desktop e Server compartilham essa identidade, embora possuam gates e
ciclos de publicação independentes (o Server usa o codinome Delos).

## Pré-releases

| Comunicação | Identificador técnico |
|---|---|
| Lyra OS 16.1 Alpha 1 | `16.1-alpha.1` |
| Lyra OS 16.1 Beta 1 | `16.1-beta.1` |
| Lyra OS 16.1 RC1 | `16.1-rc.1` |
| Lyra OS 16.1 | `16.1` |

O ciclo 16.1 do Desktop vai da Alpha 8 (publicada como `1.1-alpha.8`)
diretamente para a `16.1-rc.1`, sem Beta.

## Fonte canônica e metadados

`release.toml` separa versão, estágio, geração, base e identidade do artefato.
`scripts/release.py render` deriva o KIWI, a interface do instalador e
`/usr/lib/lyra-os/release`; arquivos gerados não devem ser editados à mão.
O RPM `lyra-release` (`packaging/lyra-release/`) carrega a mesma versão em
`/usr/lib/lyra-os/product-release` e deve ser publicado antes de uma imagem
que a anuncie.

`VERSION_ID` contém a versão do produto, `VERSION_CODENAME` contém
`odisseia`, `BUILD_ID` identifica a data do build e `IMAGE_VERSION`
identifica a candidata completa. `LYRA_BASE_VERSION_ID` conserva a versão do
Leap base, que coincide com `MAJOR.MINOR` do Lyra.

ISOs usam `LyraOS-Desktop-16.1-rc.1-x86_64.iso` em candidatas e
`LyraOS-Desktop-16.1-x86_64.iso` na release estável.

## Compatibilidade, promoção e suporte

Tags, evidências e release notes já publicados com versões calendário ou com o
esquema `1.x` continuam como registros históricos. O upgrade deve aceitá-los
somente como origens legadas explícitas; nenhuma candidata nova usa os
esquemas antigos. O Lyra Upgrade aceita a transição `1.1` → `16.1` porque a
versão de destino é maior que a de origem.

Uma versão é publicada quando passa pelos critérios de qualidade, não porque uma
data chegou. O suporte da base openSUSE, o suporte de uma release Lyra e o ciclo
da geração 16.x são distintos. Não há promessa de EOL ou suporte prolongado do
Lyra sem política formal e sustentável.

O Lyra OS 16.1 terá suporte comunitário, sem prazo contratual ou EOL prometido.
O lançamento está previsto para **5 de novembro de 2026**, sempre condicionado
ao gate completo. Artefatos legados serão preservados e republicados com nomes
semânticos, mantendo checksums, assinaturas e proveniência verificáveis.
