# ADR 0013: Zed passa a ser empacotado e instalado por padrão na ISO

- Estado: aceita
- Data: 2026-08-24
- Relacionada: [ADR 0012](0012-linuxtoys-own-repository.md), que registrou o
  mesmo padrão de repositório próprio para empacotamento de software de
  terceiros.

## Contexto

O público-alvo declarado do Lyra OS Desktop é majoritariamente
desenvolvedores e profissionais de TI. [Zed](https://zed.dev/) é um editor de
código de alto desempenho, popular nesse público, mas não tem RPM oficial da
Zed Industries: a distribuição oficial para Linux é um tarball binário
pré-compilado, autocontido, com um autoupdater embutido que tenta se
substituir sozinho.

O único pacote openSUSE existente (projeto OBS comunitário `editors`) estava,
na avaliação, quase dois anos desatualizado (0.170.2, pré-1.0, contra a
1.16.1 estável), o que descartou usá-lo diretamente no baseline. A alternativa
considerada era não empacotar Zed no baseline e oferecê-lo como instalação
opcional via LinuxToys, evitando o custo de manter um pacote de ciclo de
lançamento rápido dentro da imagem assinada. O mantenedor decidiu, ainda
assim, seguir com o baseline, aceitando esse custo de manutenção, e criou o
repositório próprio `zededitor` antes mesmo do primeiro pacote existir —
diferente do LinuxToys/Welcome/Upgrade, que nasceram dentro deste
repositório e foram extraídos depois (ADRs 0010–0012).

## Decisão

O empacotamento do Zed vive em
[`lyra-os-linux/zededitor`](https://github.com/lyra-os-linux/zededitor), no
mesmo padrão do LinuxToys: um `_service` que baixa e verifica por checksum o
tarball de release oficial do GitHub (e os arquivos `LICENSE-GPL`/
`LICENSE-APACHE` do mesmo tag), um `zed.spec`, um `zed.changes` e um teste de
contrato próprio. Duas diferenças reais em relação ao LinuxToys, que é um
aplicativo Python puro sem libs nativas:

- o tarball da Zed inclui binários ELF e cópias privadas de bibliotecas X11/
  GLib carregadas via RPATH relativo (`$ORIGIN/../lib`); o `.spec` instala
  essa árvore intacta sob `%{_libexecdir}/zed` e exclui essas bibliotecas
  das Provides automáticas de RPM (`__provides_exclude_from`), para não
  anunciar bibliotecas de sistema que na verdade são cópias privadas;
- como o autoupdater embutido da Zed é um binário compilado (não dá para
  aplicar um patch de texto como no LinuxToys), o pacote usa
  `/usr/bin/zed` como um script wrapper que define
  `ZED_UPDATE_EXPLANATION` — mecanismo documentado pela própria Zed para
  empacotadores — antes de executar o binário real, redirecionando quem
  tentar atualizar manualmente para o Zypper.

O pacote `zed` entra em `obs/projects.toml` (projeto `lyra`) e em
`kiwi/config.xml`, ao lado do `linuxtoys`. O GNOME Text Editor continua
instalado; Zed é uma adição, não uma substituição.

## Consequências

- Atualizar a versão do Zed (upstream lança com frequência bem maior que o
  LinuxToys) exige um PR só no repositório `zededitor`, mas com uma
  cadência de manutenção real e recorrente — o trade-off que motivou
  cogitar o caminho opcional via LinuxToys em vez do baseline.
- `zed-rpmlintrc`, comitado junto ao pacote, existe porque as bibliotecas
  privadas sob `%{_libexecdir}/zed/lib` disparam checks genéricos de
  "biblioteca compartilhada de sistema" do rpmlint (ausência de scriptlets
  de `ldconfig`, seção de hash ausente) que não se aplicam a uma cópia
  privada carregada só por RPATH; cada filtro do arquivo documenta o motivo.
- `i18n/inventory.json` registra `zed` como `not-applicable`, no mesmo
  raciocínio do `linuxtoys`: interface e traduções continuam de
  responsabilidade do upstream.
