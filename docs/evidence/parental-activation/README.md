# Ativação D-Bus, unidades transitórias e encerramento — 22/09/2026

Continuação do [broker restrito](../parental-broker/README.md), exclusivamente
na VM descartável marcada `lyra.parental-selinux-test=1`.

## Mudança e resultado

O broker precisava consultar e iniciar unidades transitórias no gerenciador da
própria conta. `domain.cil` acrescenta somente `system:status/start` entre
processos do próprio domínio à política anterior. Essas operações não aprovam
os executáveis solicitados; a restrição de execução permanece aplicável.

`service.c` implementa um serviço D-Bus mínimo que registra seu nome e imprime
UID/contexto. Duas cópias idênticas (SHA256 conferido pelo teste), root e 0755,
recebem rótulos diferentes: uma aprovada, outra bin_t. A ativação via
StartServiceByName executa a aprovada no contexto restrito; a outra falha
203/EXEC. Na conta comum ambas ativam, excluindo falha do programa ou do
mecanismo de ativação como explicação para a negação.

StartTransientUnit também inicia o programa aprovado. Uma unidade transitória
que solicita Python recebe 203/EXEC; a conta comum executa Python. Uma segunda
unidade solicita **um executável aprovado** com SELinuxContext apontando para
unconfined_u:unconfined_r:unconfined_t:s0. Na supervisionada, a troca é negada
na etapa SELINUX_CONTEXT (229), antes da execução. Na comum, o mesmo pedido
executa e imprime o contexto solicitado. Usar o executável aprovado nesse caso
permite distinguir a negação da troca de contexto de uma negação antecipada
do caminho de Python.

Os dois gerenciadores são parados ainda em enforcing: o comando termina dentro
do timeout de 12s, o serviço fica inactive e MainPID=0. Permissive é restaurado
apenas na limpeza final. Isso cobre esse encerramento automatizado da fixture,
não todos os fluxos de logout de GDM/GNOME, reinicialização ou encerramento
com aplicativos reais e operações pendentes.

## Validação e reprodução

`exercise.py` / `result.json`: 19 verificações passaram, incluindo preparação,
positivos/negativos de ativação, contexto, ausência de Unknown class e estados
de parada. Não são 19 técnicas independentes de evasão. Os comandos e journals
completos estão preservados. As definições D-Bus são criadas por root para o
ensaio e removidas no finally; não são arquivos escritos pela criança.

A preparação `setup.py` requer a fonte `service.c` em
`/tmp/lyra-parental-service.c`, cabeçalhos/libsystemd e os pré-requisitos da
fixture anterior. Compila com -Wall -Wextra -Werror e rotula somente as duas
cópias de teste em /opt/lyra-parental-probe. Não é idempotente nem instalador
do produto. Carregar a política mantendo o nome de módulo
`/tmp/lyra-parental-probe.cil`. Os rótulos locais precisam ser reaplicados se
a fixture for relabelada.

A passagem de argumentos para busctl usa `--` antes do comando para preservar
`-c` de Python como dado. Resultados de versões preliminares do harness não
foram usados como aprovação. O resultado final exige o código 203 na negação
de Python e identifica a etapa da tentativa de mudar contexto no journal.

Regressões finais também passaram, com a mesma política: onze casos de execução
mais duas verificações preparatórias em `execution-result.json` (hash da
política conferido); arquivo/memfd em `write-exec-result.json`; doze casos de
admissão e recuperação em `admission-result.json`. Scripts de reprodução em
[execução](../parental-services/execution-regression.py),
[escrita](../parental-services/write-exec.py) e
[admissão](../parental-services/real-admission.py).

## Pendências

Ainda faltam arquivos de unidade criados pelo processo restrito, geradores
essenciais com aprovação específica, sessão GNOME/GDM/portais e aplicativos
reais, entradas TTY/SSH/cron/lingering, identidade de produção e recuperação.
Mesmo UID fora do domínio ainda executa Python. Não há proteção completa da
conta ou GNOME qualificado. Não liberar execute_no_trans de lib_t para resolver
os geradores. Issues #6/#102 abertas, sem alteração de receita/OBS/ISO.

VM desligada após sync; checkpoint persistente mais recente em
`analysis/2026-09-22/parental-activation/system-checkpoint.raw` (não versionado).
Launcher/control continuam em `analysis/2026-09-21/parental-selinux/`.
