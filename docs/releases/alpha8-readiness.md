# Preparação da Alpha 8 — 07/10/2026

**Meta do mantenedor:** publicar até 15/10/2026, apenas se a candidata exata
passar o [gate de release](../release-gate.md). Esta branch prepara metadados;
não contém uma ISO candidata nem evidência de publicação.

## Sequência de decisão

1. Até 09/10: fechar o escopo da candidata, inclusive a decisão de incluir ou
   retirar o controle parental da Alpha 8. A evasão Flatpak #102 mantém o
   recurso parental `NO-GO` até prova contrária na imagem candidata.
2. Entre 10 e 12/10: integrar somente alterações qualificadas, conferir RPMs
   e repositórios Leap 16.1, gerar uma ISO limpa e registrar commit, inventário
   de pacotes e SHA-256. A alteração do conteúdo cria uma nova candidata.
3. Em 13 e 14/10: executar o gate inteiro na ISO exata. Inclui instalação,
   primeiro boot, Secure Boot, sessão live, hardware, rollback, upgrade com
   falhas injetadas, ECA Digital aplicável, idiomas e congelamento funcional.
4. Em 15/10: publicar o bundle da mesma ISO testada somente com todos os
   resultados exigidos aprovados e sem P0/P1. Falha no gate adia o lançamento;
   não se reaproveita evidência de outra ISO.

`scripts/image-build.py required-test-results` exige 11 resultados nesta
versão: `obs-repositories`, `live-session`, `installer`, `first-boot`,
`uefi-secure-boot`, `rollback`, `hardware-matrix`, `upgrade-rehearsal`,
`eca-digital`, `i18n` e `feature-freeze`. Todos dependem da candidata ou de
fontes de release qualificadas; protótipos parentais e a ISO Alpha 7 não são
resultados Alpha 8.

As notas em `lyra-os-desktop-1.1-alpha.8.md` são rascunho. Antes de publicar,
substituir descrições condicionais pelo escopo realmente testado e conferir
versão, nome e limitações com o inventário da candidata.
