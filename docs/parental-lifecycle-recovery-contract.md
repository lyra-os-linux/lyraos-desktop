# Contrato de recuperação e ciclo de contas supervisionadas

Status: **proposta para decisão do mantenedor**, 01/10/2026. Complemento técnico
à [ADR 0008](adr/0008-private-age-signal-and-parental-supervision.md), sem marcar
a ADR como aceita. O parecer já aprovado em #10 não precisa ser solicitado
novamente. Aprovar este contrato autoriza a próxima implementação isolada com
contas fictícias; não aprova publicação, aferição, retirada de supervisão nem
proteção completa. #5, #6, #102 e os gates de #2 continuam aplicáveis.

## Decisão recomendada

Adotar um coordenador privilegiado pequeno para o ciclo de identidade,
reaproveitando AccountsService, ferramentas de contas da base, PAM, SELinux,
systemd/logind e Polkit. Manter malcontent/OARS como adaptador onde sua aplicação
for comprovada. O coordenador acrescenta somente a transação, geração,
barreira persistente e reconciliação que os ensaios mostraram faltar.
Não substituir NSS, logind, GDM, cron ou o barramento por implementações Lyra.

A fronteira proposta considera root e o administrador com controle irrestrito
da máquina autoridades confiáveis de manutenção. Não promete impedir que root
altere arquivos, política MAC ou recrie externamente uma conta. O usuário
supervisionado não recebe essa capacidade. Alterações administrativas fora dos
fluxos suportados tornam a associação não qualificada até reconciliação;
recriação idêntica fora do coordenador pode ser indetectável pelo NSS e não
pode ser apresentada como detectada pelo token de geração.

Administrador técnico e responsável continuam papéis diferentes na API. O
primeiro pode reparar a aplicação de uma política já aprovada; não recebe por
isso capacidade para definir nova política, ler sinal etário ou retirar
supervisão. A primeira implementação usa vínculos de papéis de fixture, sem
inventar o procedimento de cadastro real do responsável.

O serviço não declara uma conta ativa quando algum produtor obrigatório estiver
sem cobertura. Canais alternativos só podem ser habilitados após qualificação;
a sua indisponibilidade deve ser explícita para a conta supervisionada e não
prejudicar a conta comum. Não basta parar uma unidade uma vez: a possibilidade
de nova ativação tem de permanecer inibida durante a transação.

## Base da decisão e limites comprovados

| Evidência | Observação | Exigência para o coordenador |
|---|---|---|
| [Barreira V2](evidence/parental-registry-barrier/README.md) | Busy conserva a barreira; leases são por geração | Persistir negação antes de aguardar; lock de metadados curto, lease por geração |
| [SSH](evidence/parental-ssh-revocation/README.md) | Túnel/multiplex antigo continua após a barreira | Revogar transportes existentes; revalidar autenticação em andamento |
| [Serviços/timers](evidence/parental-producers/README.md) | User= sem PAM passa pela barreira e escapa a logind | Inibir os produtores e confirmar parada fora de user.slice |
| [D-Bus](evidence/parental-dbus-system-activation/README.md) | Nomes ativos e rotas de ativação podem continuar criando trabalho | Inibir rotas antes de encerrar payloads; preservar o barramento compartilhado |
| [Cron](evidence/parental-cron/README.md) | Lease pode ficar no monitor root; logind não revoga o job | Identificar o payload/monitor e sua origem; não sinalizar root por coincidência de lease |
| [Reinício](evidence/parental-registry-boot/README.md) | Journal antigo não remove barreira nova; recovering permanece bloqueado | Reconciliação não reinscreve a conta nem apaga barreira posterior |
| [Saída GDM](evidence/parental-session-exit/README.md) | Worker fecha PAM, mas lingering conserva lease do manager | Logout não prova quiescência; incluir manager e classe manager do logind |

São evidências de VM e fixtures, não um inventário completo de produtores nem
qualificação da ISO. Os testes de boot usam hook exclusivo da VM; os testes
GDM usam worker diagnóstico e sessão mínima. Auditoria do kernel teve perdas.
Não usar ausência de AVC como prova de aplicação ou revogação.

