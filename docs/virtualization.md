# QEMU/KVM no Desktop Alpha 8

A imagem inclui virt-manager e virt-install, QEMU x86, qemu-img, firmware BIOS e
OVMF, interface GTK/OpenGL e dispositivo de vídeo virtio. O backend libvirt QEMU,
cliente e definição da rede padrão são dependências explícitas da receita:
`onlyRequired` não deve deixar a virtualização dependente de recomendações.

O script de configuração da imagem habilita os sockets locais dos daemons
modulares QEMU, rede, armazenamento, segredos, dispositivos, logs e locks.
Segue o modelo de [ativação por socket do libvirt](https://libvirt.org/daemons.html).
Não habilita listeners TCP/TLS nem cria máquinas ou discos. A rede NAT padrão
vem do pacote openSUSE; o virt-manager pode solicitar sua ativação ao criar uma
VM. Não se inicia um servidor DHCP/bridge automaticamente no boot do Desktop.

A sessão live tem acesso pelo grupo libvirt, como previsto na receita aprovada.
O usuário criado pelo instalador continua no grupo wheel e autentica ações
administrativas com sua própria senha através da regra Polkit já existente.
Não se adiciona o usuário instalado automaticamente ao grupo libvirt nem uma
regra global de autorização sem senha. Cancelar ou negar a autenticação deve
impedir alterações. A senha de root permanece bloqueada.

KVM depende das extensões de virtualização disponíveis e habilitadas no host;
QEMU também oferece emulação. Ausência de KVM não deve impedir iniciar a sessão
Desktop. A conexão local padrão é `qemu:///system`, detectada pelo virt-manager.

## Qualificação

Os testes de contrato verificam composição explícita, separação entre usuário
live/instalado e configuração dos sockets sem inicializar VMs ou redes no build.
A validação de componente deve usar uma raiz Leap 16.1 descartável e pacotes
oficiais assinados, sem modificar libvirt, redes ou VMs da estação.

Na candidata exata, após a auditoria: abrir virt-manager com conta recém-criada,
validar autenticação/cancelamento, criar disco e VM, iniciar a rede NAT, obter
DHCP, conferir DNS/conectividade e console gráfico, testar BIOS/UEFI e persistir
configuração após reboot. Repetir na sessão live. Registrar inventário RPM,
checksum da ISO e capacidades de KVM do equipamento. Uma VM de componente não
substitui essa qualificação.

Reversão: remover esta composição e a chamada ao configurador da receita antes
de gerar uma nova candidata. Não apagar VMs, discos, redes ou preferências de
usuários em instalações existentes.
