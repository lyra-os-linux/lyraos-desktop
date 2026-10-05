# Timeout nativo do systemd com auxiliar PAM retido

Benefício: validar a drenagem quando o callback PAM close_session não retorna
antes do timeout de parada. Os ensaios anteriores liberavam explicitamente o
marker de close; não demonstravam a intervenção nativa do systemd.

A fixture C é a anterior com uma única diferença: limite de 30 para 300 segundos
no callback close_session. Todo o código de admissão permanece idêntico. Marker
regular root-owned/nlink1/sem escrita de terceiros, CLOCK_MONOTONIC e nanosleep
continuam iguais. Código experimental apenas no overlay descartável, sem
instalação na estação ou publicação de pacote.

native-timeout.py captura propriedades efetivas DEPOIS de carregar as máscaras:
TimeoutStopUSec, TimeoutStopFailureMode, SendSIGKILL, FinalKillSignal e KillMode.
Não configura timeout/sinais nem escreve policy da máquina ou VM. Exige timeout
positivo <=95s, terminate, SendSIGKILL=true, SIGKILL9 e control-group. O marker
permanece com o mesmo inode até os pidfds encerrados/cgroup0/job0. O limite de
300s excede a janela máxima de observação (2*timeout+15s); portanto o retorno
normal pelo limite da fixture não pode ser confundido com a drenagem medida.

O principal original é sinalizado via seu pidfd verificado, como nos ensaios
anteriores de saída durante autorização. A parada de recuperação usa uma única
chamada real StopUnit com intenção durável e autorização nova; aceitação com
helper vivo não conclui. Nenhum sinal é enviado ao helper pelo código do Lyra.
O ensaio aguarda a policy existente do systemd, observa Result=timeout e exige
a mensagem de timeout no journal e o log do callback PAM desse PID. O sinal
exato é medido no tracepoint kernel signal_generate: sig9, PID do auxiliar e
common_pid1 (systemd). Uma instância tracefs privada filtra exclusivamente esse
evento; tracing global permanece intacto e a instância é removida ao terminar. Depois reautoriza reconciliação
observed-drained sem reenvio. Marker só removido APÓS toda essa prova.

Preserva masks/ledger/owner/prova negativa/peer e mede reentrada PAM224. Cleanup
é seguido de quatro leitores independentes de restauração; desligamento QEMU
confirmado. Fontes/recibos/resultados/contagens estão arquivados em provenance.json,
result.json, restoration-executions.json e python-suite.txt; o verifier valida
correspondência da evidência, sem executar nova VM.

Risco e reversão: não se acrescenta kill do Lyra ou modifica guard/admissão,
PamExecution/RetainedHelper/Effects/StopJobs. Remover a fixture reverte o ensaio;
a política do sistema permanece a original. O timeout exato é qualificação da
VM/versão/configuração medida, não promessa para todo ambiente. Se SendSIGKILL
estiver desativado ou a unidade não drenar, a recuperação deve continuar pendente.

Limites: auxiliar fechado em nanosleep é interrompível por SIGKILL. Isso NÃO
qualifica tarefa em D-state, módulo arbitrário, processo que escapa do cgroup,
proteção global, reboot, powerloss, antirollback ou daemon de produção. O
controle parental integral permanece NO-GO; #6/#102 abertos. Diagnósticos ficam
no overlay, sem afirmação de rollback integral do filesystem.

Duas tentativas incompletas foram preservadas: failed-native-1 drenou no timeout
mas exigia indevidamente um log de sinal por PID (18 controles/cleanup0); o
systemd257.13 omite auxiliares cujo comm começa com '(' em log_kill. A segunda
ativou temporariamente log debug, mas falhou ao passar boot UUID com hífens ao
journalctl (19 controles/cleanup0). Log info restaurado, quatro leitores PASS em
ambas. A execução final usa boot ID sem hífens e tracepoint kernel; não depende
do log individual omitido e não ativa debug. O nível do manager e o estado de
tracing são conferidos novamente por leitor independente após cleanup.
Fonte primária da omissão: https://github.com/systemd/systemd/blob/v257.13/src/core/unit.c#L4354
