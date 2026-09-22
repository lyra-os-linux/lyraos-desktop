# D-Bus e ativação pelo gerenciador restrito — 22/09/2026

Continuação dos [recursos de sessão](../parental-services/README.md).
Ensaio exclusivamente na VM descartável; não instala proteção no host ou ISO.

## Resultado

D-Bus, seu launcher e systemd-user permanecem no contexto
`lyra_parental_u:lyra_parental_r:lyra_parental_probe_t:s0`, UID1003.
O tmpfiles termina com status0. Um cliente aprovado dentro desse contexto
lista os serviços D-Bus, incluindo systemd1. O mesmo UID através do harness
externo, no domínio `unconfined_service_t`, é rejeitado por `dbus:send_msg`.
O cliente restrito continua funcionando após a rejeição. Isso é uma negação
específica de comunicação entre esses domínios, não prova de isolamento de
todos os usuários nem de todas as interfaces.

A conta comum inicia o gerenciador e usa seu D-Bus normalmente. Pelo próprio
systemctl restrito, a conta supervisionada inicia a unidade de teste aprovada,
mas recebe 203/EXEC ao tentar true genérico, bash e Python. O positivo imprime
UID e contexto no journal. Os mesmos quatro serviços executam na conta comum.
As unidades são criadas por root apenas para o teste e removidas no final.
Não é ainda ensaio de toda ativação D-Bus, unidades transitórias, unidades
criadas pela criança ou tentativa de alterar o contexto de execução.

## Permissões e uma falha encontrada no diagnóstico

`domain.cil` mantém os três tipos oficiais de executáveis de serviço dentro
do domínio restrito: `dbusd_exec_t`, `systemd_tmpfiles_exec_t` e
`systemd_systemctl_exec_t`. Adiciona comunicação local necessária, leitura e
monitoramento das configurações/diretórios de serviços e operações status/start
nas unidades `systemd_unit_file_t`. A regra abrange esse tipo de unidade;
a proteção contra execução não aprovada continua sendo aplicada ao processo.
Não autoriza executar genericamente bin_t, shell_exec_t ou lib_t sem transição.

O primeiro broker aparentemente funcional registrava **Unknown class dbus**,
e o gerenciador **Unknown class system**: o domínio não conseguia ler as
classes em selinuxfs. Esse resultado foi rejeitado. Depois da leitura, faltava
escrever as consultas nos arquivos access/create. A revisão permite consultar
compute_av/compute_create, sem setenforce/load_policy/setbool; o resultado de
sesearch está registrado. Também permite criar sockets com o contexto calculado,
mensagens/aquisição de nomes entre processos do próprio domínio e reload do
próprio gerenciador, necessário a set-environment. Não é uma política final
por aplicativo ou por método D-Bus.

`diagnostics-class-read-before.json` mostra o falso positivo inicial;
`diagnostics-av-query-before.json` mostra a consulta negada após reconhecer
as classes. `recovery.json` preserva o diagnóstico de um encerramento que
excedeu o timeout. O script de diagnóstico foi corrigido para salvar evidências
e restaurar logging mesmo se a parada demorar; uma limpeza emergencial foi
limitada ao user@1003 da fixture. Os resultados finais abaixo foram coletados
com dontaudit normal, fora do diagnóstico, sem Unknown class no journal.

## Evidências finais

- `broker-regression.py` / `broker-result.json`: positivos restrito/comum,
  negativo externo, recuperação, três processos com contexto conferido e
  permissões de consulta da política. Hash da política registrado.
- `service-regression.py` / `service-result.json`: oito ativações nas duas
  contas e conferência dos resultados, contexto do positivo e tmpfiles.
- `execution-result.json`: onze cenários anteriores mais duas verificações
  preparatórias, pelo [script de regressão](../parental-services/execution-regression.py).
- `write-exec-result.json`: escrita de cópia e memfd mantém execução e mmap
  executável negados; [script](../parental-services/write-exec.py).
- `admission-result.json`: doze cenários da entrada PAM real, incluindo falhas
  e recuperação; [script](../parental-services/real-admission.py).

O cliente aprovado é uma cópia de busctl preparada por root em
`/opt/lyra-parental-probe/busctl`, rotulada com o tipo de executável de teste.
`setup-client.py` documenta essa preparação, não idempotente. O cliente original
não recebeu aprovação genérica nem houve mudança de pacotes. Reaplicar o rótulo
da cópia se a fixture for relabelada; não confundir essa aprovação manual com
a lista de aplicativos do produto.

Os testes usam enforcing durante as operações. Restauram permissive para
limpeza da fixture; o encerramento completo em enforcing ainda precisa de
qualificação. Os arquivos JSON também incluem comandos auxiliares; não somar
linhas como se todas fossem cenários independentes de segurança.

## Limites e retomada

Os geradores de ambiente/autostart ainda são negados, assim como acesso ao
barramento de sistema e outros recursos da sessão. Sem qualificação GNOME,
portais ou aplicativos reais. Mesmo UID fora do domínio ainda executa Python:
a cobertura de GDM/TTY/SSH/cron/lingering não está concluída. IDs/contextos
permanecem fixos de fixture; identidade de produção e recuperação pendentes.

Próximo: ativação D-Bus e unidades transitórias adversariais, encerramento em
enforcing, geradores essenciais com aprovação específica e integração das
entradas da sessão GNOME. Não liberar execução ampla de lib_t para resolver
os geradores. Issues #6/#102 seguem abertas; nada para OBS ou ISO nesta etapa.

VM desligada após sync. Checkpoint persistente mais recente:
`analysis/2026-09-22/parental-broker/system-checkpoint.raw`, não versionado.
Launcher/control continuam em `analysis/2026-09-21/parental-selinux/`.
A política precisa ser carregada com o mesmo nome de módulo anterior,
`/tmp/lyra-parental-probe.cil`, para substituir a revisão e não duplicar tipos.
