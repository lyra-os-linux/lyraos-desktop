# Recuperação autorizada depois de corte real da VM

Resultado final PASS: 744 testes, 180 controles na VM (6 pré-corte + 12 pós-boot
por caso), 40 leitores de restauração e dez adicionais. Todas as dez VMs OFF,
limpezas e poweroffs/encerramentos finais 0. Sete estados bloqueados recuperados
e três estados sem marcador recusados antes de autorização.

Continua o ensaio parental-owner-cut acrescentando recuperação autorizada,
repetição idempotente e nova tentativa PAM. Usa os mesmos modelos Operations
e Withdrawal, sem alterações de produção. Verificador:
`python3 docs/evidence/parental-owner-recovery/verify-evidence.py`.

## Benefício e escopo

A prova anterior conferia somente inspeção e autorização negada após o corte.
Agora, uma autorização nova deve concluir o estado negativo incompleto,
retirar a prova positiva e conservar a negação. A recuperação concluída deve
aceitar uma repetição da mesma operação com autorização nova sem regravar os
arquivos ou adotar temporários. Isso é recuperação da retirada de admissão;
não é quiescência, enrollment ou permissão para mutação Unix.

São necessários novos cortes porque os overlays anteriores já tinham sido
restaurados. Dez overlays independentes reproduzem os pontos de publicação do
primeiro marcador e do registro de operação, e unlink da prova antes/depois de
fsync. Esse novo ensaio acrescenta quatro controles pós-boot por caso. A
instalação/checkpoint continuam duráveis antes do worker; não se introduz sync
extra depois da pausa. QEMU/disco são conferidos por cmdline/pidfd antes de
SIGKILL, com retorno -9; o mesmo overlay é relançado com UUID real novo.

## Autorização e resultados esperados

A autorização inicial antes do corte não é reaproveitada. Um coordenador novo
chama resume depois do boot; seu callback confirma todos os campos imutáveis
do owner planejado: identidade, operação, proof hash/snapshot e inventário.
O callback consegue tomar os locks reais exclusivamente sem contenção,
comprovando que a autorização ocorre fora dos locks. É callback confiável da
fixture, não uma interface ou autorização Polkit de produto.

Com marcador durável, exige retorno AdmissionWithdrawnNoQuiescence, owner
retired/revision 3, journal legado retired/revision 2, marcador legado
blocked/revision 1 e prova positiva ausente. Os bindings continuam os mesmos.
Uma segunda instância de coordenador solicita autorização de novo e repete a
operação. Hash, inode, proprietário, permissões e tamanho de TODOS os arquivos
ficam iguais ao estado concluído. Nova tentativa de user@1002 continua negada
com 224/PAM e causa exata do módulo; a conta vizinha mantém PID e prova.

Sem o primeiro marcador persistido, mesmo um callback que aprovaria não é
chamado: resume e sua repetição retornam RecoveryRequired. Os arquivos e o
manager ordinário já admitido ficam iguais. Não há promoção de temporário,
reconstrução de operação ou confirmação de retirada inexistente.

Os temporários do corte permanecem idênticos, mesmo quando contêm payload
completo. O protocolo consulta somente nomes canônicos e conclui a operação
verificada; limpeza de órfãos não faz parte desta API.

## Restauração, risco e limites

O risco é corromper um overlay ou deixar a fixture após falha. A reversão é a
limpeza limitada ou descarte depois de conferir o backing raw. Quatro leitores
independentes e um adicional por caso verificam restauração da fixture. Não é
rollback integral de filesystem; a estação não é alterada. O driver arquivado
host-run.py usa caminhos/runtime do laboratório, não é instalador de produção.

SIGKILL encerra QEMU e perde memória do guest; host/cache permanecem vivos.
Não qualifica falta física de energia, todos os erros de armazenamento/fsync,
interrupções durante a própria recuperação ou proteção antirollback por root.
Não qualifica produtores globais, daemon de produto, PAM geral/D-state,
transporte/Polkit/UI ou candidata ISO. Controle parental integral continua
NO-GO; #6 e #102 seguem abertos. Próximo: consolidar estas provas e revisar os
gates restantes para integração e ADR. Interrupções durante a recuperação
permanecem uma lacuna específica; esta prova cobre a retomada concluída e seu
retry, sem declarar todas as fronteiras do ciclo qualificadas.
