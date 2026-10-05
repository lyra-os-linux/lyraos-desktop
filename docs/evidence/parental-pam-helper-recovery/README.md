# Recuperação do auxiliar PAM com origem retida — experimento

Benefício: recuperar uma operação em que o principal verificado encerrou durante
uma autorização, mas o auxiliar PAM permaneceu no cgroup. `recovery.py` mantém
os dois pidfds adquiridos juntos pelo PamExecution anterior. A mesma referência,
fontes, máscaras, boot e observação do auxiliar precisam permanecer válidos.
Parent=1 só é aceito após o pidfd do principal encerrar; nenhum órfão é capturado
por PID, nome ou journal. A referência expira ao sair do contexto.

Cada recuperação exige autorização nova, fora dos locks do journal. O owner
retirado e o catálogo de rotas são validados pelo Effects antes/depois. StopJobs
mantém intenção durável, aceitação e incerteza. Um pedido existente é reconciliado
sem reenvio. Conclusão exige ambos os pidfds encerrados, membros vazios e também
as verificações de job, estado e cgroup do NativeStopBackend. ControlGroup vazio
só é aceito depois do encerramento do auxiliar e ausência de membros. Drenagem
sem intenção existente não cria uma conclusão fictícia.

Risco e reversão: camada experimental em docs/evidence, sem alterações ao guard
PAM, GuardedExecution, Effects ou StopJobs anteriores, sem instalação na estação
ou publicação. Retirar a camada restaura a recusa conservadora anterior. A
fixture C de close_session limitada a 30 segundos e seu marker root são os da
etapa anterior; o controle de admissão permanece intacto. A VM usa overlay sobre
o disco de teste previsto, com markers e serial conferidos antes da mutação.

Limites: a fixture libera explicitamente seu marker após testar que a parada
aceita não basta para concluir. Isso qualifica retenção de origem, autorização,
IPC e reconciliação; NÃO qualifica término forçado de um módulo PAM travado.
Não recupera pidfds após saída do daemon, reboot ou power loss. Não qualifica
PAM geral, controle parental integral ou adapters de produção; #6/#102 abertos.
Também não substitui a classificação global nem o catálogo global de produtores.

A primeira execução teve 17 controles/cleanup=0: a recuperação emitiu um único
StopUnit e recusou conclusão enquanto o auxiliar estava vivo, mas a reconciliação
final recusou ControlGroup vazio após drenagem. Fontes/resultado/resposta e quatro
leitores de restauração dessa tentativa estão em failed-native-1, preservados.
A correção restringe a aceitação de vazio a ambos os pidfds encerrados e membros
vazios; testes específicos cobrem vazio com auxiliar vivo e cgroup divergente.

Resultado final e contagens estão em result.json, python-suite.txt e
restoration-executions.json. Os hashes de fontes e recibos estão em provenance.json.
`python3 verify-evidence.py` verifica o arquivo de evidências; não executa VM
nem transforma resultados de modelo em qualificação de produção.
