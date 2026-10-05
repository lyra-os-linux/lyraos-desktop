# Contrato proposto do núcleo parental integrado ao vegad

Data: 05/10/2026. Status: **especificação para revisão #2/#5; sem implementação de produto**.
Deriva da [consolidação](parental-admission-integration-review.md) e do
[contrato autorizado](parental-lifecycle-recovery-contract.md).
Não aprova a [ADR 0008](adr/0008-private-age-signal-and-parental-supervision.md)
nem reduz os gates #6/#102. A aprovação final da arquitetura e a solução de
rollback continuam pendentes. O escopo executável seguinte é laboratório isolado.

## Localização e lifecycle

Recomendação concreta: um módulo de coordenação no vegad existente, servido
no barramento de sistema. Manter ativação sob demanda; não criar outro daemon,
não tornar Vega root e não usar a GUI como autoridade de estado. O módulo
possui armazenamento, classificação, autorização de operações e adaptadores;
PAM e outros pontos de admissão leem um formato negativo mínimo sem depender
de chamada ao Vega. O contrato D-Bus de produto pertence ao repositório
`lyra-vega-dbus`; este documento não adiciona uma interface ao contrato publicado.
Namespace da API parental segue provisório conforme a ADR. Não reservar nome
ou ativar um segundo serviço com o namespace provisório sem decisão #2/#5.

Inspeção do vegad HEAD `1c671bac5ce6a813d0732bbcb847dce314ae9417`:

| Fonte existente | Reutilização | Limite |
|---|---|---|
| `internal/dbusserver/server.go`: Activity.begin/stopIfIdle/trackedMethods | Segurar a chamada enquanto há trabalho; IdleTimeout atual de dois minutos só se aplica sem chamadas ativas | Trabalho em goroutine após resposta não fica protegido automaticamente |
| `internal/dbusserver/polkit.go`: checkPolkit | Identificar sujeito por nome único D-Bus via pkcheck; consulta sem interação disponível | A ação administrativa atual não demonstra papel de responsável nem autorização vinculada ao plano |
| `internal/dbusserver/desktopuser.go`: resolveDesktopUser | Consultar UID do remetente no bus | Não reutilizar fallback desktopUserOrNil; nil para UID0 e falha NSS não são autorização parental |
| `internal/dbusserver/users.go`: CreateUser/UpdateUser/RemoveUser/SetAdmin | Ponto obrigatório de integração das mutações administrativas | Sem guard parental hoje; userdel -r não pode ser compensação automática de transação parental |

Primeiro protocolo de laboratório: execução síncrona com tempo limitado, dentro
do wrapper de atividade existente. Se Busy/TimedOut, publicar resultado durável
negativo e devolver controle; retomar requer chamada explícita e autorização
nova. Não deixar uma tarefa mutante desanexada após devolver resposta. Crash,
SIGTERM, cliente perdido e interrupção pelo gerenciador de serviços podem
ocorrer mesmo com Activity: durabilidade, não o contador, protege o estado.
A resposta de sucesso só sai após fsync das publicações exigidas pelo protocolo.

## Classificação persistente e admissão

Classificação é uma decisão técnica de acesso, não um sinal etário. Campos
mínimos propostos: schema, revisão esperada, identificador local opaco,
geração aleatória, tupla local conferida (nome/UID/GID/grupo), classe
`ordinary` ou `supervised`, estado, referência de operação e digest da revisão
aplicada dos adaptadores. Nenhum dado civil ou nascimento. O nome do arquivo,
a escolha de UID ou um campo enviado pelo cliente não constitui identidade.

O catálogo deve cobrir contas locais admitidas no modo gerenciado. Uma conta
comum precisa de registro positivo explicitamente provisionado: ausência não
significa comum. Antes de habilitar leitura fail-closed, bootstrap deve incluir
as contas comuns e canais de manutenção suportados, em VM, e confirmar sua
preservação. Não aplicar este desenho ao host por simples instalação de RPM.
Migração do inventário existente não cria papéis ou supervisão automaticamente.

| Estado observado pelo leitor | Resultado de admissão no modo gerenciado |
|---|---|
| Registro ordinary íntegro, identidade exata, revisão compatível e nenhuma barreira/tombstone conflitante | Somente admissão ordinária; não afirma idade nem proteção parental |
| Supervised active, mesma geração/política em todos os adaptadores obrigatórios, sem barreira | Elegível para admissão supervisionada; ainda exige os controles próprios de cada canal |
| Barreiras, transitioning, provisioning, recovering ou tombstone | Negar; independentemente de prova positiva antiga |
| Registro ausente/corrompido, revisão/schema incompatível, identidade/NSS ambígua ou adaptador obrigatório desconhecido | Negar com diagnóstico técnico limitado; nunca converter para ordinary |
| Catálogo global inválido ou armazenamento indisponível | Não inferir nenhuma classe; recuperação técnica necessária |

