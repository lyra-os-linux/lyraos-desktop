# PAM — saída do principal durante autorização, 05/10/2026

20 testes específicos e 696 testes da suíte passam. A matriz VM passou em
19 controles; limpeza rc0, quatro leitores independentes de restauração rc0,
marker de atraso ausente e desligamento RPC/QEMU rc0. Fontes anteriores de
PamExecution/GuardedExecution/StopJobs permanecem intactas.

A VM reproduziu MainPID=0 e Unit.Job=(0,"/") enquanto o auxiliar PAM ainda
estava vivo, cgroup populated=1 e a sessão não estava drenada. O principal e o
auxiliar já haviam sido identificados e fixados com pidfd antes da autorização.
Sair durante a autorização causou Conflict antes de qualquer StopUnit; uma
captura nova sem principal causou UnverifiedRuntime antes de nova autorização.
Comandos/requests permaneceram vazios e nenhum efeito de parada foi criado.
Prova negativa, ownership e máscaras permaneceram iguais. Após liberar a espera,
o systemd drenou o auxiliar: cgroup vazio, pidfds terminados e observação
quiescente, sem registrar essa limpeza automática como efeito próprio.
Reentrada do alvo foi negada causalmente por PAM224 e o peer permaneceu admitido.

O perfil é o já qualificado em parental-pam-unit-stop. Apenas a fixture C recebeu
uma espera no close_session, limitada a 30 segundos, à conta ordinaryuser e a um
marker regular root-owned sem escrita por terceiros em /run. O prefixo anterior
a close_session é byte-idêntico, exceto pelo include time.h. A referência fixa o
novo fingerprint do módulo e o journal do pidfd/auxiliar medido confirma entrada
nessa espera. A liberação remove o marker; o finally também o remove antes da
limpeza. Esse recurso existe somente no overlay marcado, nunca no host/produto.

O systemd257.13 cria sd-pam para fechar a sessão após o principal terminar:
[exec-invoke.c](https://github.com/systemd/systemd/blob/v257.13/src/core/exec-invoke.c).
A primeira tentativa suspendia o auxiliar por SIGSTOP; ele saiu após o principal
e a condição pretendida não foi mantida. Falha de 12 controles/cleanup0 preservada
em failed-native-1. Um erro de substituição Python causou SyntaxError antes da
fixture; resposta/fonte preservadas em failed-preflight-2. O resultado antigo
lido pelo coletor após esse preflight não é resultado de uma segunda matriz.

Não há revogação nova de auxiliar órfão, adoção de PID nem referência fabricada.
Se o auxiliar não drenar, a operação continua pendente/recusada com autoridade
negativa. Recuperação persistente/antirollback e stops de auxiliares órfãos
continuam pendentes. Pilhas PAM gerais, root compartilhado, notify-reload,
capabilities, threads/subgrupos, NSS/GDM/Polkit UI/privacidade e a cobertura global
não foram qualificados. Controle parental completo NO-GO; #6/#102 abertas.

O overlay novo tem backing original somente leitura; quatro leitores conferem
PAM, sources/accounts, processes/units/ownership restaurados e marker ausente.
Helpers diagnósticos permanecem: não é rollback completo do filesystem.