## Identidade e persistência

A referência de uma associação é um identificador opaco local com geração
aleatória. Nome, UID, GID e grupo são atributos de uma conta local conferidos
em cada admissão. NSS remoto e resultados ambíguos não entram neste primeiro
contrato. Divergência da tupla não autoriza escolher o caminho de conta comum.

Cada operação usa revisão esperada e identificador de operação. O registro
armazena schema, revisão, geração, tupla, estado, hash/versão dos adaptadores e
referência da transação. Tokens não derivam de dados civis. Não armazenar senha,
documento, nascimento, biometria, lista de processos ou histórico de navegação.
O inventário de processos necessário à revogação é transitório; o journal guarda
fases, referências técnicas mínimas e códigos de erro, sem comandos dos apps.

Revisão obsoleta gera Conflict sem executar mutação. Repetição da mesma operação
só consulta/retoma o resultado correspondente; não gera outro enrollment. Uma
operação de outra conta pode avançar sem ficar presa à lease da primeira.

O protocolo exige arquivos regulares root-only sem symlinks/hardlinks, limites
de tamanho, criação exclusiva, publicação atômica e fsync do arquivo/diretório.
Leases mantêm inode estável. O leitor não cria arquivos ausentes. O lock de
metadados serializa apenas snapshots e publicações curtas; não acompanha a
vida de uma sessão. Todo adaptador deve conferir geração e barreira compatíveis.
O mecanismo de revisão monotônica e migração de schema ainda precisa ser
implementado: o writer V2 de fixture não constitui implementação deste contrato.

## Estados e operações permitidas

A associação tem `provisioning`, `active`, `transitioning`, `recovering` ou
`tombstone`. A barreira é uma condição durável independente; sua presença nega
admissão mesmo com uma linha `active`. `Blocked` é o estado efetivo exposto pela
API para associação não admitida, não uma tradução para adulto/conta comum.
`Unconfigured` também não representa idade ou capacidade de execução.

| Operação | Pré-condições | Conclusão permitida | Falha após a barreira |
|---|---|---|---|
| Criar | Capacidade de criação, reserva de nome/IDs, registro local consistente | Nova geração ativa após conferir todos os adaptadores | Provisioning/recovering bloqueado; nenhum login parcial |
| Migrar | Associação/revisão exatas e capacidades para a mudança e manutenção Unix | Antiga tombstonada e nova geração ativa após quiescência e validação | Transitioning/recovering bloqueado; não liberar IDs |
| Recuperar aplicação | Capacidade de reparo técnico e política íntegra identificada | Mesmo conteúdo de política aplicado a uma nova geração validada | Recovering bloqueado; não escolher defaults permissivos |
| Reconciliar no boot | Sem pedido de usuário; journal/schema confiáveis | Estado consistente bloqueado, ou confirmação de commit já concluído | Bloqueio preservado; nunca novo enrollment automático |
| Retirar supervisão/excluir | Contrato de autorização e retenção ainda pendente | Indisponível na primeira implementação | Nenhuma conversão para conta comum |

Criação e migração real começam com contas fictícias na VM. Uma GUI não pode
criar a conta primeiro e aplicar o bloqueio depois. Reserva, armazenamento,
modificação Unix e rótulos não são uma transação única do sistema de arquivos:
o journal deve registrar fases e verificar pós-condições para cada adaptador.
Uma falha não autoriza apagar dados/homes como compensação automática.

## Sequência de transição e revogação

1. Resolver identidade do chamador pelo transporte, conferir capacidade sobre
   a associação e autenticar via Polkit. Em seguida, revalidar revisão, vínculo,
   tupla, plano e capacidade antes do primeiro efeito persistente. A GUI nunca
   fornece o UID do chamador como prova. Negação/cancelamento antes desse ponto
   deixa o estado anterior intacto.
2. Persistir a barreira da geração antes de esperar leases ou mudar a conta.
   Só responder que a operação começou após confirmação de durabilidade.
   Contenção ou Busy não remove essa barreira e não libera a geração anterior.