O leitor valida arquivos limitados, root-owned, regulares, sem symlink/hardlink,
permissões restritas e parsing sem campos/duplicatas desconhecidos. Leases têm
inodes estáveis; publicação de registros usa temporário exclusivo, fsync de
arquivo, rename e fsync de diretório. Locks curtos protegem snapshots e commit;
não devem atravessar diálogo de autorização ou vida da sessão. Ordem proposta:
inventário/classificação, ledger de operação e locks do adaptador, sempre igual.
Especificar a correspondência dessa ordem com os módulos finais antes de portar
as fixtures, que não são uma implementação dessa classificação.

A negação por perda do catálogo pode atingir a conta comum: esse risco não foi
resolvido pelos testes de preservação com arquivos íntegros. O contrato de
recuperação deve manter a política e conferir estado confiável, sem abrir toda
a máquina porque um arquivo sumiu. Uma exceção de manutenção não pode fornecer
um caminho de evasão à conta supervisionada. Enquanto esse comportamento não
for qualificado, a classificação permanece experimental e desabilitada.

## Revisão e rollback: gate ainda aberto

CAS de revisão e geração aleatória impedem conflitos/reutilização no estado
atual; não detectam restauração conjunta do filesystem a uma revisão antiga.
Nenhum digest, tombstone ou contador no mesmo snapshot resolve isso sozinho.
Não chamar a revisão local de autoridade monotônica global.

Recomendação para revisão: manter root irrestrito confiável, mas tratar rollback
administrativo suportado como operação coordenada, que conserva o estado
negativo e recusa restaurar permissão obsoleta. Antes de implementação de
produto, registrar quais caminhos de Snapper/boot/rescue/update/downgrade
participam, onde fica a referência durável independente do estado restaurado
e como sua indisponibilidade mantém bloqueio. A localização dessa referência
não foi escolhida ou qualificada. Excluir um diretório de um snapshot isolado
não demonstra cobertura de todos os caminhos. Não introduzir TPM, serviço cloud
ou novo mecanismo como dependência implícita para preencher essa lacuna.

Aceite: demonstrar estado posterior bloqueado versus backup anterior permissivo,
rollback interrompido, referência ausente/incompatível e manutenção da conta
comum conforme o contrato de recuperação. Se não houver solução para o escopo
prometido, registrar adiamento/alteração de requisito explicitamente na ADR;
não silenciosamente aceitar snapshot antigo.

## API mínima para a etapa isolada

Nomes abaixo são propostas sem compromisso de ABI. Tipos fechados/versionados;
sem shell, paths, PID/unidade arbitrária, JSON opaco ou UID de chamador alegado.
Identificadores de plano/operação não são credenciais. O serviço resolve
associação e efeitos antes de autorizar. Consultas não levantam diálogo.

| Operação | Entrada aceita | Resultado e autorização |
|---|---|---|
| GetOwnState | Nenhum alvo | Estado próprio mínimo; remetente resolvido pelo transporte |
| GetHealth | Nenhum alvo | Versão/schema e códigos agregados, sem enumeração ou dados de contas |
| PlanWithdrawal | Associação opaca e revisão esperada | Plano tipado com ID, geração, revisão, efeito de negar novas admissões e cobertura; capacidade técnica sobre o alvo antes de confirmar existência |
| ExecuteWithdrawal | ID do plano emitido pelo serviço | Autorização nova e revalidação; resultado AdmissionWithdrawnNoQuiescence ou erro tipado |
| GetOperation | ID da operação | Progresso específico somente para capacidade autorizada; não altera arquivos |
| ResumeWithdrawal | ID da operação existente | Mesmos bindings, autorização nova, sem reconstruir temporários ou reenrollment |

Retirada aqui significa **retirada de admissão**. Retirar supervisão, apagar
conta, publicar nova geração ativa e alterar política não fazem parte desse
primeiro conjunto e retornam UnsupportedOperation. Essa separação não remove
criação/migração dos marcos finais da primeira entrega; limita o componente de
laboratório para não misturar operação qualificada com funcionalidades ausentes.

Erros mínimos: Denied, AuthorizationFailure, Conflict, Busy, TimedOut,
RecoveryRequired, StorageFailure, UnsupportedProducer, UnsupportedOperation e
UnverifiedQuiescence. Sem devolver stdout de pkcheck, dumps de registros,
faixa, caminhos pessoais ou detalhes de outra conta como erro público. Logs
registram apenas código e correlação técnica mínima, com acesso restrito.

## Autorização e concorrência

1. Resolver remetente único vivo pelo transporte. UID0 não herda papel de
   responsável pela API. Para alvo específico, verificar capacidade antes de
   responder se ele existe; alvo inexistente e inacessível não são enumeráveis.
2. Produzir plano no servidor sob snapshot curto: associação/geração/revisão,
   identidade, inventário e efeitos completos. O cliente só devolve seu ID.
   Plano tem validade limitada; prazo concreto deve ser definido no laboratório,
   não uma janela de cache de autorização global.
3. Liberar locks e solicitar ação Polkit específica de reparo/retirada de
   admissão; não reutilizar users.manage como papel parental. Sem auth_admin_keep
   como atalho para novas operações. Sucesso Polkit é condição necessária,
   não prova do vínculo de responsável nem permissão para trocar política.
