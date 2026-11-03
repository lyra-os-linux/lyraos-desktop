# Lyra OS 16.1 “Odisseia” — notas de lançamento

Versão estável do Lyra OS Desktop, com GNOME, sobre **openSUSE Leap 16.1**,
publicada em **3 de novembro de 2026**. É a própria ISO da
[RC 3](lyra-os-desktop-16.1-rc.3.md), a candidata final, promovida por tag sem
rebuild. O arquivo mantém o nome da RC 3, com o mesmo checksum e a mesma
assinatura.

| Campo | Valor |
| --- | --- |
| Versão | `16.1` |
| Tag | `v16.1` (o mesmo commit da `v16.1-rc.3`) |
| Commit | `70e4bf9805b3caaa32052585ffce75467a282acd` |
| Arquivo | `LyraOS-Desktop-16.1-rc.3-x86_64.iso` |
| SHA-256 | `50211bcf31271d232ea4326fc46704cad79a729d1bb363679ce32829d7794a3a` |
| Download | [releases/16.1/stable/desktop/](https://sourceforge.net/projects/lyra/files/releases/16.1/stable/desktop/) no SourceForge |
| Build | 30/10/2026, `scripts/build-desktop-rc3.sh` |
| Gate | completo e aprovado em 30/10/2026 |

Quem instalou a RC 3 já tem o sistema da versão estável e só precisa seguir
atualizando. As atualizações do Leap 16.1 final chegam pelo repositório
`update` depois da instalação.

## Suporte

O Lyra OS não é uma rolling release. A 16.1 tem **2 anos de suporte**, até
**3 de novembro de 2028**, e recebe as correções pelos repositórios de pacotes
dela. O fonte da release fica na tag `v16.1`, e as correções da 16.1 entram
pela branch `release/16.1` ([política de releases e suporte](https://github.com/lyra-os-linux/.github/blob/main/SUPPORT.md#ciclo-de-releases-e-suporte)).

Componentes como o Vega, a Welcome, o Beam e o Sulafat não pertencem a uma
release: continuam sendo desenvolvidos e chegam à 16.1 pelas atualizações.

## O que a 16.1 traz

Desde a Alpha 7, quando o ciclo passou para o Leap 16.1, até a RC 3:

- **Base openSUSE Leap 16.1**, com GNOME como a única edição Desktop. As
  edições KDE Plasma e XFCE foram descontinuadas.
- **Vega**, o centro de controle do sistema:
  - diagnóstico de saúde em Hardware, com **Corrigir** quando há um conserto
    seguro (com snapshot antes) ou **Ver o que fazer**;
  - revisão de segurança: firewall, portas expostas, correções pendentes, SSH,
    criptografia e contas;
  - **Liberar espaço** em Armazenamento;
  - **Minha internet não funciona** na página Rede, passo a passo e sem senha;
  - **Pedir ajuda**, com o texto para o fórum ou para uma issue, sem dados
    pessoais;
  - verificação semanal em segundo plano, com notificação só quando algo muda;
  - atualização de firmware pelo fwupd e Flatpak sem pedir senha.
- **Welcome 0.5.0**, com a página "Como pedir ajuda" e o cartão da verificação
  semanal.
- **Controle parental básico** (desde a RC 2).
- **Segurança:** correção no `sudo` (RC 2) e checksum da ISO assinado pela
  chave oficial de release (desde a RC 1).
- **Aplicativos:** o Beam, o Sulafat e o Lyra Downloads não travam mais ao
  fechar; os atalhos globais recebem a correção upstream do
  `xdg-desktop-portal-gnome` ([#125](https://github.com/lyra-os-linux/lyraos-desktop/issues/125)).
  O Flatpak e o LinuxToys não vêm mais instalados (RC 2).
- **Sessão live:** a conta live autoriza as ações administrativas do Vega
  ([#211](https://github.com/lyra-os-linux/lyraos-desktop/issues/211)).

O detalhe de cada etapa está nas notas da
[RC 3](lyra-os-desktop-16.1-rc.3.md), da [RC 2](lyra-os-desktop-16.1-rc.2.md),
da [RC 1](lyra-os-desktop-16.1-rc.1.md), da [Alpha 8](lyra-os-desktop-1.1-alpha.8.md)
e da [Alpha 7](lyra-os-desktop-1.1-alpha7.md).

## Depois da instalação

A ISO traz o Vega da RC 3 (vegad 5.6.2, vega-gtk 5.8.0). A primeira
atualização já traz as versões novas do Vega publicadas depois da RC 3. Entre
as mudanças, o Vega deixa de instalar o driver NVIDIA: o driver passa a ser
instalado pelo [guia](https://github.com/lyra-os-linux/lyraos-desktop/discussions/234),
com os pacotes oficiais da NVIDIA para o Leap 16.1.

## Escopo e limites

- Apenas instalação nova.
- O controle parental é básico: não filtra sites e não resiste a uma criança
  com conhecimento técnico.
- RAID, LVM, particionamento manual e instalação lado a lado ficam fora do
  cenário coberto.
- Idiomas do sistema: en-US, pt-BR e es-ES, com o inglês como alternativa.

## Problemas conhecidos

Não há P0 nem P1 abertos. Ficam aceitos, com prioridade P2/P3:

- [#22](https://github.com/lyra-os-linux/lyraos-desktop/issues/22): com NVIDIA,
  o monitor externo não acorda depois da suspensão ou do desligamento da tela.
  Contorno: reconectar o cabo ou trocar de terminal virtual.
- [#102](https://github.com/lyra-os-linux/lyraos-desktop/issues/102): com o
  Flatpak habilitado, uma conta supervisionada consegue instalar e abrir apps
  Flatpak. Contorno: não habilitar o Flatpak em máquinas com contas
  supervisionadas.

O gate rodou em VM QEMU/KVM. A validação em hardware físico
([#69](https://github.com/lyra-os-linux/lyraos-desktop/issues/69)) continua
aberta.

## Integridade

O bundle publicado inclui a ISO, as evidências do gate, os SBOMs, o checksum e
a assinatura destacada. Baixe a ISO, o `.sha256` e o `.sha256.asc` da mesma
pasta e confira:

```sh
sha256sum -c LyraOS-Desktop-16.1-rc.3-x86_64.iso.sha256
gpg --verify LyraOS-Desktop-16.1-rc.3-x86_64.iso.sha256.asc LyraOS-Desktop-16.1-rc.3-x86_64.iso.sha256
```

A assinatura deve ser válida para a chave oficial de release
(`01B6 3EED BE6B 0791 26A0 116E FA73 53A1 31EC EFEB`), a mesma das RCs.
