# Saída abrupta em fronteiras duráveis do consumidor PAM

Benefício: conferir a recuperação quando um consumidor perde todos os seus
pidfds/locks antes de registrar completamente a operação. O modelo anterior
só havia encerrado o contexto normalmente. Este ensaio usa processo separado
com `os._exit(91)`, que não executa `finally` nem a saída dos context managers.
O kernel fecha os descritores. Não altera os módulos de autoridade anteriores.

Quatro pontos em crash-worker.py:

- origin-synced: origem configurada persistida, antes da intenção; zero StopUnit.
- intent-synced: intenção persistida, antes de entrar no backend IPC; zero StopUnit.
- request-returned: chamada real retornou job do systemd, mas accepted ainda não
  foi gravado; journal continua intent; exatamente um StopUnit.
- acceptance-synced: accepted persistido, antes da saída dos locks; um StopUnit.

Os hooks cercam o atomic writer existente e o retorno do backend. O trace
root-owned é diagnóstico fsync'd da fixture, não journal de autoridade. O ensaio
confere rc91, ponto exato, ausência do marker do finally e trace com contagem de
entrada/retorno do backend. Um retorno real de StopUnit não é confundido com
journal accepted no cenário request-returned. PID no trace apenas identifica o
processo de ensaio; nunca é referência para recuperar ou sinalizar um órfão.

native-crash.py preserva masks/owner/prova negativa e mede principal/helper com
pidfds independentes de diagnóstico. Os consumidores seguintes são os anteriores
qualificados em parental-pam-daemon-recovery/restarted-reader.py, executados sem
herdar pidfds. Com origem sem efeito: RecoveryRequired antes da autorização,
inclusive depois de cold. Com efeito intent/accepted e auxiliar vivo: Busy antes
da autorização. Após liberar o marker de close_session, autorização negada
preserva o journal; nova autorização permite observed-drained sem outro IPC.
No primeiro cenário o principal ainda vive; apenas manutenção da fixture o
sinaliza por pidfd cujo fdinfo PID confere com o baseline capturado. Não se cria
StopUnit/journal para simular uma parada que nunca foi pedida.

Cada cenário faz setup e cleanup completos no mesmo overlay descartável, com
markers/serial/backing conferidos, SELinux enforcing no caso e quatro leitores
independentes de restauração antes do próximo cenário. Os resultados e recibos
estão em diretórios por ponto. Reentrada PAM224, peer, máscaras e ledger/prova
preservados. A suíte anterior de 744 testes continua passando. O verifier checa
fontes arquivadas/recibos e os quatro resultados, sem executar nova VM.

Risco e reversão: somente código/evidência experimental, sem pacote, instalação
na estação, alteração ao guard PAM, Origins/Restarted/Effects/StopJobs ou timeout
de sistema. Remover a fixture basta para reverter o ensaio. Não reinicia daemon
de produção, não simula power loss/reboot, nem interrupção dentro de atomic
rename/fsync. Nenhum mecanismo antirollback global ou proteção contra root é
alegado. Ainda não qualifica término forçado de PAM realmente travado: o marker
C é limitado a 30s e é liberado pelo ensaio. Proteção integral NO-GO; #6/#102 abertos.
Scripts diagnósticos permanecem no overlay; não é rollback completo de filesystem.