4. Após o diálogo, conferir remetente/capacidade novamente e revalidar todo
   binding sob os locks na ordem fixa. Cancelamento/negação/revisão obsoleta
   antes do primeiro efeito não escrevem barreira. Não transportar credenciais
   ou decisão positiva para outro cliente, operação, revisão ou reboot.
5. Persistir intent negativo como primeiro efeito; confirmar durabilidade antes
   de responder que começou. Falha subsequente mantém bloqueio. Perda do cliente
   após esse ponto não desfaz intent; serviço conclui até ponto seguro limitado.
6. Retomada confere registro canônico e bindings, pede autorização nova fora dos
   locks e revalida. Retry concluído não regrava estado. Sem primeiro marcador
   confiável retorna RecoveryRequired antes de pedir autorização, como na prova.

Uma operação ativa por associação; conflito não substitui ownership. Outras
contas podem progredir sem esperar leases desta. StopUnit exige referências
qualificadas do mesmo boot e sua própria autorização/observação; não é efeito
implícito de ExecuteWithdrawal. Nunca declarar quiescência só por proof retirada,
timeout, ausência momentânea de PID ou sucesso do pedido StopUnit.

## Guard de operações administrativas e boot

CreateUser deve reservar/classificar antes do primeiro login possível. Enquanto
isso não existir, recusar criação que colida com associação/tombstone ou use
caminho parental não suportado. No modo gerenciado, se não puder publicar a
classificação ordinary de forma protegida, recusar também criação comum; não
criar primeiro e deixar a conta sem classificação. UpdateUser/SetAdmin/RemoveUser devem verificar
classe e recusar a mutação protegida fora de transação autorizada; a revisão é
revalidada no efeito, não apenas quando a tela foi aberta. Não apagar home ou
política como compensação. Cobrir chamadas Vega/CLI/Web ao mesmo contrato.
Classificação desconhecida não permite mutação permissiva. Catálogo íntegro
ordinary continua usando o fluxo administrativo suportado.

No boot, inspecionar schema/journal e preservar bloqueio. Não criar registro
ordinary para preencher ausência, promover temporário, retomar efeitos Unix,
reemitir StopUnit de boot antigo, definir responsável ou publicar active.
Migração de schema conserva última revisão válida e estado negativo; downgrade
incompatível recusa alteração. RPM não apaga catálogo/barreiras no uninstall.

## Aceite do próximo componente

O próximo passo executável é um módulo isolado com parser/classificador,
planejamento/retomada tipados e adaptador de autorização real no laboratório.
Antes do produto, revisar esta especificação com as decisões #2/#5 pendentes.
O componente deve demonstrar:

- matriz de classificação acima, inclusive catálogo ausente e divergência NSS;
- negação/cancelamento Polkit, remetente perdido e revisão trocada durante diálogo;
- duas contas/concorrência, replay de plano alheio e preservação ordinary;
- chamada longa protegida por Activity e retomada após nova instância;
- interrupções/erros de armazenamento derivados das publicações implementadas;
- guard dos métodos administrativos sem liberação/remoção acidental de dados.

Reutilizar evidências compatíveis; não repetir toda a suite de cortes por mudança
documental. Laboratório usa contas fictícias e disco descartável verificado;
reversão é descarte/restauração do overlay, sem instalação na estação.
Produto continua dependente de cobertura de produtores, enforcement #102,
GNOME completo, UX/privacidade, revisão confiável e RPM/ISO qualificados.

## Primeiro componente isolado — 05/10/2026

O [classificador e planejador experimental](evidence/parental-service-classifier/README.md)
implementa parsing/leitura read-only, elegibilidade e planos vinculados ao
remetente/revisão. Não implementa publicação, Polkit, execução da retirada
ou guard de produto. As decisões abertas deste contrato permanecem abertas.

## Ligação à retirada negativa — 05/10/2026

A [ligação experimental](evidence/parental-service-withdrawal/README.md)
conecta planos aos modelos existentes, vincula catálogo/geração ao journal e
revalida antes do intent. Autorização é callback confiável; ledger/inventário
são simulados nos testes novos. Não qualifica armazenamento integrado ou
transporte/Polkit de produto e mantém os gates acima.

## Armazenamento real no laboratório — 05/10/2026

A [composição com arquivos de root e locks reais](evidence/parental-service-storage/README.md)
passou em 11 testes de VM, incluindo nova instância após saída do processo no
intent durável. Não qualifica Polkit/D-Bus, PAM real, rollback ou enforcement;
a estação permanece sem instalação.

## D-Bus/Polkit reais no laboratório — 05/10/2026

O [ensaio de transporte e decisão Polkit](evidence/parental-service-auth/README.md)
passou em oito cenários e retomada por novo servidor: remetente real, negação,
agente cancelando e revisão/capacidade revalidadas. Permissão usa regra restrita
da fixture; vínculo de responsável e autenticação positiva por senha não foram
qualificados. Não implementa API ou ações de produto nem altera os gates.
