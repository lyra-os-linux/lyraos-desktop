# Lyra OS

Lyra OS é uma distribuição Linux desktop baseada no openSUSE Leap 16.1,
voltada a uma experiência GNOME simples, estável e integrada ao ecossistema
Lyra. Este repositório contém a descrição KIWI usada para gerar a ISO live e
o instalador da edição **Odisseia 1.1 Alpha 7** para computadores x86_64.

## Foco da versão 1.1

A versão final do Lyra OS 1.1 tem **GNOME como único alvo de lançamento**.
O trabalho atual de pacotes próprios e interface concentra-se no GNOME e no
Vega GTK. KDE Plasma e XFCE ficam em segundo plano, sem compromisso de
lançamento ou paridade nesta versão. Seus repositórios e registros anteriores
permanecem disponíveis; retomá-los exige planejamento próprio.

A decisão de 16/09/2026 prevê **uma única ISO Desktop GNOME**, sem a pilha
NVIDIA pré-instalada. A instalação NVIDIA será opcional pelo Vega GTK após
instalar o sistema, usando RPMs oficiais e a integração `lyra-nvidia`.
Esta decisão substitui o plano de duas variantes de 14/09. A ISO e o fluxo
opcional ainda exigem qualificação; veja o [plano NVIDIA](docs/nvidia-iso.md).

A [situação do GNOME](docs/status-gnome.md) distingue código integrado,
pacotes enviados e qualificação da candidata. O planejamento futuro de KDE
está em [flavor KDE experimental](docs/kde-experimental-flavor.md).

## Políticas e privacidade

