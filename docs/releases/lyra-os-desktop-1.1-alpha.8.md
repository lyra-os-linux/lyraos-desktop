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
  permite executar um aplicativo negado; por isso, esta versão não oferece
  supervisão de contas nem sinal de idade a aplicativos. Contas comuns devem
  continuar com o comportamento habitual, sujeito à verificação na ISO final.
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
