# Paradas com resposta incerta — 04/10/2026

Implementação isolada do estado técnico de parada, vinculada à operação negativa
já existente. **658 testes Python (20 novos) e 19 verificações na VM passaram.**
Quatro leitores independentes confirmaram a restauração; QEMU saiu com código 0.
Sem integração em produto, publicação ou qualificação do controle parental inteiro.

`effects.py` reutiliza Operations, Inventory e Withdrawal. Grava intenção antes
do IPC, com escrita atômica e fsync do armazenamento histórico. Usa diretório e
lock estáveis próprios para evitar promover a classificação SH do adaptador a
EX. Identidade, operação, prova, revisão/digest do inventário, recurso, digest do
protocolo e boot ficam vinculados. Registro existente impede nova submissão.
Fases: intent → accepted/uncertain → observed-drained. Nenhuma fase remove
negação, máscaras ou autoriza admissão. O journal não contém PIDs ou comandos.

`jobs.py` encaminha exclusivamente as paradas fechadas do adaptador existente.
Resposta válida registra o objeto job; ausência, resposta inválida ou exceção
conserva incerteza. Aceitação não comprova saída. Reconciliação exige autorização
nova fora dos locks, verifica novamente owner e inibições e observa drenagem,
sem reenvio. Mudança de boot exige recuperação explícita. Objetos/factories e
callbacks são de manutenção root confiável; não constituem API GUI/Polkit pronta.
O lock EX do journal é liberado antes do IPC; o adaptador histórico ainda pode
reter seu lease SH de classificação durante o comando.

`backend.py`, restrito à VM descartável, usa StopUnit por D-Bus com modo `fail`,
sem substituir outro job. O retorno de StopUnit é um caminho de job, conforme a
[interface upstream do systemd](https://github.com/systemd/systemd/blob/main/man/org.freedesktop.systemd1.xml).
Drenagem exige estado inactive/failed, Unit.Job zero, MainPID zero para serviços,
cgroup original ausente ou cgroup.events populated=0, e saída dos processos
originalmente fixados por pidfd. Não infere drenagem só pela remoção do job ou
pela propriedade ControlGroup vazia após a saída. cgroup.events inclui a árvore;
a fixture exercita pai e filho no mesmo cgroup, não subgrupos delegados.

A matriz reutiliza GuardedExecution/MaskedSources, classificação, inventário,
OwnedInhibitions/CheckedMasks e journal de retirada anteriores, sem alterá-los.
Antes de cada envio, tenta iniciar os três produtores já mascarados, intercalando
ativação recusada entre conferência e IPC. É uma interleaving observada, não prova
de todas as corridas. StopUnit por nome continua sem condição atômica de PID.

O emissor C `drop-stop.c` envia e flushes StopUnit, aguarda brevemente e fecha
sem processar/ler a resposta. Não simula perda após chamada síncrona concluída.
A observação independente encontra job pendente, deactivating e cgroup populado;
pai e filho do `probe.c` retardam saída após SIGTERM. O journal fica uncertain;
recuperação negada e repetição não enviam outro pedido. Novo objeto reconstruído
lê os arquivos, autoriza novamente e observa ambos encerrados. Isso não é teste
de queda de energia, reboot, disco corrompido ou antirollback.

O timer é parado antes do serviço; a falha parcial deixa tick.service ativo e
bloqueado. Após reconciliar plain.service, um lote novo e explicitamente menor
para tick.service exige autorização nova e referências válidas. Não enfraquece
GuardedExecution para aceitar serviços já inativos. Foram preservados o PID do
manager e do serviço da conta comum e os bytes de sua prova. A negação do alvo
permaneceu causal no PAM (status 224). Não alegamos preservação medida do PID do
broker compartilhado nesta matriz.

## Evidências e tentativas

`result.json` e `executions.json` correspondem exatamente às 19 verificações;
`effect-state.json` arquiva as três fases finais antes da remoção da fixture.
`python-suite.txt`, `provenance.json` e `verify-evidence.py` permitem conferir
fontes, retornos, hashes e restauração.

- `failed-preflight-1`: dependência dbus-adapter.py ausente; execução abortou
  durante importação, antes da instalação de fixtures. Código/resposta arquivados.
- `failed-native-1`: leitor da VM interpretava propriedades escalares como
  listas; timer aceito permaneceu conservadoramente accepted. Asserção posterior
  do ensaio falhou; cleanup foi bem-sucedido. Fontes, journal e saída preservados.
- Matriz final: leitor distingue propriedades escalares de argumentos de método;
  19 verificações, cleanup e leitores independentes passaram, sem normalização
  dos registros de falha.

VM /root/unit-stop-jobs, prefixo lyra-unit-stop-jobs-, ledger reservado e journal
/var/lib/lyra-unit-stop-effects-test. Marcadores kernel, root e serial do disco
conferidos. PAM bytes/modo, contas e fontes anteriores preservados; unidades,
máscaras, probes, efeitos, ledger, inventário, registry/roles/proofs/module e
linger removidos; managers, sessões e cgroups das fixtures drenados. Baseline
Permissive restaurada. Helpers/arquivos diagnósticos permanecem; não é rollback
de todo o filesystem. Restauração da VM não equivale a teste da recuperação de
uma máquina de produção.

## Próximo aceite

Qualificar referências de produtor quando não há MainPID ativo: estados cold,
saída durante captura/autorização, serviço PAM e reativação indireta. Conferir
quais casos upstream resolvem e conservar recusa onde a origem não é demonstrável.
Não criar PID inventado nem aceitar journal completed como cobertura.

Cobertura global, serviços root compartilhados, notify-reload/capabilities,
subgrupos delegados/threads, persistência/antirollback, NSS, GDM, Polkit e ISO
permanecem pendentes. #6/#102 continuam abertas; controle parental integral
**NO-GO**. Produto, host, receitas PAM, RPM, OBS e ISO não foram alterados.
