# Conferência de fontes integrada ao D-Bus — 03/10/2026

24 controles nativos passaram na primeira execução, rc0/stderr vazio/cleanup0.
Suíte completa rerodada: 538 testes Python PASS, incluindo 8 novos testes do
vínculo entre fontes e visão carregada. #6/#102 abertas; parental integral NO-GO.
Sem alterações no host/PAM produto/receita/RPM/OBS/ISO. VM restaurada e desligada.

`binding.py` integra o scanner anterior, sem modificá-lo, ao adaptador D-Bus e à
descoberta de processos pendentes. O plano fechado vincula o snapshot das árvores
`/usr/share/dbus-1/system-services` e `/etc/dbus-1/system.d`, a classificação das
rotas reservadas e o resultado real de ListActivatableNames. Quatro rotas alvo
precisam permanecer ausentes. As árvores têm 22 entradas no snapshot da fixture.
O scanner usa owner/ancestrais root padrão, sem exceções para o sandbox.
O lock permanente root-only da fixture é compartilhado durante os efeitos,
sem ser mantido durante a autorização externa de execute(). Escritores cooperantes
usam o mesmo EX. A autorização interna do adaptador é uma callback de decisão
root estática da fixture, executada dentro do efeito já autorizado; não é uma
segunda interação Polkit sob esse lock. Isso ainda precisa ser desenhado na API real.

Os dois payloads alvo reais estão pendentes antes de adquirir seus nomes; pidfds,
UIDs, executável, cgroup e MainPID são conferidos. Uma rota nova Unclassified é
adicionada por um escritor root sob EX durante a autorização. O plano antigo
retorna Conflict antes de qualquer stop. ReloadConfig real confirma que a rota
fica ativável; um novo plano recusa a fonte não classificada com UnsupportedProducer.
A rota não é ativada: não se executa um payload desconhecido para classificá-la.

Após remoção explícita da rota e ReloadConfig/daemon-reload, uma nova captura
confere fontes e visão carregada e preserva inibição/barreira/journals. Outro
controle adiciona a rota entre dois stops reais: o primeiro tem rc0, a segunda
parada não acontece, o processo restante continua vivo e a operação retorna
Conflict. Essa injeção é manutenção root deliberadamente fora do protocolo do
lock; não prova que um escritor cooperante atravessa SH. Uma tentativa nova,
após reconciliação explícita, encerra o remanescente e verifica os dois pidfds
exited. Nessa parada, um escritor tenta EX e recebe contenção real.

Drenagem e verificação final conferem novamente arquivos, classificação e nomes
ativáveis. O vínculo usa a visão carregada como observação real e recusa mudanças;
esta matriz não força divergência apenas em memória mantendo os arquivos idênticos.
Os testes Python de troca da visão carregada são sintéticos. Reload não constitui
certificado completo de configuração carregada nem elimina toda ativação pendente.
Clientes pendentes originais terminam rc1 com activation request cancelled.
As quatro rotas alvo seguem não ativáveis; peer payloads/manager e broker451
mantêm PIDs, e owner ledger/proofs conservam bytes/inodes.

O scanner inclui bytes das demais fontes dessas árvores para detectar mudanças,
mas a classificação só qualifica o namespace reservado org.lyra.NamespaceDbus.*.
As fontes upstream pré-existentes são observadas, não qualificadas para a conta.
Não foram descobertos todos os diretórios/includes efetivamente configurados no
barramento, fontes de políticas vendor, diretórios de ativação alternativos,
handlers carregados, unidades/timers/cron ou produtores capazes de trocar UID.
As unidades conhecidas são conferidas pelo backend anterior; a árvore inteira
/run/systemd/system não entra no scanner. Snapshot/lista de nomes não é cobertura
completa, prova de ausência contínua nem revisão monotônica/antirollback.
Nenhum produtor novo é considerado suportado só por entrar no hash.

Autorizações são callbacks root de fixture, não Polkit/API de produção. O plano
é transitório, sem publicação Active, journal de fontes ou remoção de barreiras.
Interleavings root são determinísticos, sem qualificação ampla de races/reboot,
perda de transporte, NSS, GDM ou ISO. A fábrica não emite certificado global.

Restauração independente confere PAM/mode/vendor/passwd/group, ausência de rotas,
retirements, binário/policy/unidades, lock novo/rota desconhecida/nome carregado,
ledger/catalog/proofs/registry/module/linger, zero processos/sessões das fixtures,
Permissive/GDMoff/SSHdisabled. Nenhum RPM instalado, broker não reiniciado/parado.
Helpers/backups/logs root ficam na VM; não é rollback de todo disco/kernel audit.
`restore-routes.py` teve a saída independente ampliada após a matriz, antes de
ser executado; o resultado/hash próprios estão no provenance, sem reescrever
hashes da matriz. Depois da execução, foi removida somente uma linha vazia final
do helper de restauração. O hash dos bytes executados é preservado separadamente
e o verificador reconstrói essa única diferença. Nenhuma fonte capturada na matriz
foi modificada depois.

Benefício: impede usar a autorização/plano anterior após mudar fonte ou visão
carregada, mantendo o bloqueio e a conta comum. Risco de recusa em updates ou
fontes upstream com links não qualificados: integração permanece experimental.
Reversão é remoção da fixture/restauração da VM, já executadas; sem pacote instalado.
Suíte executada no worktree, sem alegação de export limpo. Falha preliminar foi
um erro de aspas no script host de transferência, antes de executar a matriz.

Verificação offline: `python3 docs/evidence/parental-namespace-dbus/verify-evidence.py`.
Próximo: determinar as fontes efetivamente usadas pelo barramento/configuração
upstream e classificar rotas além do namespace reservado; recusar inclusão,
precedência ou fonte não suportada. Manter o gate global fechado até qualificar
cobertura e inibição de todos os produtores obrigatórios.