O [épico do ECA Digital](https://github.com/lyra-os-linux/lyraos-desktop/issues/11)
e seus gates técnicos, jurídicos e de privacidade continuam registrados.
Essa trilha não equivale a uma declaração de conformidade já obtida. O foco
atual de integração é GNOME; nenhuma entrega Qt/XFCE é prometida para a 1.1.

> [!IMPORTANT]
> O projeto ainda está em desenvolvimento. A ISO não deve ser considerada uma
> versão final até que o ciclo completo de build, instalação e inicialização do
> sistema instalado seja validado novamente após as correções mais recentes.

## Principais características

- openSUSE Leap 16.1 com GNOME;
- sessão live e instalador nativo em Rust/Tauri, com HTML/CSS integrado ao
  WebKitGTK do sistema;
- Btrfs com Snapper e snapshots automáticos durante operações do Zypper;
- recuperação por snapshots no menu do GRUB;
- inicialização UEFI e suporte ao Secure Boot com o shim do openSUSE;
- escolha na instalação entre ZRAM com Zstandard, swap em disco ou nenhuma
  memória virtual;
- Firefox, VLC, Flatpak e Flathub;
- Vega GTK, Welcome e os aplicativos Lyra fornecidos em RPM pelo OBS;
- Sheliak como pacote de seis extensões independentes: Lyra Dock, Painel,
  Menus, Busca, Animações e Desktop Icons;
- identidade visual Lyra OS no desktop e no GRUB;
- `lyra-report` para diagnóstico local e sob demanda, sem telemetria ou envio
  automático de dados.

O instalador seleciona o caminho de **BIOS** ou **UEFI** pelo firmware da
sessão live. BIOS usa GPT com uma partição de boot de 2 MiB; UEFI usa uma ESP
no próprio disco e mantém um caminho de boot alternativo quando a NVRAM não
está disponível. Secure Boot requer UEFI e usa shim/GRUB do openSUSE.
**Intel TDX não é requisito do Lyra Installer.** A qualificação da ISO completa
continua obrigatória; veja os testes e limites em
[`docs/installer-firmware-requirements.md`](docs/installer-firmware-requirements.md).

O desktop habilita somente o Packman Essentials para as compilações completas
de FFmpeg e VLC; o Packman completo não é usado. A pilha GStreamer vem dos
pacotes oficiais compatíveis com a versão da base Leap. Os repositórios
oficiais do Leap têm prioridade sobre os repositórios OBS do ecossistema Lyra
no sistema instalado.

## Estado atual

A Alpha 7 usa exclusivamente o Lyra Installer nativo em
[`installer/`](installer/). A imagem já instala seu RPM e abre o frontend na
sessão live; a confirmação final já aciona o backend privilegiado e apresenta
o resultado da execução. O fluxo principal de instalação e primeiro boot foi
validado na base anterior; todo o gate será repetido sobre o Leap 16.1. Não
há segundo instalador, configuração alternativa ou fallback na imagem.

Para a próxima candidata ainda é necessário qualificar o conjunto de RPMs
assinados nos repositórios de release, construir a ISO localmente e repetir os
gates de live, instalação, primeiro login, Secure Boot, hardware, atualização
e rollback. As recentes correções da suíte GNOME devem estar nessa candidata.

O GitHub valida fontes e contratos; o OBS compila e publica pacotes RPM; o KIWI
constrói a ISO **localmente**; o SourceForge distribui os artefatos aprovados.
Veja o [fluxo de imagens](docs/image-builds.md).

Consulte a [documentação técnica do KIWI](kiwi/README.md) para conhecer as
decisões de implementação, limitações e verificações já realizadas.

## Ciclo atual e próximos ciclos

O instalador e as interfaces próprias do Lyra OS 1.1 têm como escopo
`en-US`, `pt-BR` e `es-ES`, com inglês como padrão e fallback. A presença dos
catálogos e os testes dos componentes não dispensam a revisão da candidata
nos três idiomas.

A [política de versões](docs/release-versioning.md) registra a meta da 1.1;
o [roadmap](docs/roadmap.md) detalha o ciclo. Datas são referências de
planejamento. A promoção depende do [release gate](docs/release-gate.md),
sem prazo conjunto para KDE/XFCE.

## Preparando o ambiente

O ambiente de desenvolvimento suportado é o Lyra OS ou o openSUSE Leap 16.1.
Clone o repositório e execute o bootstrap como usuário comum:

```bash
git clone https://github.com/lyra-os-linux/lyraos-desktop.git
cd lyraos-desktop
./scripts/bootstrap-development.sh --dry-run
./scripts/bootstrap-development.sh
```

O modo `--dry-run` mostra as ações antes de modificar o sistema. O script pede
`sudo` apenas quando precisa instalar pacotes ou configurar virtualização; não
execute o próprio script com `sudo`.

As opções disponíveis podem ser consultadas com:

```bash
./scripts/bootstrap-development.sh --help
```

Depois de uma instalação limpa ou troca da máquina de desenvolvimento, siga o
[guia de recuperação da estação](docs/development-workstation-recovery.md)
antes de retomar builds ou publicações.

Veja o [guia de contribuição](CONTRIBUTING.md) para configuração de Git,
GitHub, OBS, Codex e dos demais projetos do ecossistema.

## Gerando e testando a ISO

O caminho recomendado compila a imagem, executa verificações no resultado,
cria um disco virtual novo e inicia a sessão live no QEMU/KVM:

```bash
./kiwi/test/build-and-run-vm.sh
```

Para testar com Secure Boot:

```bash
./kiwi/test/build-and-run-vm.sh --secure-boot
```

O comando faz as três etapas em sequência: constrói a ISO, cria disco/NVRAM
novos e executa a VM. A instância anterior e seus artefatos são substituídos
somente depois que a nova ISO passa pelas validações. Depois de concluir a
instalação, reinicie o guest sem fechar o QEMU: a ISO é usada somente no
primeiro boot da execução e o reinício segue pelo disco instalado, preservando
o estado UEFI desse teste.

Para desenvolvimento, o helper compila e injeta automaticamente o instalador
do workspace, evitando abrir uma versão antiga publicada no OBS. Um candidato
de release deve obrigatoriamente testar o RPM publicado, sem override local:

```bash
./kiwi/test/build-and-run-vm.sh --published-installer
```

Para construir e validar o candidato sem abrir QEMU nem alterar o disco/NVRAM
de uma VM de teste existente:

```bash
./kiwi/test/build-and-run-vm.sh --build-only --published-installer
```

O helper espera KVM disponível para o usuário atual, uma sessão gráfica, 8 GiB
de memória para a VM e espaço para um disco virtual de 24 GiB. Os builds, ISOs,
discos e logs ficam em `kiwi/.kiwi/test-<uid>/` e não são versionados. Use
`--skip-build` para reutilizar a ISO existente em uma VM nova. Execute com
`--help` para consultar os ajustes de disco, memória e CPUs por variável de
ambiente.

O modo `--build-only` também produz o manifesto rastreável ao lado da ISO e
monitora o cache do carregador de bibliotecas do host enquanto o KIWI executa
scriptlets privilegiados. Não invoque `sudo kiwi-ng system build` diretamente
na estação de trabalho: isso pula tanto a proteção do host quanto as validações
posteriores da imagem.

O build precisa de acesso à rede para baixar pacotes e registrar o Flathub na
imagem. O helper recomendado também gera, ao lado da ISO, um manifesto
`*.iso.manifest.json` com versão, commit, data, estado da árvore e SHA-256.

Depois de concluir uma instalação, inicie novamente o mesmo disco, sem anexar
a ISO e sem recriar o disco ou o estado UEFI, com:

```bash
./kiwi/test/build-and-run-vm.sh --boot-installed
```

## Estrutura do repositório

| Caminho | Conteúdo |
|---|---|
| [`kiwi/config.xml`](kiwi/config.xml) | definição da imagem, repositórios e pacotes |
| [`kiwi/config.sh`](kiwi/config.sh) | configuração executada dentro da imagem |
| [`kiwi/root/`](kiwi/root/) | arquivos sobrepostos na raiz da ISO |
| [`kiwi/test/build-and-run-vm.sh`](kiwi/test/build-and-run-vm.sh) | build, validações e execução no QEMU |
| [`release.toml`](release.toml) | fonte única da versão e do nome dos artefatos |
| [`docs/release-versioning.md`](docs/release-versioning.md) | convenção para Alpha, Beta, RC, release, tags e notas |
| [`docs/diagnostics.md`](docs/diagnostics.md) | coleta, anonimização, revisão e compartilhamento de diagnósticos |
| [`performance.toml`](performance.toml) | orçamento de regressão para boot, RAM, instalação, CPU e I/O |
| [`docs/performance.md`](docs/performance.md) | ambiente, repetições, agregação e publicação do baseline |
| [`docs/hardware-matrix.md`](docs/hardware-matrix.md) | matriz reproduzível de validação em hardware real |
| [`installer/`](installer/) | frontend Rust/GTK e núcleo do novo Lyra Installer |
| [`docs/installer-architecture.md`](docs/installer-architecture.md) | arquitetura e gates do Lyra Installer |
| [`docs/installer-state-machine.md`](docs/installer-state-machine.md) | estados, contratos, cancelamento e recuperação |
| [`docs/adr/`](docs/adr/) | decisões técnicas aceitas do instalador |
| [`docs/roadmap.md`](docs/roadmap.md) | metas dos próximos ciclos do Lyra OS |
| [`docs/evaluation/lyra-os-comparative-assessment.md`](docs/evaluation/lyra-os-comparative-assessment.md) | avaliação comparativa e métrica de evolução do projeto |
| [`PROMPT-LYRA-OS.md`](PROMPT-LYRA-OS.md) | especificação de produto da primeira versão |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | preparação da estação e fluxo de contribuição |

## Privacidade

O Lyra OS não implementa telemetria automática. A ferramenta `lyra-report` só
é executada por solicitação do usuário, cria um arquivo local com permissão
restrita, anonimiza a coleta e nunca envia o relatório. O conteúdo saneado é
mostrado antes da confirmação; ainda assim, deve ser revisado antes de ser
compartilhado. Consulte o [guia de diagnóstico](docs/diagnostics.md).

## Contribuindo

Antes de enviar uma mudança, confira o diff, mantenha credenciais fora do
repositório e valide o fluxo afetado. Instruções detalhadas estão em
[`CONTRIBUTING.md`](CONTRIBUTING.md).

## Licença

O código e a documentação próprios deste projeto são distribuídos sob a
[GNU General Public License versão 3](LICENSE) (GPL-3.0). Arquivos e recursos
originados de terceiros permanecem sob as licenças indicadas nos próprios
arquivos ou nos respectivos metadados.
