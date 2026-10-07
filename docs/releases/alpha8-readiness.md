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

## Bloqueios encontrados no pré-voo de 07/10

- O inventário remoto de issues ainda mostra a [#89](https://github.com/lyra-os-linux/lyraos-desktop/issues/89)
  (`P1`, montagem de efivarfs/BIOS) e a [#102](https://github.com/lyra-os-linux/lyraos-desktop/issues/102)
  (`P1` parental/Flatpak) abertas. Há correções de código para o instalador,
  mas a #89 requer a matriz BIOS/UEFI/NVRAM na candidata antes de fechamento.
  A #102 só deixa de bloquear a Alpha 8 se o recurso parental for formalmente
  retirado do escopo da imagem e das alegações de proteção.
- A [#125](https://github.com/lyra-os-linux/lyraos-desktop/issues/125)
  registra o backport de atalhos globais do portal GNOME ainda sem RPM final
  consumido na candidata. Decidir seu escopo e severidade com o comportamento
  observado na ISO exata; não marcar como resolvida pela fixture temporária.
  O RPM de staging assinado passou testes de sessão em VM, mas a qualificação
  registrou que o `zypper update` normal não migra uma instalação SUSE para
  esse vendor OBS. A promoção e o consumo na imagem exigem resolver essa
  migração específica e repetir os testes com o pacote final.

- A antiga revisão 1.10.1 do `lyra-theme` havia entrado diretamente no OBS
  release e seu tarball diferia do commit Git anunciado. A
  [PR 21 do tema](https://github.com/lyra-os-linux/lyraos-desktop-theme/pull/21)
  registrou o payload no Git e passou na CI. O staging publicou r25, srcmd5
  `7f5192d585bc2b8d2f7817636cbe78db`, somente para Leap 16.1; o gate
  completo passou. O RPM público e os metadados do repositório passaram na
  verificação com a chave fixada, e as 53 entradas de caminho/digest/tamanho
  do payload são idênticas ao RPM release anterior. O
  [request OBS 1383107](https://build.opensuse.org/request/show/1383107) foi
  aceito, instalando essa fonte como release r51. **Falta o novo build e a
  publicação do release** antes de repetir `obs-release.py health` e fixar
  RPMs na candidata.
- A [PR 147](https://github.com/lyra-os-linux/lyraos-desktop/pull/147)
  corrige o gate OBS para recusar `published dirty=true`, observado logo após
  o aceite da nova fonte do tema. Sem isso, o gate poderia tratar binários
  antigos como atuais. Os 38 testes locais passaram; CI/merge pendentes.
- A última construção de ensaio Alpha 7 (06/10) foi rejeitada pelo audit do
  initrd live: o módulo Plymouth entrou no initrd genérico. Não é teste da
  Alpha 8 atual: o build usou fonte `561201e` com alterações locais, enquanto
  `origin/main` já inclui a configuração condicional de dracut do commit
  `b5979ea`. Antes de aprovar a candidata, reexecutar o audit no build atual;
  preservar Plymouth no sistema instalado e não afrouxar a checagem.
