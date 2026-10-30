# Lyra OS 16.1 RC 3 “Odisseia” — notas de lançamento

Terceira e última candidata de lançamento do Lyra OS Desktop 16.1 sobre
**openSUSE Leap 16.1**. Por decisão do mantenedor em 30/10/2026, a RC 3 sai
antes do previsto, fica **congelada** e é promovida por tag à versão estável
**16.1 em 19 de novembro de 2026**, sem rebuild. As atualizações do Leap 16.1 GA
chegam pelo repositório `update` depois da instalação.

A identidade técnica é `16.1-rc.3`, tag `v16.1-rc.3`, arquivo
`LyraOS-Desktop-16.1-rc.3-x86_64.iso`, publicado em
[SourceForge](https://sourceforge.net/projects/lyra/files/releases/16.1/rc3/desktop/).

| Campo | Valor |
| --- | --- |
| Build | a preencher |
| Commit | a preencher |
| SHA-256 | a preencher |
| Gate | a preencher |
| Decisão | a preencher |

## Exceção ao congelamento

O Vega ganhou funcionalidades novas depois da RC 2, por decisão explícita do
mantenedor: o diagnóstico de saúde completo, a revisão de segurança, o
Liberar espaço, "Minha internet não funciona", a análise de boot, o Pedir
ajuda e a verificação semanal. Todos foram especificados (OpenSpec), testados
pelo mantenedor e passam por este gate. A Welcome ganhou a página "Como pedir
ajuda" e o cartão da verificação semanal.

## Mudanças desde a RC 2

- **Vega** (vegad 5.6.2, vega-gtk 5.8.0):
  - **Diagnóstico de saúde** em Hardware: pacotes, disco (SMART, btrfs),
    processador e memória sob carga, desempenho do disco, GPU, logs,
    plataforma (com espaço livre e backup atrasado), segurança, tempo de boot e
    rede. Cada item em Atenção ou Falha tem **Corrigir** quando há conserto
    seguro (com snapshot antes) ou **Ver o que fazer**; os logs têm **Já vi**.
  - **Segurança:** firewall, portas expostas (com "Portas abertas" na página
    Rede), correções de segurança pendentes, SSH, criptografia e contas.
  - **Liberar espaço** em Armazenamento: core dumps, journal antigo, cache do
    zypper, Flatpak sem uso, kernels antigos, Snapper, lixeira, miniaturas e o
    cache dos aplicativos (as pastas em uso por um programa ficam de fora).
  - **Minha internet não funciona** na página Rede: cabo ou Wi-Fi, endereço,
    roteador, DNS e internet, passo a passo e sem senha.
  - **Pedir ajuda** no relatório: o texto para o fórum ou uma issue, sem dados
    pessoais ([guia](https://lyraos.com.br/docs/pedir-ajuda.html)).
  - **Verificação semanal** em segundo plano, com uma notificação do GNOME só
    quando algo muda; liga, desliga e muda a frequência em Preferências.
  - Atualização de firmware pelo fwupd e Flatpak sem pedir senha.
- **Welcome 0.5.0:** a página "Como pedir ajuda" depois da rede e o cartão da
  verificação semanal na página do Vega.
- **Apps Tauri** (beam 1.1.1, sulafat 1.1.1, lyra-downloads 0.2.1): a mesma
  correção do crash do WebKit ao fechar (DMA-BUF) que o Vega já tinha.
- **Atalhos globais:** o `xdg-desktop-portal-gnome` com a correção upstream
  ([#125](https://github.com/lyra-os-linux/lyraos-desktop/issues/125)).
- **Sessão live:** o liveuser autoriza as ações administrativas do polkit
  ([#211](https://github.com/lyra-os-linux/lyraos-desktop/issues/211)), o
  problema conhecido da RC 2.
- **Rede:** a imagem traz o `iputils` (`ping`, `tracepath`).
- **vegad:** a manutenção das chaves de assinatura não falha mais no primeiro
  boot (vegad 5.1.48), e a WebKit do Vega não aborta ao fechar (vega-gtk
  5.3.3).

## Problemas conhecidos

- Nenhum P0/P1 aberto na abertura desta candidata.

## Qualificação

Repete o gate completo da RC 2 (`../release-gate.md`, seção RC 3 changes), na
ISO exata. A imagem recusa versões anteriores às mínimas de
`check-gnome-image.py` (vegad 5.6.2, vega-gtk 5.8.0, Welcome 0.5.0, beam e
sulafat 1.1.1, lyra-downloads 0.2.1). O bundle inclui a ISO, as evidências, os
SBOMs, o checksum e a assinatura destacada pela chave oficial de release
(`01B6 3EED BE6B 0791 26A0 116E FA73 53A1 31EC EFEB`).
