# Interrupção do registro de aceitação nas fronteiras de persistência

PASS local: quatro VMs descartáveis independentes, 744 testes da suíte,
88 controles na VM (13 antes + 9 depois por caso), 16 leitores independentes
de restauração e quatro leitores adicionais. Todas as VMs terminaram OFF.
Verificador: `python3 docs/evidence/parental-pam-atomic-cut/verify-evidence.py`.

A prova cobre a substituição de `intent` por `accepted` depois de um único
StopUnit. Seu benefício é demonstrar que uma gravação interrompida não converte
uma resposta de IPC antiga ou um temporário em autoridade para agir no boot
seguinte. Nenhum módulo de produção foi alterado.

## Método

A fixture estabelece a durabilidade da instalação ANTES da retirada de
admissão. O checkpoint contém fontes instaladas e artefatos negativos, e é
gravado ANTES de executar o worker. O worker usa o `RegistryStore._atomic`
existente, cujo hash é conferido com a fonte arquivada. A instrumentação local
intercepta somente os syscalls dessa escrita accepted; não substitui o algoritmo
nem simula o resultado de um syscall.

Na escrita parcial, realiza um os.write real de metade do payload e pausa
antes da próxima iteração. Nos outros pontos, pausa imediatamente após o
syscall real de fsync do temporário, rename ou fsync do diretório. Publica
contadores e observações em /run (tmpfs), usando as operações originais para
essa notificação, e aplica SIGSTOP ao próprio worker. Não há gravação/fsync de
checkpoint ou auditoria em disco depois do ponto de pausa. A auditoria anterior
já havia registrado o retorno de UM pedido StopUnit.

O host confere os marcadores e o serial do convidado, boot, worker parado,
auxiliar PAM vivo, MainPID 0 e job pendente. Valida a linha de comando do QEMU
e seu disco, abre pidfd e aplica SIGKILL somente àquele processo. O QEMU termina
com -9; não há shutdown do convidado. Relança o MESMO overlay, confirma UUID
real diferente e verifica as fontes instaladas antes dos testes de admissão.

## Resultados observados

| Corte | Canônico antes do corte | Canônico após novo boot | Temporário após novo boot |
| --- | --- | --- | --- |
| Meio da escrita | intent | intent | Ausente |
| Após fsync do temporário | intent | intent | Payload completo, ignorado |
| Após rename, antes do fsync do diretório | accepted | intent | Payload completo, ignorado |
| Após fsync do diretório | accepted | accepted | Ausente |

O caso rename voltou de accepted para intent. O teste permite qualquer uma
dessas duas versões inteiras nessa fronteira, mas exige accepted após fsync
do diretório. Um temporário completo não é promovido, adotado ou interpretado
como aceitação. O nome histórico do controle
`real-new-boot-keeps-old-accepted-effect-and-negative-artifacts` é herdado do
ensaio anterior: o controle canônico separado verifica a fase efetivamente
observada neste ensaio, inclusive intent.

Em todos os casos, dois consumidores novos recusam RecoveryRequired antes de
solicitar autorização, sem pidfd herdado, reutilização de job ou StopUnit novo.
Os bytes dos arquivos em effects permanecem iguais durante essas consultas.
Provas, ledger e máscara mantêm hashes/inodes/permissões/proprietários.
A máscara nega partida; o teste causal com a mesma máscara guardada/recolocada
nega PAM com 224, e user@1002 também é negado. A conta vizinha continua admitida.

## Restauração, risco e limites

As quatro limpezas retornam 0. Os leitores verificam restauração e remoção do
perfil, marker, effects e notificação; SELinux volta ao Permissive original.
Os quatro poweroffs e encerramentos finais retornam 0. Os discos são overlays
com backing raw previamente conferido. A estação não foi alterada.

O risco é corromper o overlay ou deixar uma fixture experimental após falha.
A reversão é a limpeza limitada ou descarte do overlay depois de conferir o
backing; não é rollback integral de filesystem. `host-run.py` arquiva o driver
local, cujos caminhos/runtime e imagem de base pertencem ao ambiente de teste;
a evidência não é um instalador de produção.

O host/cache permaneceu vivo: SIGKILL do QEMU não qualifica falta de energia
física do armazenamento. Tampouco cobre interrupções das escritas de origem,
intent, owner/retirada de admissão, todas as combinações de erro de I/O ou
rollback por root. O ensaio não autoriza recuperação entre boots nem qualifica
daemon de produção, PAM geral/D-state ou cobertura global.

Controle parental integral permanece NO-GO; #6 e #102 seguem abertos. Próximo:
aplicar a mesma prova às gravações de origem e intent, antes do pedido StopUnit.