3. Inibir novas admissões e reativações em todas as rotas obrigatórias. O
   inventário inclui sessões/autenticações, managers/lingering, SSH, unidades
   de sistema/usuário, timers, jobs cron e nomes/ativações D-Bus. Um adaptador
   sem inibição demonstrada retorna UnsupportedProducer; não é ignorado.
4. Mostrar o efeito do encerramento e obter a autorização exigida antes de
   revogar atividade existente. A primeira implementação não usa SIGKILL
   silencioso nem encerra serviços compartilhados da conta comum. Operadores
   podem manter a conta bloqueada e adiar a revogação. Se autorizada, usar
   operações upstream e referências de processo verificadas, não PIDs/UIDs
   enviados pela GUI nem sinais a monitores root arbitrários.
5. Confirmar saída dos produtores conhecidos, drenagem de sessões/runtime,
   inexistência de atividade atribuída à conta e aquisição exclusiva da lease.
   Revalidar a inibição depois da drenagem. Sem prova de cobertura, retornar
   UnverifiedQuiescence; ausência pontual de processos/leases é insuficiente.
6. Gravar tombstone antes de remover/liberar a identidade antiga. Aplicar a
   mutação Unix autorizada, adaptadores e rótulos; conferir a identidade via
   NSS e as versões aplicadas. Gerar nova associação, sem reutilizar geração.
7. Preparar a publicação protegida por barreira, validar enforcement negativo
   e conta comum, confirmar commit durável e remover apenas a barreira de
   publicação desta transação. Preservar a negação da geração anterior e
   barreiras de operações posteriores. Só então expor `Active`.

Cada adaptador terá espera limitada definida pelo coordenador e testada na
base. Timeout, desconexão da GUI ou revogação da autorização após a barreira
não reabrem a conta. O serviço persiste o progresso, informa Busy/TimedOut e
permite consultar ou retomar. O timeout não é comprovação de quiescência.

## Recuperação técnica e perda de credenciais

Reparo técnico deve selecionar uma transação/revisão confiável já conhecida,
verificar hashes/schema/tupla e restaurar os adaptadores com a mesma política.
Se houver sessões ou produtores, cumprir a mesma inibição/revogação/quiescência.
Concluir por nova geração explícita, após tombstone da geração anterior. A
reabertura requer autorização e verificações equivalentes às de publicação;
`recover()` executado no boot apenas organiza o estado e mantém a negação.

Não copiar um backup antigo por cima de uma barreira mais recente. Estado
corrompido sem política verificável permite diagnóstico limitado e reparo do
sistema, mas não reabertura automática ou criação de vínculo substituto. Perda
de todas as credenciais do responsável não transfere seu papel para wheel/root
pela API. Reparo que conserve a política pode ser permitido ao administrador;
restabelecer responsável, alterar regras, exportar dados ou retirar supervisão
exige decisões próprias ainda pendentes na ADR/UX. Não implementar atalhos de
"rescue = conta comum" nem prometer proteção contra root com acesso irrestrito.

## API e autorização da primeira implementação

A interface do coordenador pode ser parte do serviço já proposto na ADR 0008;
o transporte/linguagem e empacotamento continuam sujeitos à avaliação de
integração upstream. Não acrescentar um daemon paralelo só para contornar #2.

Consultas próprias, consultas de conta vinculada, plano, execução e progresso
são tipadas/versionadas. O plano contém associação, revisão, operação, efeitos,
adaptadores e necessidade de encerramento; é produzido pelo serviço. Execução
confere novamente os mesmos dados. Não aceitar shell, caminhos arbitrários,
JSON opaco, unidade/PID livre ou capabilities alegadas pelo cliente.

| Capacidade | Papel proposto | Limite |
|---|---|---|
| Consultar próprio estado/pedido | Usuário supervisionado | Sem enumerar outras contas ou sinal etário |
| Definir política/migração vinculada | Responsável autorizado | Não confere por si privilégio para mutar Unix |
| Aplicar mutação Unix autorizada | Administrador técnico | Conferir aprovação da mudança e política vinculada |
| Reparar aplicação existente | Administrador técnico autenticado | Não lê sinal nem muda conteúdo da política |
| Reconciliar persistência no boot | Serviço | Sem nova política, papel, associação ativa ou enrollment |

