# Lyra OS 16.1 RC 1 “Odisseia” — notas de lançamento

Candidata de lançamento do Lyra OS Desktop 16.1 sobre **openSUSE Leap 16.1**.
Por decisão do mantenedor em 13/10/2026, a versão do Lyra OS passa a seguir a
numeração do openSUSE Leap: o que era planejado como Desktop 1.1 é publicado
como **16.1**; o codinome Odisseia identifica a geração 16.x.
Por decisão do mantenedor em 14/10/2026, o ciclo do Desktop sai da Alpha 8
diretamente para a RC 1, com publicação prevista até **31 de outubro de 2026**
e a versão estável em **5 de novembro de 2026**, dois dias após o GA do Leap
16.1. A RC 1 inicia o congelamento estrito: a partir dela só entram correções
de bugs, travamentos, segurança e performance crítica em pacotes já
distribuídos; nenhuma funcionalidade nova entra antes da 16.2.

A identidade técnica é `16.1-rc.1`, tag `v16.1-rc.1`, arquivo
`LyraOS-Desktop-16.1-rc.1-x86_64.iso`. Nenhum artefato `1.1-rc.1` foi
publicado; tags `1.1-*` anteriores permanecem apenas como registro histórico. Estas notas acompanham a candidata; o
commit, o SHA-256 e a decisão de GO são preenchidos no bundle publicado.

## Mudanças desde a Alpha 8

- Aparência padrão: a paleta Lyra deixou de ser aplicada no primeiro login;
  janelas GTK e terminal seguem as cores padrão do GNOME e do libadwaita
  ([#162](https://github.com/lyra-os-linux/lyraos-desktop/pull/162)). O tema
  Lyra do Firefox continua selecionado por padrão.
- NVIDIA via Vega: a integração oficial foi requalificada para o driver
  615.71.09 com o KMP assinado pela SUSE para o kernel 6.12.0-160100.7 do Leap
  16.1 (vegad 5.1.33 a 5.1.36, vega-gtk 5.1.47). A instalação opcional pelo
  Vega foi validada numa GeForce GTX 1650 Mobile com Secure Boot; após a
  instalação o Vega atualiza os repositórios NVIDIA do sistema e as consultas
  de software toleram repositórios ainda sem cache.
- Estabilidade do GNOME Shell: a dock (sheliak 2.0.5) não destrói mais os
  menus de contexto ativos a cada mudança de aplicativos abertos, caminho que
  derrubava o GNOME Shell (`invalid_closure_notify`); a imagem exige essa
  versão ([#172](https://github.com/lyra-os-linux/lyraos-desktop/pull/172)).
- Boot mais rápido: `iscsi.service` deixa de ser habilitado e o vegad 5.1.38
  não puxa mais `network-online.target` na preparação do primeiro boot, então
  `NetworkManager-wait-online` (+5,6 s medidos em hardware físico) sai da
  cadeia crítica do `graphical.target`. Pools iSCSI do libvirt continuam
  disponíveis sob demanda
  ([#168](https://github.com/lyra-os-linux/lyraos-desktop/issues/168)).
- Administração remota pelo Vega: o vegad 5.1.37 traz a regra polkit que pede
  a senha do próprio administrador (`wheel`) fora de uma sessão local, usada
  pelo `vega-cli` via SSH.
- Versão: identidade do produto alinhada ao Leap (`1.1` → `16.1`) em
  `release.toml`, no RPM `lyra-release` e nos scripts de release.
- Calendário: lançamento oficial do Lyra OS 16.1 em 5 de novembro de 2026,
  registrado em `docs/release-versioning.md` e no contrato do ecossistema.

## Escopo e limites

- Instalação nova apenas. A atualização de uma instalação Alpha 8 para a RC 1
  não é suportada; reinstale. O upgrade entre releases fica para a 16.2.
- O controle parental continua fora da 16.1 ([#102](https://github.com/lyra-os-linux/lyraos-desktop/issues/102)).
- RAID, LVM, particionamento manual e instalação lado a lado continuam fora
  do cenário coberto.
- Idiomas: `en-US`, `pt-BR` e `es-ES`, com `en-US` como fallback explícito.

## Qualificação obrigatória

A RC 1 repete o gate de `../release-gate.md` na ISO exata, em VM QEMU/KVM:
sessão live, instalação UEFI com NVRAM e Secure Boot, BIOS legado e UEFI sem
variáveis EFI, primeiro boot, rollback e `i18n`, além do resultado
`obs-repositories` do health check de release. Um defeito não trivial
interrompe a promoção e gera a RC 2; os critérios não são reduzidos para
preservar a data.

## Integridade

Arquivo esperado: `LyraOS-Desktop-16.1-rc.1-x86_64.iso`. Verifique o checksum
com `sha256sum -c LyraOS-Desktop-16.1-rc.1-x86_64.iso.sha256` e a assinatura
destacada `LyraOS-Desktop-16.1-rc.1-x86_64.iso.sha256.asc` com a chave oficial
de release (impressão digital `01B6 3EED BE6B 0791 26A0 116E FA73 53A1 31EC
EFEB`, publicada em `docs/release-signing-key.asc`). Pela ADR 0005, a RC é a
primeira candidata Desktop assinada; pacotes e repositórios continuam exigindo
assinatura válida.

## Versão final

A versão estável `16.1` será reconstruída a partir dos pacotes GA do openSUSE
Leap 16.1 (3 de novembro de 2026) e passará por um gate reduzido antes da
publicação em 5 de novembro de 2026.
