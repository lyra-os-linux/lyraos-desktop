# Primeira publicação de origem e intenção interrompida

Resultado final PASS: 744 testes, 176 controles na VM (13 pré-corte + 9 pós-boot
por caso), 32 leitores de restauração e oito leitores adicionais. Todas as oito
VMs qualificadas terminaram OFF. O ensaio inicial do verificador fica arquivado
como FAILED, com quatro leitores de restauração PASS adicionais.

Qualificação local das gravações que antecedem StopUnit. O teste usa oito
overlays independentes: origem e intenção, cada uma interrompida no meio da
escrita, após fsync do temporário, após rename e após fsync do diretório.
Verificador: `python3 docs/evidence/parental-pam-early-cut/verify-evidence.py`.

O benefício é demonstrar que ausência de registro ou um temporário incompleto
não libera admissão, autoriza parada ou permite adotar processos históricos.
Os módulos de produção permanecem intactos. A instrumentação fica restrita ao
worker da fixture descartável.

## Caminho executado e fronteiras

Como no ensaio accepted, a instalação é sincronizada ANTES da retirada, e o
checkpoint é persistido ANTES de iniciar o worker. Usa-se o gravador
RegistryStore._atomic existente, com hash conferido. Os wrappers pausam após
syscalls reais, sem substituir o algoritmo. A escrita parcial envia metade do
payload real. A notificação de pausa fica em /run (tmpfs), e o worker aplica
SIGSTOP a si mesmo. Não há checkpoint/auditoria/fsync em disco após a pausa.

Na gravação de origem, MainPID e auxiliar PAM ainda estão vivos e o worker
não pediu autorização para recuperação nem iniciou uma parada. Na gravação de
intenção, o caminho de recuperação fechado já capturou a origem e aplicou
SIGTERM por pidfd ao MainPID original verificado; conserva o auxiliar PAM vivo.
A autorização prévia do próprio worker ocorreu, mas a publicação de intent
é interrompida antes de retornar ao código que chama StopUnit. Em todos os
pontos, os contadores de entrada e retorno de StopUnit são ZERO.

O host valida root, ambos os marcadores, serial, boot, estado T do worker e
processos na unidade. Para origem verifica MainPID vivo e ausência de job;
para intenção verifica MainPID 0, auxiliar vivo e ausência de job. Valida o
QEMU/disco por linha de comando e pidfd, aplica SIGKILL somente à VM e observa
retorno -9. Relança o MESMO overlay e confirma novo boot UUID real.

## Condições de aceitação

Antes de rename, o canônico deve permanecer ausente. Depois de rename mas
antes de fsync do diretório, permite-se ausência ou o documento inteiro novo.
Depois de fsync do diretório, exige-se documento inteiro publicado. Para origem,
nenhum efeito pode existir. Para intenção, a origem previamente persistida deve
continuar íntegra, e o efeito, se existir, precisa ser intent/revision 1/job null.
Nenhum temporário é promovido ou usado como substituto do canônico.

No novo boot, dois consumidores distintos recusam RecoveryRequired antes de
solicitar autorização. Não herdam pidfds, adotam PIDs/jobs ou enviam StopUnit.
Os bytes em effects não mudam durante as consultas. As fontes PAM/unidades são
conferidas antes dos testes; prova/ledger/máscara mantêm hashes, inodes e
proprietários. A máscara nega partida; o teste causal PAM com a MESMA máscara
guardada/recolocada e user@1002 falham com 224. A conta vizinha permanece admitida.

Nos dois registros, os resultados observados foram: canônico ausente nos
três primeiros pontos, e publicado inteiro após fsync do diretório. Temporários
completos após fsync/rename permaneceram ignorados.

## Falha do verificador preservada

O primeiro caso de intenção foi interrompido pela expectativa errada do
verificador do host de encontrar um job pendente, herdada do ensaio accepted.
Antes de StopUnit, Job era vazio. O driver encerrou sua VM na saída de erro.
Esse ensaio fica FAILED em failed-intent-job-guard/, sem qualificar o corte:
o retorno desse primeiro QEMU não foi arquivado. Após relançar o overlay,
verificações pós-boot e quatro leitores de restauração passaram, limpeza
retornou 0 e poweroff/encerramento final retornaram 0. A expectativa foi corrigida
para Job vazio ou 0. O caso de intenção foi repetido em overlay novo; os quatro
casos de origem já concluídos não foram repetidos.

## Risco, reversão e limites

O risco é deixar configuração experimental ou corromper um overlay. A reversão
é a limpeza limitada ou descarte após conferir o backing. Os discos usam o
backing raw previamente conferido; a estação não é modificada. O driver local
é arquivado em host-run.py; os caminhos/runtime/imagem pertencem ao laboratório.
Não é instalador de produção nem rollback integral de filesystem.

O host/cache fica vivo durante SIGKILL do QEMU: não é falta de energia física
do armazenamento. Não cobre interrupções na retirada/owner, todos os erros de
I/O, proteção contra rollback por root ou recuperação autorizada entre boots.
Daemon de produção, PAM geral/D-state e cobertura global continuam NÃO
qualificados. Controle parental integral NO-GO; #6 e #102 permanecem abertos.
Próximo gate: interrupções na gravação do owner e da retirada de admissão.
