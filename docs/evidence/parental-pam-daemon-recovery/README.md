# Reconciliação PAM após perder o contexto — modelo e consumidores separados

O journal de StopUnit já conserva a intenção/aceitação, mas não uma referência
configurada reutilizável depois da perda de pidfds. `restart.py` acrescenta uma
origem root-owned, gravada atomicamente no armazenamento protegido anterior.
A gravação exige o contexto PamExecution original com ambos os processos vivos,
referência fechada válida, hash do fragmento igual à rota registrada e invocação
não vazia estável. Só ocorre antes da intenção e não sobrescreve origem existente.

A origem liga propriedades históricas e fingerprints à operação retirada, UID,
rota, protocolo e boot. O consumidor reconstrói a referência com o validador PAM
fechado, resolução de identidade e fingerprints atuais, comparando ao registro
original. Não interpreta a máscara como configuração original. Há limite de
8192 bytes, rejeição de campos duplicados e verificação do armazenamento com
owner/mode/nlink/nofollow herdada do Withdrawal. Não é assinatura criptográfica,
proteção contra root nem um mecanismo global de antirollback.

O consumidor novo não abre pidfds, não adota PIDs órfãos e não possui método de
pedido IPC. Só reconcilia um journal já existente depois de provar unidade fria:
MainPID=0, inactive/dead ou failed/failed, Job=(0,'/'), cgroup original vazio,
fontes e máscaras intactas. A invocação deve ser a original ou estar vazia;
systemd limpa InvocationID ao concluir a drenagem. Um identificador não vazio
diferente é recusado. O mesmo snapshot precisa permanecer válido durante uma
nova autorização fora de todos os locks. StopJobs aplica o CAS/observed-drained
anterior, sem reenvio de StopUnit. Origem sem efeito não cria conclusão.

Benefício: um consumidor reiniciado pode confirmar uma parada já drenada sem
inventar autoridade sobre processos restantes. Risco limitado ao modelo:
nenhuma alteração aos guards PAM, Effects/StopJobs ou ao sistema da estação.
Reversão: retirar os novos consumidores mantém a recusa conservadora anterior;
não há restauração de admissão, exclusão de prova negativa ou unmask público.

Ensaios: tests-source.txt contém 28 testes específicos; python-suite.txt registra
744 testes passando. native-restart.py usa overlay descartável com markers/serial
conferidos, SELinux enforcing durante o caso, referências capturadas antes das
máscaras e origem antes de sair o principal. O consumidor original encerra seu
contexto. Execuções separadas de restarted-reader.py não recebem referências ou
pidfds: recusam o auxiliar vivo antes de autorizar, recusam origem com permissões,
owner, hardlink ou symlink inseguros e conservam o journal. Após liberar o marker
da fixture, uma execução com autorização negada mantém accepted; outra autorizada
conclui observed-drained. Um único StopUnit real foi emitido pelo consumidor
original. Máscaras/prova/ownership/peer e recusa de reentrada PAM224 preservados.

Limites: trata-se de processos consumidores experimentais separados, não de um
restart de serviço de daemon de produção. O orquestrador conserva pidfds apenas
para medir/restaurar a fixture; os consumidores novos não os herdam. Unidade
vazia não prova proteção global da conta nem ausência de escape de um produtor
fora do escopo. Não qualifica terminação forçada de módulo PAM travado, reboot,
crash/powerloss ou rollback. A fixture de close_session tem limite30s e seu marker
é liberado pelo ensaio. Controle parental integral permanece NO-GO; #6/#102 abertos.

A primeira execução, antes de acrescentar InvocationID, passou 25 controles e
quatro restaurações; fica arquivada em analysis/2026-10-05/parental-pam-daemon-recovery/
before-invocation-binding. Não é a matriz final. A execução final está em result.json,
com recibos/source hashes/provenance e quatro leitores independentes de restauração.
A VM foi desligada com confirmação do processo QEMU. Scripts diagnósticos ficam
no overlay; não se afirma rollback integral do filesystem.
