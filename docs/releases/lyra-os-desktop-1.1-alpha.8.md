# Lyra OS 1.1 Alpha 8 “Odisseia” — notas de lançamento (rascunho)

Este texto acompanha a preparação da candidata. Os recursos e limitações
definitivos serão fechados após a qualificação da ISO exata; este rascunho não
autoriza publicação.

A Alpha 8 tem como foco concluir a integração do Desktop 1.1 sobre
openSUSE Leap 16.1 e verificar instalação, primeira inicialização,
atualização, rollback e interfaces nos três idiomas suportados (`en-US`,
`pt-BR`, `es-ES`). É uma versão Alpha destinada a testes, não a produção.

## Escopo e limites a confirmar

- O controle parental está fora da Alpha 8. A integração com Flatpak ainda
  permite executar um aplicativo negado; por isso, o Lyra não oferece a
  integração de supervisão de contas nem sinal de idade a aplicativos nesta
  versão. Contas comuns devem
  continuar com o comportamento habitual, sujeito à verificação na ISO final.
- A Alpha 8 cobre apenas instalação nova. A atualização de uma instalação
  Alpha 7 para a Alpha 8 não foi testada e não é suportada; reinstale.
- RAID, LVM, particionamento manual e instalação lado a lado continuam fora do
  cenário de instalação coberto, salvo qualificação específica posterior.
- A candidata é qualificada somente em máquinas virtuais (BIOS, UEFI com e
  sem NVRAM, Secure Boot). Nenhum hardware físico foi testado nesta versão.
- O pacote atual da base para o portal GNOME de atalhos globais pode responder
  com erro após a confirmação de um atalho. Há um backport em staging, mas sua
  instalação/atualização ainda não foi qualificada para esta candidata
  ([#125](https://github.com/lyra-os-linux/lyraos-desktop/issues/125)).
  Confirmar a limitação na ISO final antes de publicar estas notas.

## ECA Digital

Esta versão não inclui controle parental, vínculo de contas supervisionadas
nem sinal de idade para aplicativos, e não retém qualquer evidência de idade.
O pacote `malcontent` da base permanece instalado por dependência do Centro de
Controle do GNOME; sua presença não é proteção configurada pelo Lyra
([#102](https://github.com/lyra-os-linux/lyraos-desktop/issues/102)).

## Congelamento funcional

Nenhuma funcionalidade nova entrou depois do plano aprovado em 07/10/2026
([#28](https://github.com/lyra-os-linux/lyraos-desktop/issues/28)). A
publicação só ocorre sem P0 ou P1 abertos no escopo entregue; os P2 e P3
aceitos aparecem em "limitações conhecidas". Confirmar esta declaração na
decisão de GO antes de publicar.

## Integridade

Arquivo esperado: `LyraOS-Desktop-1.1-alpha.8-x86_64.iso`. Verifique o
checksum distribuído junto da ISO com
`sha256sum -c LyraOS-Desktop-1.1-alpha.8-x86_64.iso.sha256`.
Pela ADR 0005, a Alpha usa SHA-256 sem assinatura GPG destacada da ISO;
pacotes e repositórios exigem assinatura válida.

O contrato de publicação está em `docs/release-gate.md`. Não publique senhas,
chaves ou dados pessoais em relatos de problemas.
