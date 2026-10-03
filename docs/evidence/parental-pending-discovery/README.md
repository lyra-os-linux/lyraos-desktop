# Descoberta de produtores pendentes — 2026-10-03

Etapa experimental isolada: identifica automaticamente os dois produtores D-Bus
pendentes antes de adquirirem seus nomes, sem registrar manualmente suas observações.
23 controles nativos passaram na primeira execução; a suíte Python completa foi
executada novamente, com 504 testes aprovados, incluindo 8 novos testes do núcleo.

`discovery.py` captura todos os processos do UID alvo antes de qualquer parada,
fixa sua identidade com pidfds, valida as observações e revalida população, versão
e identidade antes de agir. `proc_inventory.py` consulta /proc e systemd reais;
confere quatro UIDs, executável (dispositivo, inode e hash), argumentos, instante
de criação, cgroup, MainPID, unidade e fontes root do catálogo fechado. Processo
não reconhecido ou executável com permissões inseguras causa recusa antes da parada.
O backend e sua construção pertencem à autoridade root confiável da fixture.

A recaptura tem limite de rodadas (1–4) e população (até 64 processos). A matriz
usa duas rodadas. Um produtor conhecido surgido entre lotes é descoberto e parado;
atividade que reaparece a cada lote esgota o limite e retorna bloqueio. Uma nova
tentativa autorizada drena o remanescente. Não há promessa de prazo global de
parede ou de ausência contínua de atividade depois da captura final.

Os produtores tardios são iniciados diretamente por systemctl pela fixture root,
não por novas solicitações D-Bus enfileiradas. O controle de resposta omitida
executa uma parada real bem-sucedida e faz o backend retornar False; não reproduz
uma desconexão real de transporte. O campo herdado
`transport_failure_controls_tested` deve ser lido com essa limitação nesta matriz.
Os dois clientes pendentes originais terminam com ativação cancelada.

As rotas retiradas permanecem indisponíveis, os registros de propriedade e
negação conservam bytes/inodes, e os processos/manager do UID 1000 e o broker
compartilhado mantêm seus PIDs. A descoberta recusa cobertura global: não é um
emissor de inventário completo e não qualifica adaptadores de produção.
Controle parental integral continua NO-GO; #6 e #102 permanecem abertas.

A restauração independente confere PAM, arquivos de contas, fontes vendor,
ausência dos caminhos experimentais, processos/sessões alvo e unidade transitória
extra. SELinux fica Permissive, GDM desligado e SSH desativado, como na base de teste.
Helpers, logs e backups root da VM permanecem; não é rollback de todo o disco
nem auditoria completa de kernel. Nenhum RPM foi instalado. VM desligada, QEMU rc 0.
Host, receitas, PAM de produto, RPM, OBS e ISO não foram alterados.

`result.json` vincula hashes das fontes executadas; `provenance.json` vincula
artefatos, testes e execuções de restauração/desligamento. `restore-extra.py` foi
executado separadamente após a matriz e tem sua própria evidência independente.
A suíte Python foi executada no worktree, sem alegação de export limpo.

Verificação offline: `python3 docs/evidence/parental-pending-discovery/verify-evidence.py`.
Próximo gate: autoridade confiável para inventário/cobertura dos produtores,
com descoberta qualificada além deste catálogo fechado.