Uma pessoa pode acumular papéis. Não se exige duas pessoas por padrão; exigem-se
as capacidades corretas e decisões vinculadas à revisão/efeito. O procedimento
real de vincular responsáveis, retenção de pedidos e divulgação de dados não é
resolvido por esta tabela. Diagnóstico global expõe códigos agregados, sem
identidade/sinal/lista de apps. Consultas específicas requerem capacidade antes
de confirmar a existência da associação. Logs de Polkit/journal precisam de
qualificação contra vazamento; não assumir que a intenção de minimizar basta.

## Reutilização upstream e critérios de implementação

A base já oferece lifecycle de sessões/managers, autorização e ferramentas de
contas. A [qualificação upstream](parental-controls-upstream-qualification.md)
e as evidências acima registram o que falta; malcontent isolado não cobre esses
requisitos. Não portar os helpers de evidência literalmente para produção:
eles usam argumentos PAM estáticos, caminhos de fixture, labeling manual e
inventários limitados. Ainda falta definir a classificação persistente que
nega uma conta supervisionada após falha do serviço, remoção de configuração,
handles antigos ou mudanças parciais da identidade. Esse é um gate anterior ao
primeiro teste de criação, não um detalhe a deixar para depois da GUI.

| Etapa | Entrega revisável | Critério para avançar |
|---|---|---|
| 1 | Decisão deste contrato e especificação de adaptadores obrigatórios | Autoridade/fronteira explícitas; classificação e inibição sem lacunas conhecidas |
| 2 | Coordenador mínimo isolado, journal/revisão e recuperação bloqueada | Crash/falhas/concorrência e conta comum preservada; sem liberação automática |
| 3 | Operações reais de contas fictícias e geração | Remover/recriar mesma tupla não herda acesso; colisão/mutação parcial/NSSfalha negados |
| 4 | Reparo técnico autorizado e capacidades | Recuperação mantém política, nova geração; Polkitnega/cancela e revisão obsoleta sem bypass |
| 5 | Integração Vega/upstream e pacote de staging | UX de estado/efeito, instalação, update/downgrade/rollback e dados mínimos qualificados |
| 6 | Candidata de ISO | Checksum exato, boot Enforcing, GNOME/login/logout/desbloqueio e matriz de evasão |

A etapa 1 exige ainda especificar por produtor como a inibição funciona. Onde
não houver mecanismo seguro, manter o recurso indisponível para essa conta ou
adiar a integração completa. Não declarar etapa 1 concluída somente porque
este texto foi aprovado. Testar Busy com atividade persistente, nova ativação
concorrente com drenagem, handles que antecedem instalação, duas contas,
falhas de armazenamento/rotulagem e atualização/downgrade com journal pendente.
Os ensaios já executados podem ser reutilizados quando fontes e escopo forem
compatíveis; não repetir todas as fixtures como substituto dessa integração.

Risco principal: uma falha de aplicação pode bloquear o acesso da conta.
Mitigar com estado consultável, reparo técnico mantendo política, teste
independente da conta comum e restauração de snapshot da VM. Reverter pacote
ou remover Vega não apaga registro/barreira para liberar acesso. Não instalar
na máquina real até qualificar migração e recuperação em staging. Receita,
OBS (somente Leap 16.1) e candidata continuam fora desta entrega documental.

## Aprovação solicitada

Registrar uma decisão explícita sobre a direção acima: coordenador integrado
com transações tipadas, root/admin irrestrito confiável, papéis separados,
reparo técnico sem alterar política e bloqueio quando não houver cobertura de
produtor. Alternativa: revisar a fronteira se for necessário resistir a um
administrador root; os protótipos atuais não atendem essa exigência.

Essa aprovação resolve a direção técnica da próxima etapa isolada. Permanecem
pendentes o desenho final dos adaptadores/classificação, revisões da ADR,
retenção, aferição/sinal, cadastro de responsáveis, retirada de supervisão,
exportação/exclusão e os gates funcionais. Nenhuma dessas decisões é inferida
por uma resposta que aprove este contrato técnico.
