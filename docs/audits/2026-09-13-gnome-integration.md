# Auditoria GNOME — inventário e integração, 13/09/2026

Primeira etapa da [auditoria #78](https://github.com/lyra-os-linux/lyraos-desktop/issues/78).
Escopo: fontes integradas, pacotes da estação do mantenedor, início da sessão
e contrato de seleção da próxima ISO. Esta etapa não qualifica uma ISO nova.

## Baseline e proveniência

Receita inicial: `65c6691bd98e03dc15e41e6bf62344dd30186a73`.
Identidade: Lyra OS 1.1 Alpha 7 (Odisseia), Leap 16.1, x86_64.
A estação mantém `BUILD_ID=20260903`; instalar prévias não altera a identidade
da imagem originalmente instalada.

| Componente | Versão instalada | Evidência de fonte enviada em 12/09 |
| --- | --- | --- |
| Vega GTK | 5.1.37-0.local1 | staging Vega rev19, srcmd5 `b392ee867a1f1c88128b394abad05f3a` |
| Sheliak | 2.0.1-0.local1 | staging Lyra rev21, srcmd5 `9d2d21c42430763a7263b3e223efa114` |
| Welcome | 0.4.1-0.local1 | staging Lyra rev12, srcmd5 `4f51ec8e638d8d2142891f996d30dfe6` |
| Nautilus branding | 1.9.4-0.local1 | staging Lyra rev2, srcmd5 `3c6d3e16d33acda78c939da798fda4fb` |
| vegad | 5.1.26-lp161.1.1 | inventário RPM local; não houve promoção nesta etapa |
| GNOME Shell / Nautilus | 48.8 / 48.7 | pacotes da base instalados |

Os quatro primeiros são prévias locais, não os binários assinados produzidos
pelo OBS. Os recibos acima são evidência do envio anterior, sem acompanhamento
de builds nesta rodada. O inventário local registra cabeçalhos RPM, manifestos
com hashes e os arquivos instalados das seis extensões; `rpm -V` dos quatro
pacotes de prévia passou. Isso não substitui a qualificação dos RPMs de release.

## Consumidores da suíte

| Consumidor | Contrato revisado | Resultado e limite |
| --- | --- | --- |
| Vega GTK | Descoberta do Dock, schema compartilhado e helper `shell-suite`, API 1 | Caminho atual usa a suíte; UUIDs antigos permanecem no caminho de compatibilidade. Sem retirada indiscriminada de schemas/IDs persistidos. |
| Welcome | Comandos de perfil delegados ao Vega GTK | Não altera diretamente a lista de extensões; RPM exige Vega GTK >=5.1.35 e Sheliak >=2.0.0. A ISO exige as correções posteriores coordenadas. |
| Nautilus branding | Cinco UUIDs Shell e UUID legado | 1.9.4 reconhece a suíte; LDI sozinho não ativa a marca em Vanilla. A validação nativa é a evidência anterior da PR 16, não um novo ensaio nesta rodada. |
| Sheliak/autostart | Seis diretórios, helper sem privilégio e `migrate --wait-for-shell` | Payload instalado compatível com API 1/GNOME 48; serviço executou no novo login pessoal. |
| Receita KIWI | Seis UUIDs padrão, seleção RPM e verificador de mínimos | Identificada e corrigida a divergência de `vega-cli`, descrita abaixo. |

Scripts de desenvolvimento preservados na árvore upstream do LDI ainda citam
DING. Eles não integram o payload instalado da suíte. Essas ocorrências não
são tratadas como dependências ativas do GNOME. O schema compartilhado Sheliak
e os IDs de perfil legados continuam intencionais para preservar preferências.

## Achado corrigido: frontend opcional exigido pela ISO

[Issue #80](https://github.com/lyra-os-linux/lyraos-desktop/issues/80), P1 da
receita, responsável: manutenção do Desktop.

`check-gnome-image.py` exigia `vega-cli >=5.1.22`, embora a receita não
selecionasse esse pacote. Vega GTK exige `vegad`, sem dependência do frontend
de terminal. Com `onlyRequired`, a ausência de CLI interrompia a preparação
da imagem no verificador, mesmo com todos os componentes GNOME previstos.

A correção mantém CLI opcional, retira sua exigência do gate GNOME e seleciona
`vegad` explicitamente. O mínimo do daemon permanece 5.1.26. O verificador
continua rejeitando obrigatórios ausentes, versões antigas e extensões
incompatíveis; assinatura e proveniência continuam em seus gates próprios.

Dois testes de regressão conferem a correspondência entre mínimos e seleção
explícita, além da execução completa do verificador sem o frontend opcional.
A falha de CLI foi reproduzida antes da correção. Após corrigir, passaram os
seis testes do verificador e os 200 testes Python do Desktop. A seleção de
pacotes e os metadados da imagem são fixtures nesse ensaio; nenhuma raiz KIWI
ou ISO foi construída para esse resultado.

Risco limitado à composição/verificação da imagem; sem mudança na estação.
Se a composição pretendida mudar, revisar seleção e mínimos em conjunto.
Reverter esta correção isoladamente reintroduz a exigência incorreta.

## Novo login e limite da evidência pessoal

O GNOME iniciou em 13/09 às 17:12:54, horário de São Paulo. O autostart do
coordenador registrou sucesso às 17:12:58. A consulta posterior mostrou
perfil Lyra, seis componentes instalados e seis estados runtime `1` (ativos).
Isso encerra a pendência de observar o helper 2.0.1 no próximo login pessoal.
Não equivale a uma nova migração do monolito, uma conta nova ou primeiro boot
da candidata. Não houve reinício forçado da sessão durante a auditoria.

Há uma pendência P3 local acompanhada na #78: arquivos de prévias antigas,
sem proprietário RPM, mantêm um diretório `sheliak@lyraos.com.br` incompleto
na estação. O Shell registra `Missing metadata.json` ao examiná-lo. Foram
encontrados `windows-preview.js`, `windows-spacing-preview.js` e três
catálogos em `locale-windows-refresh`. Eles não integram o RPM 2.0.1 nem a
receita atual, e os seis componentes atuais ficaram ativos. A limpeza deve
preservar backup dos arquivos e verificar seus hashes/proprietários; não
adicionar remoção indiscriminada de arquivos do usuário ao pacote para isso.

O override global da estação ainda tem o UUID monolítico da imagem de origem;
a migração aplica os UUIDs novos por usuário. O override da próxima receita
já contém a suíte. Essa diferença reforça que a estação não é a nova ISO.
O instalador também não está instalado na estação; continua obrigatório na
raiz da imagem. Não executar o verificador local e declarar a ISO aprovada.

## Continuidade

- Consolidar e qualificar o conjunto de RPMs assinados e a candidata local.
- Executar instalação, usuário novo, migração, atualização/reboot/rollback,
  hardware e idiomas sobre a mesma candidata, conforme a #78.
- Retomar os controles do Vega dependentes de componente/perfil.
- Pedido novo do mantenedor, apenas na fila:
  [Vega #142](https://github.com/lyra-os-linux/vega/issues/142), habilitar o
  botão de áreas de trabalho no perfil Ubuntu.

Evidências locais: `analysis/2026-09-13/gnome-audit/` no workspace do mantenedor,
com baseline, manifestos RPM, log do login e resultados antes/depois. Nenhuma
publicação OBS ou qualificação integral de hardware/ISO foi feita nesta etapa.
