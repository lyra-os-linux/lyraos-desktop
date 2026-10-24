# Lyra OS 16.1 RC 2 “Odisseia” — notas de lançamento

Segunda candidata de lançamento do Lyra OS Desktop 16.1 sobre **openSUSE Leap
16.1**. A RC 1 (`v16.1-rc.1`) foi publicada; em 24/10/2026 o mantenedor
decidiu levar à candidata duas correções do vegad em vez de deixá-las para
uma atualização depois do lançamento. Como o conteúdo da imagem muda, a RC 2
é uma nova candidata e repete o gate. A publicação está prevista até **31 de
outubro de 2026**, deixando margem para uma RC 3 antes do GA do Leap 16.1 em
3 de novembro. A versão estável continua prevista para **5 de novembro de
2026**. Vale o congelamento estrito da RC 1: só correções
de bugs, travamentos, segurança e performance crítica em pacotes já
distribuídos.

A identidade técnica é `16.1-rc.2`, tag `v16.1-rc.2`, arquivo
`LyraOS-Desktop-16.1-rc.2-x86_64.iso`. Estas notas acompanham a candidata; o
commit, o SHA-256 e a decisão de GO são preenchidos no bundle publicado.

## Mudanças desde a RC 1

- Firewall no Vega: o vegad 5.1.39 informa a zona que realmente filtra o
  tráfego da máquina (`public`, ligada à interface de rede), e não a zona
  `docker` predefinida que o firewalld lista mesmo sem a interface `docker0`
  ([vegad#83](https://github.com/lyra-os-linux/vegad/issues/83),
  [vegad#85](https://github.com/lyra-os-linux/vegad/pull/85)). As regras do
  firewall não mudam; só o nome da zona exibido estava errado.
- Contrato D-Bus: a introspecção de `org.lyraos.Vega1.Snapshots` passa a
  declarar o sinal `ClearProgress`, como no contrato de `lyra-vega-dbus`
  ([vegad#86](https://github.com/lyra-os-linux/vegad/pull/86)).
- A imagem exige vegad 5.1.39 ou posterior (`check-gnome-image.py`).
- Escopo: KDE Plasma e XFCE foram abandonados; o GNOME é a única edição
  Desktop ([ADR 0018](../adr/0018-abandon-kde-xfce.md)). Nenhum pacote da ISO
  muda por isso.

O vegad 5.1.39 foi promovido ao canal de release do OBS pelo SR 1392226,
depois de testado numa VM Leap 16.1 contra o 5.1.38.

## Escopo e limites

Os mesmos da [RC 1](lyra-os-desktop-16.1-rc.1.md#escopo-e-limites):

- Só instalação nova. Uma instalação RC 1 recebe o vegad 5.1.39 pela
  atualização normal do zypper, sem reinstalar.
- O controle parental continua fora da 16.1 ([#102](https://github.com/lyra-os-linux/lyraos-desktop/issues/102)).
- RAID, LVM, particionamento manual e instalação lado a lado continuam fora
  do cenário coberto.
- Idiomas: `en-US`, `pt-BR` e `es-ES`, com `en-US` como fallback explícito.

## Qualificação obrigatória

A RC 2 repete o gate da RC 1 (`../release-gate.md`) na ISO exata, em VM
QEMU/KVM:

- sessão live;
- instalação UEFI com NVRAM e Secure Boot;
- BIOS legado e UEFI sem variáveis EFI;
- primeiro boot;
- rollback;
- `i18n`;
- o resultado `obs-repositories` do health check de release.

No sistema instalado, o status do firewall no Vega precisa mostrar a zona
`public`. Um defeito não trivial interrompe a promoção e gera a RC 3; os
critérios não são reduzidos para preservar a data.

## Integridade

Arquivo esperado: `LyraOS-Desktop-16.1-rc.2-x86_64.iso`. Para verificar:

- o checksum, com `sha256sum -c LyraOS-Desktop-16.1-rc.2-x86_64.iso.sha256`;
- a assinatura destacada `LyraOS-Desktop-16.1-rc.2-x86_64.iso.sha256.asc`,
  com a chave oficial de release (impressão digital `01B6 3EED BE6B 0791 26A0
  116E FA73 53A1 31EC EFEB`, publicada em `docs/release-signing-key.asc`).

## Versão final

A versão estável `16.1` será reconstruída a partir dos pacotes GA do openSUSE
Leap 16.1 (3 de novembro de 2026), com o mesmo conteúdo Lyra da RC 2, e
passará por um gate reduzido antes da publicação em 5 de novembro de 2026.
