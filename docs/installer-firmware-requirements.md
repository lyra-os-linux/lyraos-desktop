# Firmware do instalador — Desktop #89 e Ecosystem #25

## Contrato de 19/09/2026

O modo da sessão live define o plano. O serviço reconstrói esse plano com uma
nova descoberta antes de escrever: mudar de BIOS para UEFI (ou o inverso),
forjar a política de boot ou enviar um schema antigo bloqueia a execução.
O schema 4 inclui `firmware`. Firmware desconhecido bloqueia a interface.

| Sessão live | Disco selecionado | Instalação do bootloader |
| --- | --- | --- |
| BIOS | GPT, BIOS Boot de 2 MiB sem filesystem, Btrfs | GRUB i386-pc no disco |
| UEFI com NVRAM | GPT, ESP FAT de 300 MiB, Btrfs | shim/GRUB do Leap, entrada Lyra OS e caminho alternativo |
| UEFI sem NVRAM | mesmo layout UEFI | mesmos arquivos assinados, caminho EFI/boot/bootx64.efi |

A escolha de swap continua disponível nos três modos. A instalação apaga o
disco escolhido, com confirmação explícita; não reutiliza a ESP de outro
disco. Isso mantém o boot independente dos demais discos. Particionamento
manual, RAID e LVM continuam fora do caminho executável da interface.

UEFI executa `shim-install --no-nvram`, inclusive com `--removable`, verifica
os arquivos necessários e compara as cópias de shim/GRUB. Não constrói um GRUB
EFI sem assinatura. Só então tenta montar efivarfs e registrar uma entrada
pelo efibootmgr. Indisponibilidade de variáveis ou recusa de gravação ativa o
caminho alternativo; falhas de shim, arquivos ausentes/inconsistentes e falhas
de desmontagem continuam fatais. Nenhuma entrada de outro sistema é apagada.
O helper `fallback.efi`, que pode tentar cadastrar entradas implicitamente,
é removido da ESP recém-criada; shim, GRUB e MokManager permanecem.

O sistema instalado registra o resultado em
`/var/log/lyra-installer-boot.json`. O modo alternativo grava `UPDATE_NVRAM=no`
para o libbootloader do Leap. BIOS grava `LOADER_TYPE=grub2` e
`SECURE_BOOT=no`; UEFI usa `grub2-efi` e `SECURE_BOOT=yes`.
Secure Boot requer UEFI. Intel TDX não é requisito do instalador.

A receita mantém `firmware="uefi"` e explicita `eficsm="true"`, que habilita
o caminho BIOS da mídia ISO conforme a
[documentação KIWI](https://osinside.github.io/kiwi/image_description/elements.html).
O layout BIOS/GPT segue a
[documentação GRUB](https://www.gnu.org/software/grub/manual/grub/html_node/BIOS-installation.html).
A conclusão anterior de que `firmware="uefi"` sozinho excluía BIOS foi corrigida.
O bloqueio deliberado no planejador de 15/09 foi substituído por caminhos de
instalação específicos; sua evidência antiga era somente de descoberta.

## Evidência de componentes em 19/09/2026

Quatro VMs descartáveis passaram por instalação real dos arquivos de boot e
uma segunda inicialização pelo disco, sem `-kernel` nessa segunda etapa:

- SeaBIOS: GRUB BIOS, sem ESP ou acesso a efivarfs;
- OVMF: entrada NVRAM criada e boot UEFI;
- OVMF com `efi=noruntime` durante a instalação: relatório de indisponibilidade
  de variáveis e boot pelo caminho alternativo;
- OVMF com chaves SUSE: boot com shim/GRUB assinados e kernel confirmando
  `secureboot: Secure boot enabled` e lockdown.

Kernel Leap `6.12.0-160100.4-default`, GRUB `2.14-160100.2.3`, shim
`16.1-160100.2.1`, disco sparse de 40 GiB, 2 vCPUs e 2 GiB de RAM.
A fixture contém apenas ferramentas públicas e um initramfs de prova;
configurações pessoais, contas e banco RPM do host não são copiados.
O teste destrutivo exige marcador na linha do kernel e serial específico do
disco virtual. Discos, variáveis privadas e initramfs são removidos ao terminar.

Reproduzir em Leap com ferramentas correspondentes instaladas:

```sh
python3 scripts/check-installer-boot-vm.py \
  --kernel /boot/vmlinuz-6.12.0-160100.4-default \
  --modules-dir /usr/lib/modules/6.12.0-160100.4-default \
  --output-dir /tmp/lyra-installer-boot-evidence \
  --case bios --case uefi --case uefi-no-nvram --case secure-boot
node tests/installer-firmware.mjs
```

Os testes unitários cobrem layouts com/sem swap, fstab BIOS, revalidação,
falhas de NVRAM, boot incompleto e limpeza. A interface tem teste comportamental
em português, inglês e espanhol, incluído no CI.

## Gates restantes

Esses ensaios não qualificam uma ISO completa, sessão GNOME, instalação pela
interface, Snapper/rollback, firmware físico ou atualização posterior do
bootloader. O RPM `lyra-installer-0.1.0-lp161.34.1` foi promovido pelo
[pedido OBS 1379053](https://build.opensuse.org/request/show/1379053), com
assinatura, origem e dependências verificadas; 124 testes passaram no staging
e no release. Falta incluí-lo na candidata e repetir instalação e boot dos três modos no checksum exato da ISO. Secure Boot
com OVMF/chaves Microsoft e hardware físico também continua no gate da imagem.
A issue #89 permanece aberta até a integração/qualificação aplicável.

Reversão: reverter este conjunto de alterações e reconstruir o RPM/candidata
antes de distribuição; não houve instalação do pacote ou mudança no firmware
do host. Não reverter apenas o serviço: interface e serviço devem compartilhar
o schema do plano.
