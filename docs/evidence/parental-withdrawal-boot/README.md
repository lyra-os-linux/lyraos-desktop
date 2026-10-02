# Retirada de acesso comum após reinício real — ensaio isolado

Continua a [retirada durável](../parental-ordinary-withdrawal/README.md). O guard C
PAM e withdrawal.py são os mesmos do gate anterior, sem alterações; referências
e hashes vinculam suas fontes. Helpers novos preparam e inspecionam a VM. Não
instalar o hook ou código de evidência em pacote, estação ou ISO.

## Cenário e sequência

Duas contas comuns JÁ existentes na VM: ordinaryuser UID1002/GID1003 (alvo) e
installeduser UID1000/GID1001 (controle independente). Não se cria, remove,
renomeia ou altera conta/grupo/mapping SELinux. O registro parental fixture
anterior e parentaltest permanecem para reproduzir a pilha, sem ligar lingering
da conta supervisionada nesta etapa. O PAM vendor recebe só o módulo de ensaio.

A preparação cria locks estáveis por UID e declarações positivas distintas,
admite ambos os managers no contexto unconfined esperado e interrompe o
controlador com rc91 logo DEPOIS do fsync do marcador de retirada do alvo.
Ainda não há journal; a declaração antiga permanece íntegra. Ambos os managers
antigos continuam ativos. Habilita lingering para as duas contas e instala um
hook exclusivo da VM antes de logind e dos managers. Segue reinício ORDENADO do
kernel; o launcher -no-reboot sai e o controlador inicia QEMU novamente.

No primeiro boot, o hook coloca SELinux em Enforcing e apenas chama inspect.
Não restaura declaração, não escreve journal, não enrolla e não desbloqueia.
Confere estado persistido (bytes/hash/modo/proprietários/nlink e inode dos locks).
A admissão automática do alvo falha com status224/PAM e causa exata do módulo;
o outro manager comum inicia no contexto esperado. Retry manual do alvo falha
sem trocar o PID do controle. Negação de autorização preserva o estado; retomada
explicitamente autorizada só conclui retirada da declaração alvo e grava
journal2/retired, conservando bloqueio e a declaração/PID comuns independentes.
Uma nova tentativa do alvo continua negada.

No segundo boot real, o hook sai deliberadamente42 DEPOIS de Enforcing e ANTES
de inspect. Marker+journal da retirada permanecem idênticos, o alvo continua
recusado por lingering e retry manual, a outra conta comum inicia normalmente.
Retry autorizado da mesma operação mantém bytes/revisão da retirada e preserva
PID/declaração da comum. Três boot IDs distintos comprovam dois reinícios de
kernel; não confundir com restart de processo.

## Critérios e reversão

17 controles nativos: 4 preparação, 7 primeiro boot, 6 segundo boot. Negativas
PAM exigem MainPID0/status224 e mensagem exata; retries usam cursor de journal.
Admissões comuns exigem PID ativo e contexto unconfined exato. O arquivo de
controle comum e inodes dos locks permanecem iguais entre fases e boots.
inspect é somente leitura; nenhuma capacidade de supervisão é publicada aqui.

Exige root, AMBOS marcadores de kernel e disco serial lyra-admission-test.
Helpers /root/withdrawal-boot, C /root/withdrawal-pam-guard.c, writer V2 histórico
/root/barrier-writer.py. Após preparação, systemctl reboot, relaunch e verify-boot;
a primeira verificação configura fault=true para o segundo boot. Não executar
verify-boot duas vezes no primeiro boot nem tratar o reset da fixture como API.

cleanup.py desabilita/remove o hook e os três linger markers, termina somente
os três usuários fictícios do ensaio, remove índices/locks/markers/journals e
módulo, restaura bytes/modo do PAM original e Permissive da VM. restore-check.py
inspeciona de forma independente managers/runtime/sessões/processos, conta,
PAM/vendor e arquivos de fixture. Backup/helpers em /root permanecem como
evidência. Não alegar restauração de todo arquivo home gerado por systemd-user.

## Limites

Boots ordenados e interrupção após fsync não qualificam queda de energia,
escrita parcial, erro de fsync, falhas ANTES da durabilidade nem rollback total
de armazenamento. Launcher kernel/initrd direto com enforcing=0: hook põe
Enforcing antes de logind, sem qualificar earlyboot, initrd ou candidata ISO.
O helper defeituoso ainda executou setenforce antes de falhar; não extrapolar
para falha anterior ao Enforcing. Sem bootloader, GDM/GNOME completo, password
login, logout/desbloqueio ou aferição etária. Não afirmar que supervisão foi
aplicada ao alvo: só se retirou sua autorização para nova admissão comum.

Não qualifica dois coordenadores concorrentes, revisão monotônica global,
Polkit/transport, update/downgrade/backup ou real lifecycle NSS/reusoIDs. O fim
dos managers antigos no shutdown não prova revogação sem reboot nem cobertura
SSH/cron/D-Bus/unidades sem PAM. all_producer_quiescence/whole_classification/
full_account_protection/power_loss/real_nss_mutations continuam false. Auditoria
do kernel não é inventário completo. Proteção parental completa permanece
NO-GO #6/#102. Nenhum host/receita/OBS/ISO parental alterado.

Próximo: integrar a autoridade negativa ao gate de classificação/coordenador,
qualificar operações concorrentes e produtores reais antes de permitir mutação
Unix ou publicação. Não reduzir REQUIRED, usar zero leases como quiescência ou
recriar a declaração Ordinary em boot/recuperação.

## Resultado de 02/10/2026

17 controles nativos PASS (4+7+6), três bootIDs e dois reinícios reais; ambos
comandos de reboot e três processos QEMU retornaram0. Conta alvo negada por
lingering/retry em ambos; segunda comum admitida e declaração/locks preservados.
Hook normal só consultou; hookfalha42 não alterou dados. Retomada autorizada após
boot somente retirou a declaração alvo; retry idempotente continuou bloqueado.
294 testes Python existentes PASS (sem novos nesta etapa), verificador offline
e diffcheck. Limpeza/inspeção independente PASS e VM desligada. Sem warnings
de backlog no último boot, ainda sem comprovar auditoria completa; isso não é
prova de ausência de AVC. Nenhuma mudança em host/receita/OBS/ISO parental.
