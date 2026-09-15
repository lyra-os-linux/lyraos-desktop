# Firmware e TDX — Ecosystem #25

A receita GNOME usa `firmware="uefi"`, GPT, ESP e shim do openSUSE. BIOS
legado é uma limitação deliberada desta imagem, não uma detecção de TDX.
Não há requisito de Intel TDX no código do instalador nem na receita KIWI.
TDX é uma tecnologia de máquinas virtuais confidenciais; a descrição upstream
está na [documentação do kernel](https://www.kernel.org/doc/html/v6.16/arch/x86/tdx.html).

Defeito corrigido: a descoberta já informava `StorageSnapshot.uefi`, mas o
planejador ignorava o campo. Uma inicialização em BIOS podia avançar até a
implantação privilegiada, onde a configuração EFI falharia. `PlanBuilder`
agora recusa BIOS; o serviço repete essa validação com uma descoberta atual,
antes de executar qualquer operação. A interface apaga planos anteriores,
desabilita Continuar e explica a exigência em português, inglês e espanhol.

## Evidência local de 15/09/2026

- Teste QEMU com o kernel Leap `6.12.0-160100.4-default`, duas CPUs virtuais
  do modelo Nehalem e 1 GiB de RAM. Esse é o tamanho do ensaio do núcleo do
  instalador, não uma recomendação de memória para o desktop GNOME.
- OVMF normal: descoberta UEFI real, ausência de TDX e plano aceito.
- SeaBIOS: descoberta BIOS real, ausência de TDX e plano recusado por UEFI.
- Um único disco sparse descartável de 40 GiB; nenhuma escrita, inclusive
  conferência do mtime. VMs, variáveis OVMF, initramfs e discos removidos.
- Teste do serviço: uma requisição anterior válida não executa operações se
  a nova descoberta informa BIOS. Teste da UI: rejeição e limpeza de estado
  anterior nos três idiomas, preservando elegibilidade normal em UEFI.

Reproduzir, com kernel/módulos correspondentes e QEMU/OVMF disponíveis:

```sh
python3 scripts/check-installer-firmware-vm.py \
  --kernel /boot/vmlinuz-6.12.0-160100.4-default \
  --modules-dir /usr/lib/modules/6.12.0-160100.4-default \
  --output-dir /tmp/lyra-firmware-evidence
node tests/installer-firmware.mjs
```

Os testes comprovam descoberta e planejamento, sem instalar uma ISO completa.
Não qualificam Secure Boot, reinício do sistema instalado, requisitos mínimos
do GNOME nem todo hardware antigo. Esses gates permanecem para as duas ISOs
GNOME locais, depois das issues e da auditoria Desktop #78, antes da Alpha 8.
Um aviso de TDX isolado não deve ser classificado como causa de falha de boot:
é necessário preservar o log completo e identificar o erro fatal real.

Reversão da correção: restaurar os arquivos alterados no candidato local;
nenhum pacote do instalador foi instalado nesta máquina de trabalho. O ensaio
não alterou BIOS/UEFI do host e não adicionou suporte a BIOS legado.
