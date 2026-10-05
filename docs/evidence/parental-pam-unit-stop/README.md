# PAM — perfil experimental fechado, 05/10/2026

18 testes específicos e 694 testes da suíte passaram. Em um novo overlay
qcow2 descartável, a matriz passou em 16 controles; limpeza rc0, quatro leitores
independentes de restauração rc0 e desligamento RPC/QEMU rc0.

O perfil mínimo anterior omitira pam_selinux close/nottys open, necessário para
preparar o contexto de execução exigido pelo módulo de admissão. O perfil
corrigido acrescenta essas duas linhas do contrato vendor systemd-user e fixa
também o fingerprint de pam_selinux.so. O módulo de admissão continua intacto.
A primeira matriz falha e suas restaurações permanecem em failed-native-1.

O serviço antes admitido foi mascarado e depois parado pelo adaptador e StopJobs
existentes. O processo principal e o auxiliar PAM foram fixados por pidfd;
o auxiliar apresentou UID/GID da conta, grupos vazios, capabilities zero,
executável systemd-executor e pai/cgroup esperados. Autorização negada e alteração
do pai recusaram a parada sem IPC; troca do módulo SELinux durante a captura
recusa a referência. Após parada, ambos saíram, job/cgroup drenaram, a conta de
controle permaneceu admitida e a reentrada do alvo foi recusada causalmente por
PAM (224). A captura geral continua recusando PAMName.

Este ensaio qualifica somente esse perfil fixture e essa combinação de serviço,
auxiliar, credenciais e base. Não qualifica pilhas PAM arbitrárias, produtores
root/compartilhados, notify-reload, capacidades, threads/subgrupos, recuperação
persistente/power-loss, GDM/Polkit/NSS nem cobertura global da conta. O controle
parental completo continua NO-GO; #6/#102 abertas. Não houve alteração parental
no host, no produto, em receitas, RPMs ou OBS. Helpers diagnósticos permanecem no
overlay; não é rollback completo do filesystem. O backing original não foi
alterado pela nova matriz.

Execute verify-evidence.py para conferir as evidências arquivadas; o verificador
não repete a VM nem transforma resultados históricos em qualificação global.
