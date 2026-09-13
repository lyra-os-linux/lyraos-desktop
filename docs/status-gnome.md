# Situação do GNOME — 12/09/2026

Este é um registro datado de implementação e qualificação, não uma declaração
de release aprovada. `release.toml` continua identificando **Lyra OS 1.1 Alpha 7
(Odisseia)**, baseado no Leap 16.1, x86_64.

## Escopo confirmado

- GNOME é o único alvo da versão final 1.1; trabalho atual em pacotes GNOME.
- KDE e XFCE ficam em segundo plano, sem prazo conjunto ou promessa de paridade.
- Uma única ISO Desktop; NVIDIA opcional após instalar, pelo Vega.
- Pacotes próprios em RPM no OBS; ISO construída localmente com KIWI.
- PT-BR, EN-US e ES-ES nas interfaces próprias; inglês como padrão e fallback.
- Sheliak é o repositório/pacote de seis extensões, não uma extensão monolítica.
  Lyra Desktop Icons faz parte desse pacote e preserva a origem/licenças DING.
- Os perfis visíveis são Lyra, Ubuntu, GNOME Vanilla, Lyra Clássico, Lyra Central
  e Lyra Flutuante. IDs legados são mantidos para preservar preferências.

## Implementação e pacotes

| Entrega | Evidência | Limite da evidência |
| --- | --- | --- |
| Suíte Sheliak 2.0.1, migração no login e busca após menus | [PR 31](https://github.com/lyra-os-linux/lyraos-desktop-sheliak/pull/31), CI e GNOME descartável; staging rev21 | Novo login automático e ISO atual ainda precisam de qualificação. |
| Vega GTK 5.1.37, componentes após perfis e limpeza das configurações | [PR 140](https://github.com/lyra-os-linux/vega/pull/140), [PR 141](https://github.com/lyra-os-linux/vega/pull/141), CI; staging rev19 | Ajustes dependentes de componente/perfil e reorganização das páginas continuam pendentes na auditoria. |
| Welcome 0.4.1, nomes dos perfis e integração com Vega | [PR 7](https://github.com/lyra-os-linux/lyraos-desktop-welcome/pull/7); staging rev12 | A presença do pacote não comprova a experiência do primeiro boot da nova ISO. |
| Receita GNOME com seis UUIDs e versões mínimas | [PR 75](https://github.com/lyra-os-linux/lyraos-desktop/pull/75), [PR 76](https://github.com/lyra-os-linux/lyraos-desktop/pull/76), [PR 77](https://github.com/lyra-os-linux/lyraos-desktop/pull/77) | Receita integrada não significa ISO construída ou homologada. |

O envio ao staging foi confirmado. Este registro não afirma que o build de
cada revisão terminou ou que o conjunto foi promovido ao release. Prévia RPM
local e aceitação visual na estação do mantenedor são evidências adicionais,
com escopo diferente dos RPMs assinados e da candidata distribuída.

A marca d'água do Nautilus também depende da integração com a suíte: o módulo
antigo exigia o UUID monolítico. A correção 1.9.4 está na
[PR 16](https://github.com/lyra-os-linux/lyraos-desktop-theme/pull/16), com testes
no Nautilus real em escalas 1 e 2. Ela deve integrar a próxima candidata junto
das versões coordenadas em
[desktop-icons-and-macos.md](desktop-icons-and-macos.md).

## Qualificação que ainda falta para a candidata atual

1. Conferir os RPMs assinados, revisões, proveniência e publicação no canal de
   release; manter evidência do conjunto exato consumido pela ISO.
2. Construir a ISO localmente e registrar commit, inventário e checksum.
3. Validar live, instalação, primeiro login automático e conta nova.
4. Repetir os cenários de perfis, desktop, idiomas, monitores e acessibilidade
   sobre essa candidata.
5. Executar hardware, energia/suspensão, atualização, reboot e rollback,
   incluindo cenários NVIDIA suportados.
6. Aplicar todos os critérios do [release gate](release-gate.md).

A [qualificação GNOME](https://github.com/lyra-os-linux/lyraos-desktop/issues/56),
o [roteiro de hardware](https://github.com/lyra-os-linux/lyraos-desktop/issues/69)
e o [ensaio de atualização/rollback](https://github.com/lyra-os-linux/lyraos-desktop/issues/24)
organizam esse trabalho. Checklists antigos devem ser conciliados com as
respectivas evidências antes de serem encerrados. Títulos antigos sobre duas
ISOs, três edições simultâneas ou versões calendário não alteram o escopo acima.

A nova [rodada de auditoria #78](https://github.com/lyra-os-linux/lyraos-desktop/issues/78)
consolida integração entre pacotes, configurações, ciclo de atualização,
hardware, idiomas, documentação e critérios de encerramento dos achados.

Atualização em 13/09: a [primeira etapa da auditoria](audits/2026-09-13-gnome-integration.md)
registrou o inventário e confirmou o autostart da suíte no novo login pessoal.
Também corrigiu a exigência indevida do frontend opcional `vega-cli` no
verificador da ISO. A qualificação da nova candidata permanece pendente.

## Ordem de trabalho

Concluir a integração e as correções identificadas, consolidar a candidata e
concentrar a validação no ciclo completo de uso. Novas funcionalidades exigem
análise de impacto e seguem os limites de Alpha/Beta/RC; nenhum cronograma
substitui os critérios de qualidade. Datas vigentes ficam na
[política de versões](release-versioning.md) e no [roadmap](roadmap.md).
