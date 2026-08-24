# ADR 0014: VS Code entra só como registro do repositório oficial da Microsoft

- Estado: aceita
- Data: 2026-08-24
- Relacionada: [ADR 0013](0013-zed-editor-baseline-package.md), que
  registrou Zed no baseline reempacotando o binário upstream — o caminho
  descartado aqui por um motivo de licença, não técnico.

## Contexto

Depois do Zed (ADR 0013), o mantenedor pediu o mesmo tratamento para o
Visual Studio Code. Diferente do Zed (GPL-3.0/Apache-2.0) e do LinuxToys
(GPL-3.0), o EULA da Microsoft para os builds oficiais do VS Code proíbe
empacotar ou redistribuir o instalador oficial por conta própria — inclusive
via um repositório de terceiros assinado, como o `home:rodrigosbrito:lyra`.
Reempacotar o tarball oficial da Microsoft do mesmo jeito que o Zed
violaria esses termos.

A Microsoft já publica seu próprio repositório YUM/Zypper oficial
(`packages.microsoft.com/yumrepos/vscode`), assinado com uma chave de
release própria. O pacote `distribution-gpg-keys`, já disponível no
repositório OSS padrão do openSUSE, inclui essa mesma chave em
`/usr/share/distribution-gpg-keys/microsoft/microsoft.gpg` — confirmado
localmente por fingerprint (`BC52 8686 B50D 79E3 39D3 721C EB3E 94AD BE12
29CF`, idêntico ao `microsoft.asc` publicado pela Microsoft) e por
verificação real da assinatura do `repomd.xml` do repositório contra essa
chave.

## Decisão

O pacote `vscode-repo`, em
[`lyra-os-linux/vscode`](https://github.com/lyra-os-linux/vscode), não
carrega nenhum binário do VS Code. Ele só instala um arquivo
`/etc/zypp/repos.d/vscode.repo` apontando para o repositório oficial da
Microsoft, com `gpgcheck` e `repo_gpgcheck` habilitados e a chave resolvida
via `distribution-gpg-keys` (declarado como `Requires`). Depois de
instalado, `zypper install code` resolve direto do repositório da
Microsoft — instalação, atualização e assinatura continuam
inteiramente sob responsabilidade deles.

`vscode-repo` entra em `obs/projects.toml` (projeto `lyra`), para ficar
disponível via o repositório assinado do Lyra que a imagem já mantém
registrado. Ao contrário do Zed, **não** entra em `kiwi/config.xml`: o VS
Code não vem pré-instalado por padrão — o usuário roda `zypper install
vscode-repo && zypper install code` quando quiser, evitando instalar por
padrão um binário de telemetria/licença proprietária da Microsoft numa
imagem assinada.

## Consequências

- Nenhuma manutenção de versão: quem mantém `code` atualizado é a
  Microsoft, não o Lyra. Isso resolve o trade-off de cadência de
  lançamento que motivou a ADR 0013 a cogitar (e descartar) o caminho
  opcional via LinuxToys para o Zed.
- Se o mantenedor decidir, no futuro, instalar `code` por padrão na ISO,
  isso exige apenas adicionar `<package name="code"/>` a
  `kiwi/config.xml` (e, por consequência, aceitar a EULA/telemetria da
  Microsoft no baseline) — uma decisão separada desta.
- `i18n/inventory.json` registra `vscode-repo` como `not-applicable`: não
  há texto de interface próprio do Lyra nesse pacote.
