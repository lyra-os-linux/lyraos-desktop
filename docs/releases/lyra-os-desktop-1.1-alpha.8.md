# Lyra OS 1.1 Alpha 8 “Odisseia” — notas de lançamento (rascunho)

Este texto acompanha a preparação da candidata. Os recursos e limitações
definitivos serão fechados após a qualificação da ISO exata; este rascunho não
autoriza publicação.

A Alpha 8 tem como foco concluir a integração do Desktop 1.1 sobre
openSUSE Leap 16.1 e verificar instalação, primeira inicialização,
atualização, rollback e interfaces nos três idiomas suportados (`en-US`,
`pt-BR`, `es-ES`). É uma versão Alpha destinada a testes, não a produção.

## Escopo e limites a confirmar

- O controle parental só será incluído se a candidata passar os testes de
  negação e evasão, incluindo Flatpak. Se não passar, ficará fora da Alpha 8;
  contas comuns continuarão com o comportamento habitual.
- O ensaio de upgrade e rollback da versão publicada para a candidata é
  obrigatório antes de anunciar migração segura de uma instalação existente.
- RAID, LVM, particionamento manual e instalação lado a lado continuam fora do
  cenário de instalação coberto, salvo qualificação específica posterior.
- A cobertura de hardware físico será descrita conforme os resultados da
  candidata final.

## Integridade

Arquivo esperado: `LyraOS-Desktop-1.1-alpha.8-x86_64.iso`. Verifique o
checksum distribuído junto da ISO com
`sha256sum -c LyraOS-Desktop-1.1-alpha.8-x86_64.iso.sha256`.
Pela ADR 0005, a Alpha usa SHA-256 sem assinatura GPG destacada da ISO;
pacotes e repositórios exigem assinatura válida.

O contrato de publicação está em `docs/release-gate.md`. Não publique senhas,
chaves ou dados pessoais em relatos de problemas.
