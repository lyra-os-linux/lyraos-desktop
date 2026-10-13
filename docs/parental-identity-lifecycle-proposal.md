# Ciclo de vida da conta supervisionada — proposta para ADR #5

**Status:** proposta de arquitetura; não implementada nem aprovada.
**Escopo:** desenhar criação, migração, recuperação e remoção de uma conta
supervisionada. Não define aferição etária, obrigações legais ou UX final.
**Dependências:** ADR #5, parecer registrado em #10, base/enforcement #6/#102 e
autorizações/UX #7/#8.

O objetivo é fechar a lacuna identificada nos ensaios de identidade e
transições: os protótipos admitem uma conta com vínculo já estabelecido, mas
ainda não coordenam com segurança a criação, mudança de identidade, sessões
ativas e retirada da supervisão. Este texto propõe um contrato para revisão;
não autoriza ativar a política no host ou na ISO.

## Princípios do contrato

- A fonte persistente da associação é um registro root-only, versionado e
  transacional. Nome/UID/GID/grupo são atributos conferidos, não a identidade
  estável isoladamente. Não reutilizar uma associação antiga porque os números
  Unix coincidem.
- Cada associação recebe um identificador aleatório local, não derivado de
  nome, UID, faixa etária ou dados civis. O identificador serve à consistência
  interna e não é exposto aos aplicativos.
- NSS remoto, resultado ambíguo e identidade parcial não podem selecionar o
  caminho de conta comum. Até que NSS remoto tenha contrato explícito, contas
  desse tipo ficam fora do escopo de supervisão.
- Mutações começam em estado de bloqueio persistente e só publicam `active`
  depois de instalar e conferir todos os adaptadores obrigatórios. Erro,
  encerramento do processo ou reinicialização deixam `blocked`/`recovering`,
  nunca um perfil comum por ausência de dados.
- Nenhuma transição apaga o último registro válido antes de gravar e verificar
  o próximo. Tombstones impedem reutilização silenciosa de identificadores.
- Mudança de configuração não revoga processos ou conexões já existentes por
  si só. Uma operação que dependa de cessar atividade deve provar que todos os
  produtores da conta foram parados e que novas admissões permanecem fechadas.
- O estado parental não contém documento, biometria, nascimento exato ou
  histórico de navegação/processos. Métodos de aferição e campos de sinal ficam
  bloqueados até decisões da ADR e revisão profissional.

## Registro e estados propostos

O registro root-only contém versão do schema, revisão monotônica, geração
aleatória da associação, estado, identidade Unix vinculada, versão/hash das
configurações de enforcement exigidas e identificador da transação incompleta,
quando houver. Não armazena uma cópia da senha nem detalhes de atividade.

```text
unconfigured
    │ criação autorizada
    v
provisioning ── verificação completa ──> active
    │ erro/crash                              │ migração ou remoção autorizada
    v                                         v
blocked <────────────────────────────── transitioning
    │                                        │ sessões/processos cessados,
    │ recuperação autorizada                │ adaptadores verificados
    v                                        v
recovering ── validação completa ────────> active
    │ erro ou evidência insuficiente
    v
blocked
```

`unconfigured` significa que a conta ainda não tem vínculo, não que seja
adulta. `provisioning`, `transitioning`, `recovering`, identidade desconhecida,
estado inválido e enforcement degradado são estados não ativos. O Vega só pode
exibir “supervisão ativa” quando o serviço confirmar a mesma revisão aplicada
por todos os adaptadores obrigatórios.

## Operações

### Criar uma conta supervisionada

1. Autorizar uma operação tipada para um responsável vinculado; associação a
   `wheel` sozinha não define esse papel. Polkit valida a capacidade no serviço,
   não na GUI.
2. Reservar nome e identificadores, gravar transação `provisioning` e impedir
   login concorrente antes de criar arquivos ou configurar PAM.
3. Criar a conta com identidade única e estado inicialmente bloqueado. Instalar
   as vinculações de identidade, mapeamento MAC e entradas necessárias sem
   substituir arquivos do fornecedor globalmente.
4. Verificar ownership/modes, schema e contexto SELinux, comportamento negativo
   e conta comum; conferir que todos os caminhos configurados apontam para o
   identificador da mesma geração.
5. Publicar `active` por substituição atômica e fsync; só então liberar novas
   admissões. Repetir a consulta de estado depois da publicação.

Falha em qualquer passo preserva `blocked` e registra somente código técnico
não pessoal. A recuperação retoma ou desfaz a transação com base em seu journal;
nunca decide que a conta é comum porque criação ou integração ficou incompleta.

### Migrar identidade

1. Autorizar a migração e gravar `transitioning` para a geração atual, fechando
   novas admissões em todas as entradas já qualificadas.
2. Adquirir a trava exclusiva de transição. Se houver sessões, handles PAM,
   processos ou conexões não revogáveis, manter bloqueado e retornar `Busy`;
   não matar processos silenciosamente.
3. Confirmar todos os UIDs reais/efetivos/salvos/de filesystem, gerenciadores,
   D-Bus, lingering, cron e serviços com `User=`. Uma varredura `/proc` isolada
   não prova que um produtor externo não possa criar outro processo.
4. Gravar os valores antigos e novos no journal root-only, adicionar tombstone
   aos identificadores liberados e atualizar atomicamente as vinculações PAM,
   NSS permitido, AccountsService e MAC.
5. Validar a identidade nova e as negações/positivos exigidos. Publicar a nova
   geração `active` apenas quando todos os adaptadores confirmarem a revisão;
   manter a geração antiga e o journal até a verificação pós-transação.

Não permitir alteração parcial de nome/UID/GID/grupo que faça um vínculo cair
no caminho comum. Qualquer divergência entre cadastros bloqueia a admissão e
requer recuperação explícita.

### Recuperar

Recuperação exige autorização elevada e seleciona uma revisão conhecida pelo
serviço. O operador vê a identidade técnica afetada, o código da falha e o efeito
da ação antes de confirmar. Recuperar não remove a política nem converte a conta
para comum. Se não for possível reconstruir enforcement de modo verificável,
manter novas admissões bloqueadas e oferecer uma ação separada para salvar os
dados da conta, sem iniciar sua sessão.

O procedimento para recuperar sem acesso gráfico, inclusive a divisão entre
responsável e administrador técnico, permanece decisão da ADR/UX. Não presumir
que a recuperação de root físico ou mídia de rescue seja resistência a um
administrador comprometido.

### Remover supervisão ou excluir a conta

Essas são operações diferentes e não devem compartilhar um botão ou contrato.
Retirar supervisão muda a fronteira de segurança e depende de autorização,
consentimento, contestação e condições que ainda precisam ser resolvidas na
ADR #5/#8 à luz do parecer. Até essa decisão, não oferecer a transição para
conta comum.

Excluir uma conta também requer política de retenção e tratamento de dados,
pendências, sessão e recuperação definidos. A exclusão não apaga tombstones ou
journals necessários para impedir reutilização de identidade; retenção e prazo
desses metadados são decisões pendentes. Se não houver contrato aprovado, não
implementar nenhuma das duas operações.

## Persistência e concorrência

- Diretório e arquivos de root, sem escrita por outros; abrir com
  `O_NOFOLLOW|O_CLOEXEC`, validar tipo, proprietário, modo e número de links.
- Serializar mutações com lock exclusivo e leitores por snapshot coerente.
- Escrever arquivo temporário com criação exclusiva, validar conteúdo, fazer
  `fsync` do arquivo, `rename` atômico e `fsync` do diretório.
- Revisão monotônica, journal explícito por fase e última revisão válida
  preservada; pacote removido ou downgrade incompatível nunca limpa o estado.
- Integrar as travas mantidas por sessões com todos os pontos de admissão. A
  trava PAM atual é uma prova da ideia, não cobre automaticamente GDM,
  systemd-user, SSH, cron, D-Bus, lingering ou serviços `User=`.

## Autorização e interface

API local tipada e versionada: `Create`, `Migrate`, `Recover`, `RequestRemoval`,
`GetOwnState` e `GetManagedState`. Sem comando shell, caminho arbitrário, UID
isolado ou JSON opaco fornecido pela GUI. A identidade do chamador e sua
capacidade são verificadas no serviço a cada mutação. Erro de autenticação,
Polkit, serviço, armazenamento ou adaptador não altera o estado ativo.

`RequestRemoval` não executa uma mudança: registra pedido somente depois de a
ADR definir quem pode solicitar, aprovar e contestar. A UI apresenta revisão e
saúde real dos adaptadores e distingue conta bloqueada, incompleta e ativa.
Desinstalar Vega não altera enforcement.

## Matriz de qualificação necessária

| Risco/caso | Resultado exigido |
|---|---|
| Crash/reboot entre cada gravação da transação | Estado recuperável e bloqueado; nunca associação parcial ativa |
| Conta removida e UID/GID reutilizados | Nova geração não herda política nem acesso anteriores |
| Nome, UID, GID ou grupo parcialmente alterado | Admissão recusada até recuperação |
| Identidade inteiramente trocada ou NSS indisponível | Nunca cair silenciosamente no perfil comum |
| Sessão, handle PAM ou autenticação em andamento | Migração retorna ocupado ou conclui revogação comprovada; sem login posterior |
| Túnel SSH/D-Bus/processo fora do logind já existente | Transição detecta/revoga segundo política explícita; não declara sucesso com atividade aberta |
| Serviço persistente tenta iniciar trabalho após varredura | Bloqueado pela fronteira integrada, não apenas por snapshot de `/proc` |
| Erro simultâneo ao publicar e restaurar estado | Bloqueado e recuperação explícita; nunca `active` ambíguo |
| Conta comum, com ou sem módulo parental disponível | Mantém login e uso normal |
| Sem Vega ou após update/downgrade | Política consistente e estado verificável; incompatibilidade mantém bloqueio |

Cada resultado deve ligar versão/hash da política e dos RPMs, estado SELinux,
conversa PAM/processo real, códigos de saída e restauração do snapshot da VM.
Mock de GUI, uma sessão PAM aberta por root ou ausência de processo num único
instante não satisfazem os critérios.

## Recomendação para deliberação da ADR

O ensaio descartável de 29/09/2026 confirmou que uma associação PAM composta
somente por nome, UID, GID e grupo admite uma nova conta criada com a mesma
tupla. O achado reproduzido, incluindo a limpeza, está em
[`reuse-result.json`](../../worktrees/desktop-parental-identity/docs/evidence/parental-identity/reuse-result.json)
e no [relatório do ensaio](../../worktrees/desktop-parental-identity/docs/evidence/parental-identity/README.md).
`passed: true` nesse diagnóstico significa que a reprodução e a limpeza foram
bem-sucedidas; não significa que o controle de segurança passou.

Para a ADR, recomenda-se aprovar estes requisitos técnicos antes de escolher
um backend ou começar a implementação:

1. Uma associação ativa recebe um identificador aleatório local e uma revisão
   monotônica. Nenhum nome ou ID Unix serve como identidade estável, e o token
   não contém nem deriva de dados civis.
2. O registro root-only é a fonte autoritativa da geração ativa. Um adaptador
   de admissão só aceita a conta quando consegue verificar a mesma geração,
   revisão e estado `active`; registro ausente, inconsistente ou inacessível
   falha fechado. A prova experimental PAM conseguiu comparar tupla/geração
   com um registro root-only; ela está em
   [registry-result.json](../../worktrees/desktop-parental-identity/docs/evidence/parental-identity/registry-result.json).
   Isso não qualifica as entradas reais nem o serviço que mantém o registro.
3. Ao remover ou substituir uma associação, a transação persiste o tombstone
   antes de liberar a geração. Recriar a mesma tupla não reativa a geração
   anterior; a nova conta permanece bloqueada até uma operação explícita e
   autorizada criar uma associação nova.
4. Uma mutação é serializada por lock, journalizada e publicada por gravação
   atômica com `fsync`. Crash, falha de adaptador ou conflito concorrente deixa
   a revisão em `blocked`/`recovering`. O último estado verificado e os
   tombstones não são apagados por downgrade ou remoção do pacote.
5. Criação, migração e recuperação são operações tipadas de um serviço
   privilegiado; a GUI não escreve o registro nem passa comandos ou caminhos
   arbitrários. Conta comum não é convertida em supervisionada por coincidência
   de IDs, e estado desconhecido não é interpretado como adulto.

O aceite específico para fechar o achado é: provisionar identidade A, removê-la
pela transação aprovada, recriar a mesma tupla como identidade B e demonstrar
que B não alcança sessão PAM nem contexto supervisionado até novo enrollment;
testar também crash em cada fase, corrupção/ausência do registro, duas mutações
concorrentes e conta comum preservada. A reprodução atual permanece como teste
de caracterização e deve ser substituída por essa expectativa negativa quando o
contrato for implementado.

Esses requisitos não resolvem quem pode solicitar/aprovar enrollment,
recuperação ou remoção, nem quando se pode retirar supervisão. Essas são
decisões de produto e da revisão profissional; precisam de resposta na ADR
antes de habilitar qualquer fluxo. O mecanismo que observa remoção de conta,
trava as entradas e integra NSS/SELinux também continua sujeito à prova de
viabilidade no Leap 16.1. O token de geração sozinho não detecta que um
administrador externo recriou manualmente a mesma tupla.

### Viabilidade no protótipo PAM

O protótipo atual (`pam-guard.c` e `bindings.py`) recebe nome, UID, GID e grupo
por argumentos da configuração PAM root-owned e compara esses valores com NSS
em cada abertura de sessão. A estrutura POSIX consultada pelo módulo não expõe
um identificador de geração da conta. Portanto, acrescentar um UUID aos mesmos
argumentos não resolveria a reprodução: a nova conta ainda teria os atributos
que fazem o argumento antigo coincidir.

A prova de viabilidade, feita na VM descartável em 29/09, demonstrou que o
módulo PAM experimental pode consultar o registro root-only em cada admissão:
uma geração ativa é aceita, tombstone/estado bloqueado e configuração obsoleta
são negados, ausência/corrupção/permissão inadequada falham fechado e a conta
comum segue funcionando. Os 12 cenários e hashes estão em
[registry-result.json](../../worktrees/desktop-parental-identity/docs/evidence/parental-identity/registry-result.json);
o código está em
[pam-registry-guard.c](../../worktrees/desktop-parental-identity/docs/evidence/parental-identity/pam-registry-guard.c).
Isto prova a checagem estática do adaptador, não a cobertura de login real ou a
corrida com sessões PAM em andamento.

Um helper de transação separado foi ensaiado na mesma VM: 16 cenários cobriram
interrupções de processo antes/depois de publicações atômicas, recuperação e
duas tentativas concorrentes. O resultado está em
[registry-transaction-result.json](../../worktrees/desktop-parental-identity/docs/evidence/parental-identity/registry-transaction-result.json)
e o fonte em
[registry-transaction.py](../../worktrees/desktop-parental-identity/docs/evidence/parental-identity/registry-transaction.py).
Isso caracteriza o protocolo de gravação, mas não é um corte de energia, não
prova o comportamento do armazenamento físico.

Uma terceira prova conectou o lock compartilhado do handle PAM ao lock
exclusivo do escritor: uma sessão aberta fez a transição retornar `Busy`; após
`pam_sm_close_session`, a transição publicou `transitioning` e novas admissões
foram negadas. Os nove checks estão em
[registry-pam-lock-result.json](../../worktrees/desktop-parental-identity/docs/evidence/parental-identity/registry-pam-lock-result.json).
Isso ainda é um handle sintético, não qualifica a duração das sessões GDM,
TTY, SSH ou serviços, nem demonstra que todos os processos/conexões do UID
terminaram quando o handle PAM fecha.

Em 01/10, a integração com `systemd-user` real passou 30 checks nativos:
sd-pam retém o lease por geração, inclusive em lingering sem login interativo
ou remoto e após reexec. Tombstone e argumentos com geração antiga recebem
224/PAM; a geração nova só inicia após enrollment e troca explícita do
argumento PAM. Contenção do escritor também recusa a admissão sem esperar
liberação do lock. Evidência e fontes estão no
[relatório nativo](../../worktrees/desktop-parental-registry-lifetime/docs/evidence/parental-identity/README.md)
e no [resultado](../../worktrees/desktop-parental-registry-lifetime/docs/evidence/parental-identity/native-registry-manager-result.json).
Isso não exercita logout/boot com lingering, GDM por geração ou revogação de
conexões já autenticadas. A fixture precisa esperar logind/runtime do usuário
terminarem antes de reiniciar o serviço; deadline e recuperação dessa
quiescência ainda precisam de contrato de produto.

O ensaio seguinte conectou o mesmo guard/escritor ao GDM com senha: 22 checks
nativos e 270 testes Python passaram. Worker e sd-pam conservam leases; uma
conversa já no prompt recebe a senha correta depois de `transitioning` e sua
abertura é recusada. Tombstone/geração antiga e falhas de registro/módulo
também recusam, preservando conta comum e restauração. Veja a
[evidência GDM](../../worktrees/desktop-parental-registry-lifetime/docs/evidence/parental-registry-gdm/README.md).
Worker diagnóstico, sessão ELF mínima e labeling de fixture continuam sendo
limites; não há produto GNOME completo, enrollment sem guard ou revogação
de conexões anteriores qualificados. Logs registraram perdas de audit e não
representam um inventário completo de AVCs.

Há duas divergências importantes entre helper e proposta: o lock do registro
é global, de modo que uma conta supervisionada pode impedir uma transição de
outra; e `begin` retorna `Busy` deixando o registro ativo, em vez de persistir
o bloqueio antes de aguardar leases. A fixture anterior das PRs137–140 já
ensaiou uma barreira persistente. Reconciliar geração, barreira de admissão e
isolamento por conta é requisito antes de adotar o helper num serviço; o teste
nativo não autoriza alterar o contrato proposto para facilitar a implementação.

A transação autorizada ainda precisa gravar o tombstone antes de remover/liberar
a identidade; a mesma tupla fica negada até enrollment explícito com nova
geração. O serviço de ciclo de vida, recuperação automática no boot, operações
reais de conta e integração com sessões/adaptadores reais ainda precisam ser
implementados e testados. Esses helpers de VM não são uma implementação
escolhida para o produto.

Há um limite de autoridade que a ADR precisa declarar: uma ferramenta executada
por root fora do serviço pode apagar uma conta sem gravar tombstone. O módulo
não consegue inferir depois, apenas pelo NSS, que uma conta idêntica foi
recriada. Assim, o contrato deve integrar todos os fluxos suportados de criação
e remoção ao serviço e tratar root/admin técnico como autoridade confiável; se
isso não for aceitável, será necessário outro mecanismo de detecção antes de
prometer proteção contra essa ação administrativa. O achado original foi
produzido como root e caracteriza justamente essa fronteira, não uma ação
disponível ao usuário supervisionado.

## Decisões em aberto para revisão da ADR

1. Quem pode iniciar migração e recuperação: responsável, administrador
   técnico, ambos ou política de dupla aprovação?
2. Qual ação é permitida se todas as credenciais de responsável forem perdidas?
3. Quais eventos autorizam retirar supervisão e como atender autonomia,
   contestação e recuperação?
4. Qual retenção mínima de tombstones, journals e pedidos é necessária?
5. Qual conjunto oficial de serviços/entradas deve ser bloqueado na primeira
   versão, e a proteção pode ser entregue se faltar algum canal?
6. Qual mecanismo MAC da candidata oferece política suportável e qual equipe
   mantém seus tipos, rótulos e migrações durante update/rollback?

Até responder essas questões e fechar #6/#102, esta proposta não desbloqueia
serviço #2, UI #7/#8, inclusão na receita ou publicação. O ciclo deve ser
implementado e qualificado em VM descartável antes de alterar qualquer conta
real.


## Atualização experimental — barreira v2 em 01/10/2026

Na worktree `worktrees/desktop-parental-registry-lifetime`,
`docs/evidence/parental-registry-barrier/` agora qualifica a barreira persistente
antes da quiescência e leases/journals por geração. Busy bloqueia novas
admissões, enquanto outra conta pode entrar e concluir sua transição.
Writer52, manager nativo30, PAM de duas contas18 e GDMsenha22 passaram;
suítePython270. Fontes/evidências anteriores preservados. VM restaurada e OFF.

Isso substitui o gap de Busy deixando active/lockglobal de longa duração do
protótipo v1, não o contrato de produto. Revogação de conexões antigas,
produtores persistentes, logout/boot/desbloqueio e ciclo real de contas ainda
não estão completos. ADR/autoridade/recuperação, UI/Polkit/privacidade e
update/rollback continuam pendentes. #6/#102 seguem abertas; não há publicação
nem alteração de receita. Audit perdeu eventos: não é inventário completo AVC.
Retomada em `analysis/2026-10-01/parental-registry-barrier/CURRENT.md`.


## Atualização experimental — revogação SSH em 01/10/2026

24 controles nativos em `worktrees/desktop-parental-registry-lifetime/docs/evidence/parental-ssh-revocation/`
qualificam barreira v2 na fase account e revogação dos transportes anteriores
pelo logind, com saída de monitores root confirmada por pidfds, preservando
conexões comuns e listener. Autenticação pendente com senha correta posterior
é negada. Túnel sem shell tem sessão PAM/logind na versão executada;
ControlMaster antigo continua abrindo canal antes de revogar o transporte.

O adapter só admite a baseline para ensaiar revogação; não muda a política de
produto de recusar CLI/SSH da conta supervisionada nem qualifica MAC/apps.
VM restaurada/OFF; suíte270 e integridade das evidências passaram. Próximo:
cron/timers/D-Bus/serviçosUser= e demais produtores persistentes; ainda não há
quiescência de toda a conta ou autorização para operações reais de identidade.
ADR/autoridade/recuperação, backend/UI/Polkit/privacidade e update/rollback
seguem pendentes. #6/#102 abertas, sem host/receita/OBS/ISO alterados.
Retomada: `analysis/2026-10-01/parental-ssh-revocation/CURRENT.md`.

### Evidência adicional — produtores systemd, 01/10/2026

14 verificações nativas PASS e 270 testes PASS; três controles reproduzem lacunas: serviço/timer User= sem PAM executa após barreira e logind não revoga esses produtores em system.slice. PAMName experimental nega novas admissões e vincula gerações. Encerramento explícito apenas das unidades fixture não é revogação geral. Cron e D-Bus não qualificados; proteção completa NO-GO. Evidência: worktrees/desktop-parental-registry-lifetime/docs/evidence/parental-producers/; retomada: analysis/2026-10-01/parental-producers/CURRENT.md. VM restaurada e desligada; sem alteração no host/receita/OBS/ISO.

### Evidência adicional — D-Bus system bus, 01/10/2026

17 verificações nativas PASS, incluindo quatro reproduções de lacunas, e 270 testes PASS. SystemdService sem PAM e Exec+User via broker36 admitem após barreira e sobrevivem a logind; nomes já ativos atendem chamadas. PAMName experimental nega novas admissões; desarme apenas das rotas fixture antes de parar unidades comprovou saída de quatro payloads e preservou conta comum/barramento. Isso não resolve inventário/inibição geral, corridas pendentes, autorização de clientes nem MAC parental. Proteção completa NO-GO; cron pendente. Evidência em worktrees/desktop-parental-registry-lifetime/docs/evidence/parental-dbus-system-activation/; retomada analysis/2026-10-01/parental-dbus-system-activation/CURRENT.md. VM restaurada/OFF; sem alteração no host/receita/OBS/ISO.

### Evidência adicional — cron nativo, 01/10/2026

9 controles nativos PASS, 4 negativas PAM/cronie exatas após cursor, 2 pidfds saíram e 270 testes PASS. Cron user/system non-root consultam guard experimental; duas leases ficam em monitores root. Logind não revoga jobs não-login; encerrar apenas payloads fixture confiáveis libera leases e preserva conta comum/daemon. Enrollment/PAM geração antiga/nova exercitados. Pacotes oficiais temporários removidos, VM restaurada/OFF. Rotulagem fixture normalizada conforme regras antigas daVM, sem qualificar labelingstock deISO; tentativa via launcherunit não qualificada. Não fecha proteção parental nem quiescência geral. Consolidação SSH/systemd/D-Bus/cron no README; próximo reinício/recuperação e logout/lingering faltantes. Evidência worktrees/desktop-parental-registry-lifetime/docs/evidence/parental-cron/; retomada analysis/2026-10-01/parental-cron/CURRENT.md. Sem host/receita/OBS/ISO alterados.

### Evidência adicional — reinício real e recuperação, 01/10/2026

20 controles nativos e 270 testes Python PASS, mais verificador offline. Dois reinícios de kernel preservaram barreiras duráveis: recuperação normal bloqueia geração recovering sem enrollment; falha42 do helper mantém estado bloqueado. Lingering automático supervisionado e retry manual negados por PAM/status224; conta comum inicia em ambos. VM restaurada/OFF; commit local f6a86f8, sem push/PR ou alteração host/receita/OBS/ISO. Hook exclusivoVM, kernel enforcing=0 com Enforcing anteslogind, sem qualificar ISO/earlyboot/logout interativo ou perda de energia. Recuperação autorizada e ciclo realNSS ainda pendentes; proteção completa NO-GO. Próximo: lacunas de logout/revogação e contrato de recuperação/ciclo real de contas. Evidência worktrees/desktop-parental-registry-lifetime/docs/evidence/parental-registry-boot/; retomada analysis/2026-10-01/parental-registry-boot/CURRENT.md.

### Evidência adicional — saída normal GDM e lingering, 01/10/2026

8 controles nativos PASS (um reproduz lacuna), 270 testes Python e verificador offline PASS. Sessão ELF sai normalmente0 após30s; payload/worker pidfds saem e PAMfecha, mas manager com lingering conserva lease e begincontinuaBusy. Revogação explícita só da supervisionada libera lease e permite tombstone, preservando PIDdo GDM e managercomum; marcadorlinger não autoriza restart/PAM224. Isso não qualifica logoutUI GNOME, desbloqueio, ISO ou quiescênciageral. Tentativapreliminar distinguia incorretamente sessão Class=manager de login; corrigidoharness, limpezaPASS. VMrestaurada/OFF; commitlocal1243df5, sempush/PR/host/receita/OBS/ISO. Auditlost1/2/3, seminventárioAVCcompleto. Evidência worktrees/desktop-parental-registry-lifetime/docs/evidence/parental-session-exit/; retomada analysis/2026-10-01/parental-session-exit/CURRENT.md. Próximo: contrato explícito de recuperação autorizada/ciclo real de contas e decisãoADR antesbackendprodutivo; parental completo NO-GO.

### Contrato técnico para decisão — 01/10/2026

Consolidado documento revisável worktrees/desktop-parental-registry-lifetime/docs/parental-lifecycle-recovery-contract.md, referenciado pela ADR0008; commitlocal4e5fec7, sempush/PR. Propõe coordenadorintegrado, root/adminirrestrito como autoridadeconfiável, papéisseparados e reparotécnico preservandopolítica; boot sem enrollment, barreira antesquiescência, inibição/revogação porprodutor e recuperaçãoautorizada comnovageração. Classificaçãopersistente/adaptadores ainda exigemdesenho e gate; nãoportar fixturescomoproduto. 12referênciaslocais/diffcheckPASS, VMcontinuaOFF/restaurada, semhost/receita/OBS/ISO. Direção técnicaaguardadecissão explícita AGENTS.md; nãoconstituiaprovaçãoADRinteira, release, legal, aferição/retirada/retencão. Retomada analysis/2026-10-01/parental-lifecycle-contract/CURRENT.md.

### Coordenador experimental — 02/10/2026

Direção técnica autorizada nesta conversa por “continue” após apresentação do contrato. Commit local `9912d48`: gate de transição recusa cobertura ausente após barreira persistente, inclusive com zero leases; reconciliação bloqueada não reinscreve e associação saudável não é declarada verificada. Passaram 10 controles nativos, 286 testes Python (16 novos) e verificador offline. VM restaurada/OFF. Modelo de classificação e adaptadores sintéticos não são cobertura produtiva; classificação persistente, adaptadores reais/inibição, Polkit, revisão monotônica e ciclo real de contas continuam pendentes. Nenhum host/receita/OBS/ISO alterado nesta implementação. Contrato e limites em worktrees/desktop-parental-registry-lifetime/docs/evidence/parental-coordinator/README.md; retomada analysis/2026-10-02/parental-coordinator/CURRENT.md. Proteção completa continua NO-GO.

### Índice persistente de papéis — 02/10/2026

Commit local `7de92c0`, sem push/PR: módulo experimental remove associação estática do override PAM, consulta papéis explícitos root-only e cruza contexto SELinux. Rodada final de 20 controles concluída, 286 testes Python existentes e verificador offline PASS. Três controles reproduzem falha de disponibilidade: índice ausente/corrompido/inseguro bloqueia conta comum; classificação ainda NÃO qualificada. Registro transacional ausente/corrompido preserva conta comum explicitamente classificada. Harness corrigido para restauração atômica0600, tentativa inválida preservada. VM restaurada/OFF; sem host/receita/OBS/ISO alterado. Próximo: fonte independente que preserve ordinary quando classificador falhar, mantendo Unknown bloqueado; depois adaptadores reais e cicloNSS/recuperação. Parental completo NO-GO. Evidência worktrees/desktop-parental-registry-lifetime/docs/evidence/parental-role-index/README.md; retomada analysis/2026-10-02/parental-role-index/CURRENT.md.

### Conta comum independente do estado parental — 02/10/2026

Commit local `db59571`, sem push/PR: variante experimental exige declaração positiva separada porUID, tupla completa e MAC pendente unconfined/Enforcing. Seis falhas exclusivamente parentais preservam a comum e recusam a supervisionada; sem declaração válida não há fallback ordinary. Passaram 26 controles nativos, 286 testes Python existentes e verificador offline. VM restaurada/OFF; sem alteração host/receita/OBS/ISO. Falha da própria declaração ainda bloqueia a comum; declaração obsoleta e MAC comum podem conservar acesso: retirada durável antes de supervisão/cutover crash/concorrência/NSSreuse ainda NÃO implementados/qualificados. Proteção completa NO-GO. Próximo gate: transação de retirada dessa autoridade, sem reconstrução automática, e inibição/revogação das atividades antigas. Evidência worktrees/desktop-parental-registry-lifetime/docs/evidence/parental-ordinary-attestation/README.md; retomada analysis/2026-10-02/parental-ordinary-attestation/CURRENT.md.

### Retirada durável da autorização comum — 02/10/2026

Commit local `2be5102`, sem push/PR: controlador experimental publica marcador negativo antes de journal e retirada da declaração, compartilhando lock porUID com o snapshot PAM. Passaram 33 controles nativos e 294 testes Python (8 novos), verificador offline e diffcheck. Quatro interrupções de processo após fsync preservam negação; autorização negada/conflito não iniciam efeito, retomada só retira, retries não reinscrevem, declaração antiga restaurada e journal órfão/corrompido não reabrem. Manager comum admitido antes continua ativo: falta revogação e quiescência; outro manager supervisionado preservado, sem teste de segunda comum intacta. VM restaurada/OFF; nenhum host/receita/OBS/ISO alterado. Não é reboot/queda de energia, revisão monotônica global, Polkit, supervisão publicada ou lifecycle NSS. Próximo: reboot real, isolamento de outra comum e concorrência/cutover, integração ao gate de classificação e adaptadores reais obrigatórios. Proteção completa NO-GO. Evidência worktrees/desktop-parental-registry-lifetime/docs/evidence/parental-ordinary-withdrawal/README.md; retomada analysis/2026-10-02/parental-ordinary-withdrawal/CURRENT.md.

### Retirada após reinício real e outra conta comum — 02/10/2026

Commit local `67c9c51`, sem push/PR: guard/protocolo anteriores inalterados, helpers exclusivos da VM. 17 controles (4+7+6), dois reboots reais/trêsbootIDs e 294 testes Python existentes PASS. Conta alvo negada por lingering/retry após marker-only crash; segunda comum JÁ existente inicia nos dois boots e sua declaração/locks/PID porboot são preservados. Hook normal só inspeciona; hookfalha42 apósEnforcing não muda bloqueio. Resume autorizado só retira provaalvo, retry idempotente mantém journal2/marker. VMrestaurada/OFF; sem mutaçãoNSS ou host/receita/OBS/ISO. Não é earlyboot/ISO, falhaantesEnforcing/fsync, quedaenergia ou revogação semreboot; proteção completa NO-GO. Próximo: integrar autoridade negativa ao coordenador e qualificar concorrência/adaptadoresreais antes lifecycle/publish. Evidência worktrees/desktop-parental-registry-lifetime/docs/evidence/parental-withdrawal-boot/README.md; retomada analysis/2026-10-02/parental-withdrawal-boot/CURRENT.md.

### Coordenador de retirada e concorrência real — 02/10/2026

Commit local `cde031f`, sem push/PR: OrdinaryCoordinator compõe protocolo anterior e lista REQUIRED completa; marker/proofretirada antecedem cobertura, sem método Unix/publish. Passaram16controles nativos, três disputas reais de dois processos (um UnsupportedProducergravado, umBusy porrodada; retryperdedorConflict), 313testesPython/19novos e verificadoroffline. PID/prova da outra comum preservados; lockalvo não impede plano/admissão deoutraUID. Ausênciadeprodutores recusaMESMOzeroprocessos, manager antigo continuaativo antesstopfixture: revogação/quiescência nãoqualificadas. Fakeadapters positivos sógrafo/unidade; native ZEROadaptadoresprodutivos. VMrestaurada/OFF; nenhuma alteraçãohost/receita/OBS/ISO ouNSS. Próximo: adaptadoresREAIS de classificação/manager/inibição/revogação mantendoREQUIRED, revisão/journalglobal e depoislifecycle; proteção completaNO-GO. Evidência worktrees/desktop-parental-registry-lifetime/docs/evidence/parental-ordinary-coordinator/README.md; retomada analysis/2026-10-02/parental-ordinary-coordinator/CURRENT.md.


### Atualização de 02/10/2026 — classificação e revogação de manager

Commit local 72d09e0: adaptadores experimentais verificam a retirada comum e
revogam o gerenciador de usuário via logind/systemd com autorização explícita e
espera limitada. 13 controles nativos e 334 testes passaram; restauração da VM
conferida e VM desligada. O usuário comum independente continuou funcionando;
novas admissões do alvo foram rejeitadas, inclusive com linger habilitado.
Primeira tentativa recusou quiescência durante teardown assíncrono do logind;
falha preservada e matriz completa repetida após correção. Cobertura de GDM,
SSH, system-units, D-Bus e cron segue pendente; REQUIRED não foi reduzido e o
coordenador com só esses dois adapters continua UnsupportedProducer. Sem
mutação NSS, instalação parental no host, OBS ou ISO. NO-GO #6/#102 mantido.
Retomada: analysis/2026-10-02/parental-manager-adapters/CURRENT.md.


### Atualização de 02/10/2026 — GDM password e SSH experimentais

Commit local 81134f9: LoginRoute verifica a rota e usa revogação nativa do
logind/systemd, preservando os daemons compartilhados. Wrapper PAM SSH inclui
checagem de conta antes de forwarding e o guard histórico de sessão/MAC.
25 controles nativos e 344 testes passaram; quatro tentativas falhas de fixture
foram preservadas separadamente e não contam como qualificação. A revogação
encerrou payloads, root monitors SSH e worker GDM observados por pidfds;
novas admissões foram recusadas com causas PAM explícitas e o peer preservado.
Readmissão GDM usa recriação explícita do display da fixture ELF. GNOME completo,
worker oficial, retorno automático do greeter, todas as rotas GDM e conversas
pendentes não foram qualificados. REQUIRED permanece inteiro e os quatro
callbacks experimentais ainda recusam falta de system-units/D-Bus/cron.
Não considerar GDM password como cobertura global de GDM. VM restaurada e
desligada; shadow/backup, PAM, GDM e SSH conferidos; sem instalação parental
no host, OBS ou ISO. NO-GO #6/#102 mantido. Próximo: serviços/timers User=.
Retomada: analysis/2026-10-02/parental-login-adapters/CURRENT.md.


### Atualização de 02/10/2026 — serviços e timers registrados

Commit local1269fca: adaptador experimental inibe catálogo root explícito com
máscaras persistentes e revoga timers antes de serviços. Sem unmask automático
ou mutação NSS. 25 controles nativos e6 adicionais do armazenamento de máscaras
passaram;364 testes Python, incluindo20 novos. Serviços sem PAM sobreviveram
à retirada/logind, mas o adaptador os encerrou e impediu novas ativações,
preservando o serviço, timer, manager e proof do peer. Unidade extra inativa,
fonte alterada e perda de máscara recusaram conclusão; reparo explícito e
retries mantiveram negative authority. Primeira tentativa falhou no driver
write_text(bytes), foi preservada e a matriz completa repetida. VM restaurada
e desligada. Namespace global/descoberta/recoveryboot/globaljournal ainda não
qualificados; REQUIRED permanece inteiro, NO-GO #6/#102 mantido. GDM/SSH do
gate anterior não foram requalificados como completos. Próximo:D-Busactivation,
depoiscron. Sem alterações parentais no host/OBS/ISO.
Retomada: analysis/2026-10-02/parental-unit-adapter/CURRENT.md.


### 02/10/2026 — adaptador D-Bus registrado (experimental)

Commit local 3d80494, worktree desktop-parental-registry-lifetime, sem push/PR.
24 controles D-Bus reais + 8 de persistência + 384 testes Python PASS.
Inibição retém definições de Exec+User/SystemdService e ReloadConfig antes de
revogar somente payloads cadastrados; reativação alvo negada, peer e barramento
preservados. Catálogo desconhecido/alterado e autorização negada recusam.
VM restaurada/desligada; sem alterações parentais no host/receita/RPM/OBS/ISO.
Escopo fixture, sem pendências de ativação/reboot/powerloss/namespace completo.
Issues #6/#102 OPEN e parental NO-GO. Próximo adapter cron; depois inventário,
autoridade/recuperação global, cobertura login e lifecycle/UI/release.
Retomada: analysis/2026-10-02/parental-dbus-adapter/CURRENT.md.


### 02/10/2026 — adaptador cron registrado (experimental)

Commit local fbf3932, sem push/PR. 19 controles nativos finais e 404 testes
Python PASS; duas tentativas anteriores preservadas com suas causas e limpeza.
PAMaccount bloqueia novos jobs por usuário e /etc/cron.d; revogação com pidfds
somente nos payloads registrados, monitores root encerram naturalmente, peer e
daemon preservados. RPMs temporários removidos e versões originais verificadas;
VM restaurada/desligada. Sem alteração parental no host/receita/RPM/OBS/ISO.
Issues #6/#102 OPEN; parental NO-GO. Todas famílias têm algum protótipo, não
cobertura completa. Próximo inventário/autoridade/política de cobertura, depois
recuperação global, pendências login/GDM e lifecycle/UI/release.
Retomada analysis/2026-10-02/parental-cron-adapter/CURRENT.md.


### 02/10/2026 — gate experimental de inventário

Commit local a0e8b2f, sem push/PR. 23 controles nativos de inventário/recusa e
433 testes Python PASS. Planos vinculados a UID/operação/proofhash e snapshot,
revisão local, rotas e adaptadores; mudanças antes da autorização impedem
retirada, mudanças após a barreira conservam bloqueio. Os sete nomes de famílias
não certificam cobertura completa; default whole-account continua recusado.
Somente 2 adaptadores reais no ensaio, demais explícitos unsupported; sucesso
registered-test nos testes sintéticos não qualifica conta real. VM restaurada,
desligada; sem host/receita/RPM/OBS/ISO parental alterado. #6/#102 OPEN/NO-GO.
Próximo journal durável/ownership/retomada bloqueada, depois inventário real e
qualificação completa/GDM/NSS/UI/release. Revisão local não é antirollback global.
Retomada analysis/2026-10-02/parental-inventory-gate/CURRENT.md.


### 03/10/2026 — journal durável de retirada de admissão

Commit local 8966274, sem push/PR. 31 controles nativos PASS na primeira execução
e 455 testes Python PASS (22 novos). Owner vinculado à identidade, operação,
prova e inventário; oito crashes reais de processo preservam bloqueio PAM;
retomada exige nova autorização, mantém fases e retries concluídos read-only.
VM restaurada/desligada, evidências e hashes verificados. Sem produto/host/OBS
alterado. #6/#102 OPEN/NO-GO. Não prova quiescência, reboot/powerloss, autoridade
global monotônica ou antirollback. Próximo: reboot real com operação pendente;
depois ownership das inibições persistentes, inventário completo e demais gates.
Retomada analysis/2026-10-03/parental-operation-journal/CURRENT.md.


### 03/10/2026 — owner persistente após reboot real

Commit local b47e250, sem push/PR. 19 controles nativos PASS, dois reboots reais
com três boot IDs. Operação pendente mantém barreira/owner/locks/inventário;
retomada exige autorização e original binding. Segundo boot com helper falhando
42 após Enforcing conserva bloqueio e conta comum; retry concluído read-only.
VM restaurada/desligada, SHA/verificador offline PASS. Baseline455Python anterior
reutilizada sem mudança no núcleo. Sem produto/host/OBS alterado. #6/#102 OPEN,
parental NO-GO. Próximo ownership das inibições persistentes systemd/D-Bus,
depois autoridade global/inventário completo/GDM/NSS/Polkit/UI/release.
Retomada analysis/2026-10-03/parental-operation-boot/CURRENT.md.


### 03/10/2026 — ownership das inibições persistentes (filesystem)

Commit local132e78c, sem push/PR. 36 controles nativos finais e 482 testes
Python PASS (27 novos). Masks/DBusretirements privados vinculados ao owner
durável, identidade, inventário, versões e recurso; intentantesefeito, retomada
autorizada e completedretryreadonly; conflitos entreUIDs negados, lockglobal
estável. Duas falhas nativas preservadas: importação de helper e diagnóstico
de lock ausente; correção e regressão na nova camada. VMrestaurada/desligada,
verificador/hash/diffcheck PASS. Sem host/produto/OBS alterado. #6/#102 OPEN/NO-GO.
Escopo FS: não integração com produtores vivos, reload/revocation/reboot deste
ledger. Próximo integração scopedliveSystemUnits/DBusActivation e recuperação;
depois autoridadeglobal/inventário completo/GDM/NSS/Polkit/UI/release.
Retomada analysis/2026-10-03/parental-owned-inhibitions/CURRENT.md.


### 03/10/2026 — ownership integrado a produtores vivos

Commit local 8866124, sem push/PR. 57 controles nativos PASS (29 units,
28 D-Bus), sem tentativas falhas; suíte completa496Python PASS (14 novos).
Interfaces read-only verificam owner/fenced/inventário/identidade atual antes
dos adapters upstream; reload e revogação autorizada reais preservam peer,
manager/proof e broker. Journals não reescritos; recurso perdido não reparado
automaticamente. VM restaurada/desligada, SHA/verificador/diffcheck PASS.
Sem host/produto/OBS alterado. #6/#102 OPEN, parental NO-GO. Escopo fechado,
sem whole-account coverage, reboot deste ledger ou antirollback qualificados.
Próximo: reboot real das barreiras e ledger owned com recuperação bloqueada;
depois races/autoridade global/inventário completo/GDM/NSS/Polkit/UI/release.
Retomada analysis/2026-10-03/parental-owned-live/CURRENT.md.


### 03/10/2026 — barreiras owned systemd após reboot real

Commit local69c46fc, sem push/PR. 43 controles nativos PASS (6+20+17),
dois reboots reais/três bootIDs, primeira execução das matrizes. Registros
owned e máscaras/inodes persistem; pendingaftereffect requer autorização
para completar journal; hookreadonly ou falhando42 mantém bloqueio, peer
auto-admitido e timerativo. Baseline496Python anterior reutilizada/hash-bound,
não rerodada; núcleo histórico intacto. VMrestaurada/desligada, readers
independentes/SHA/verificador/diffcheck PASS. Probe final wholecoordinator
legacyresume autorizado troca inode do journal legado com mesmos bytes;
readonlyclaims não se aplicam a esse probe, nem antirollback/earlyboot/global
coverage. Sem host/produto/OBS alterado. #6/#102 OPEN/NO-GO. Próximo reboot
D-Bus com fixtures persistentes, depois races/inventário/autoridade/GDM/NSS/
Polkit/UI/release. Retomada analysis/2026-10-03/parental-owned-unit-boot/CURRENT.md.


### 03/10/2026 — barreiras owned D-Bus após reboot real

Commit local7df60c0, sem push/PR. 51 controles nativos PASS (10+22+19),
dois reboots reais/três bootIDs, primeira execução das matrizes. Registros
owned e retirements/inodes persistem; pendingaftereffect requer autorização
para completar sójournal; hookreadonly ou falhando42 mantém targetPAM/routes
bloqueados, peeradmitido e rotasExec/SystemdService ativáveis. Broker epeer
PIDs preservedwithinboot; não entrekernelboots. Baseline496Python anterior
reutilizada/hash-bound, não rerodada; núcleo histórico intacto. Wholeprobe
readonly._check semlegacyresume mantém todosproof/journalinodes. VMrestaurada/
desligada, readersindependentes/SHA/verificador/diffcheck PASS. Sem host/
produto/OBS alterado. #6/#102 OPEN/NO-GO. Escopo closednamespace, semearlyboot/
wholecoverage/antirollback/powerloss. Próximo pendingactivation e races
retire/reload/stop/falhastransporte; depois inventário/autoridade/GDM/NSS/
Polkit/UI/release. Retomada analysis/2026-10-03/parental-owned-dbus-boot/CURRENT.md.


### 03/10/2026 — ativações pendentes e falhas D-Bus

Commit local06cda1a, sem push/PR. 28 controles nativos PASS/primeira execução.
Duas ativações realmente pendentes (SystemdService/Exec), PIDfds e SIGSTOP
antesnome. ReloadConfig/StopUnit falhando não permitem success; callback
completed-only perde Exec em interleaving de stop, observerdetecta atividade
e recusa quiescência. Registro rootfixture da observação pinned permite stop
autorizado, preservando peer/broker/journals. NÃOdescoberta de produto nem
qualificação ampla de races. Originalclients rc1 cancelled (não success).
Baseline496Python reused/hash-bound, não rerodada; VMrestaurada/desligada,
SHA/verificador/readers/diffcheckPASS, semhost/produto/OBS alterado. #6/#102
OPEN/NO-GO. Próximo inventário verificado pending/recapture bounded e falhas
de transporte, depois coverage/persistência/NSS/GDM/Polkit/UI/ISO. Proposta
de primeiraentrega em worktree/docs/parental-first-release-scope.md organiza
marcos mas NÃOaltera contrato/gates; redução escopo depende decisão.
Retomada analysis/2026-10-03/parental-pending-activation/CURRENT.md.


## Entrega — descoberta automática de pendentes — 03/10/2026

Commit local c3dea1c (worktree desktop-parental-registry-lifetime, sem push/PR).
Catálogo fechado descobre automaticamente ambos produtores pendentes com pidfds,
sem registro manual. Recaptura limitada encontra produtor tardio; atividade que
reaparece esgota o limite e recusa sucesso. Processo desconhecido e executável
inseguro recusam antes de qualquer parada. Resposta omitida pelo backend após
stop real mantém bloqueio (não ensaio de desconexão literal). Peer/broker e
journals preservados. 23 controles VM e suíte Python completa 504 PASS, incluindo
8 novos testes. Evidência/hash/verificador PASS, VM restaurada/desligada.
Não qualifica cobertura global nem produção: #6/#102 OPEN, parental NO-GO.
Próximo: autoridade confiável de inventário/cobertura além catálogo fechado;
depois persistência, NSS, GDM, Polkit/UI e ISO. Escopo não reduzido silenciosamente.
Retomada analysis/2026-10-03/parental-pending-discovery/CURRENT.md.


## Entrega — conferência de mudanças nas fontes — 03/10/2026

Commit local f1f8471, sem push/PR. Guard experimental detecta fontes novas,
removidas, alteradas ou substituídas em árvores declaradas, antes/depois de
 autorização e de cada efeito; mudanças invalidam plano. Lock permanente confere
identidade e exclui escritores cooperantes durante efeitos, sem prender autorização.
530 testes Python PASS, incluindo 26 novos; filesystem/flock reais e dois testes
sintéticos integrados à descoberta. Nenhum ensaio VM novo/nenhuma mudança produto.
Não emite cobertura global: #6/#102 OPEN/NO-GO. Próximo validar guard junto ao
adaptador D-Bus real na VM e reconciliar fontes/configuração carregada.
Retomada analysis/2026-10-03/parental-namespace-guard/CURRENT.md.


## Entrega — fontes e visão carregada D-Bus — 03/10/2026

Commit local 61253d3, sem push/PR. Guard integrado ao adaptador e à descoberta
na VM: nova fonte após autorização recusa antes de qualquer stop; nova fonte
entre paradas recusa a segunda. Rota já presente/não classificada impede plano.
Reparo explícito + reload + plano novo drena remanescente, preservando bloqueio,
journals, peer/broker. 24 controles nativos e538 Python PASS (8novos). VMrestaurada
/desligada, evidências/hash/verificadorPASS. Duas árvores e prefixofechado apenas,
não cobertura global nem produto; #6/#102 OPEN/NO-GO. Próximo determinar fontes
/configuração upstream efetivamente usadas e classificar rotas alémprefixofixture.
Retomada analysis/2026-10-03/parental-namespace-dbus/CURRENT.md.


## Entrega — levantamento das fontes D-Bus instaladas — 03/10/2026

Commit local dc057da, sem push/PR. Índice de20arquivos e6dependências encontra
vendorpolicy e overrideoptional fora do guard anterior. Probes do broker36 real
confirmam também /usr/local/share e /lib (/usr/lib) para ativação. /etc e /run
servicedirs não carregam nesta configuração. Não confundir latestupstream com
versão instalada. 12 controles VM e554PythonPASS (16novos); fontes/probes removidos,
broker/config/PAM/contas preservados; VMdesligada/statussalvo. Índiceobservacional,
não parser/precedência/identidadecarregada/coberturaglobal. #6/#102OPEN/NO-GO.
Próximo vincular grafo/raízes reais/ausências opcionais ao plano antes dos efeitos.
Retomada analysis/2026-10-03/parental-dbus-config/CURRENT.md.


## Entrega — ausências opcionais vinculadas ao plano — 04/10/2026

Commitlocal 5a43c30, sempush/PR;8VM+570PythonPASSincl16novos. Plano capta20filesgrafo+overrideoptional,2policytrees+3serviceroots reais ealiasexato/lib. Criar override/alternativeRoot invalidaoldplan e fonte não classificada impede newplan; vendorpolicybetweencallbacks impede2ºmarker. Marcadoresreadonly: NÃO nova qualificação de revogação real. VMrestaurada/desligada/hash/verifierPASS, no productchanges, #6/#102OPEN/NO-GO. Próximo classificar serviços/precedência/duplicidade efonte semadaptador. Retomada analysis/2026-10-04/parental-source-set/CURRENT.md.


## Entrega — declarações de serviços e duplicidade — 04/10/2026

Commitlocal d99e0b9, sempush/PR. 13definições tipadas+localUID/GID, duplicatasName
inclusivebytesidênticos e unknownfields recusados, todosprodutores exigemadapter
inclusive root. Observações12systemdunits separadas: polkit/timesyncUnitUserdiff.
8VM+586PythonPASS incl16novos; VMrestaurada/desligada/hash/verifierPASS. Não ativou
payload/revogouprocesso/nãoprova effectiveexecution/fullcoverage. #6/#102OPEN/NO-GO.
Próximo bindingSystemdService canonicalunit/fontesdropinsExecStart/localidentity,
Execdirect separate. Retomada analysis/2026-10-04/parental-service-catalog/CURRENT.md.


## Entrega — referências configuradas do systemd — 04/10/2026

Commit local 3e74641, sem push/PR. Referências tipadas de unidade canônica,
identidade configurada, ExecStartEx e fingerprints de fontes/drop-ins/executável/contas.
602 testes Python (16 novos) e 15 controles VM passaram. Nove referências aceitas;
polkit/logind notify-reload e timesyncd ambient recusados pelo subconjunto atual.
Duas tentativas nativas falhas preservadas. VM conferida e desligada.
Não prova credenciais efetivas/cobertura global/ativação ou revogação real.
Próximo: processo real + adaptador de ativação/revogação, tratamento explícito
para os três casos recusados. #6/#102 abertas, parental integral NO-GO.
Retomada: analysis/2026-10-04/parental-systemd-reference/CURRENT.md.


## Entrega — vínculo com o processo principal — 04/10/2026

Commit local d87d2b0, sem push/PR. Referência de configuração ligada a processo
principal com pidfd, UID/GID/grupos/capacidades/executável/argv/cgroup conferidos.
620 testes Python (18 novos), nove controles VM PASS. Edição real da unidade e
exec com mesmo PID/ticks/pidfd invalidam a referência. Primeira tentativa falha
arquivada; VM conferida/desligada. Ainda sem cobertura integral ou adaptador de
revogação qualificado. Próximo: integrar ao backend de unidades existente sob
autorização/inibição, qualificar mudança/reinício antes de StopUnit e conta comum.
#6/#102 abertas, full parental NO-GO. Retomada:
analysis/2026-10-04/parental-running-reference/CURRENT.md.


## Entrega — parada de unidades integrada — 04/10/2026

Commit local e2fff42, sem push/PR. Adaptador existente confere referências de
processo antes de parar unidades sob máscaras registradas. Exec/restart durante
autorização recusam antes de efeitos; novo lote para timer antes dos serviços
e preserva conta comum. 638 testes Python (18 novos) e17 verificações VM PASS.
Tentativas/evidências divergentes anteriores preservadas; artefatos finais conferem.
VM restaurada/desligada. Próximo: job upstream/ativação concorrente/check→efeito,
resultado incerto e drenagem do cgroup com journal conservando bloqueio.
Ainda sem cobertura integral/produção; #6/#102 abertas, full parental NO-GO.
Retomada: analysis/2026-10-04/parental-guarded-unit-stop/CURRENT.md.


### Continuação isolada — 04/10/2026 — paradas com resposta incerta

Commit local dc2317a, sem push/PR/publicação. 658 testes Python (20 novos) e
19 verificações VM passaram. Estado técnico do StopUnit vinculado à operação
negativa; perda real de resposta preserva bloqueio e recusa reenvio. Reconciliação
nova observa pai/filho e cgroup drenados. Conta comum preservada. Duas falhas
arquivadas; restauração independente, VM desligada. Evidências:
worktrees/desktop-parental-registry-lifetime/docs/evidence/parental-unit-stop-jobs/.
Próximo: cold/noMainPID, saída durante captura/autorização, serviço PAM e ativação
indireta. Cobertura integral continua NO-GO; #6/#102 abertas. Sem mudanças em
produto/host/RPM/OBS/ISO. Ponto de retomada:
analysis/2026-10-04/parental-unit-stop-jobs/CURRENT.md.


### Pausa — 04/10/2026 — serviços inativos

676 testes Python (18 novos) e20 verificações VM PASS. Etapa isolada cold/mixed
implementada, ainda não commitada. Serviços inativos conferem job/cgroup/fences sem
IPC ou falso journal completed. InvocationID não garante histórico de execuções;
limitação e falhas arquivadas. PAM negou novas entradas após retirada; atribuição/
revogação de serviço PAM já ativo permanece pendente. VM restaurada e desligada.
Primeiro na retomada: formalizar provenance/verificador, revisar e fazer commitlocal;
depois seguir PAM ativo. Controle parental integral NO-GO, #6/#102 abertas.
Checkpoint: analysis/2026-10-04/parental-cold-unit-stop/CURRENT.md.


### Atualização — 05/10/2026

Serviços inativos formalizados/commit6b52365,676tests/20VM/verifierPASS.
PAMnovo aindaWIP/nãocommitado:693testsPASS, VMentrada no perfil mínimo recusada,
falhaarquivada/restauraçãoPASS/OFF. InvestigarMAC antesqualificarrevogaçãoPAM.
Usuário priorizou recorrência da identidade: lyra-release corrigido embranch
fix/release-identity-persistence c808d68/d775286,10tests/7RPMVMpassaram. Nome local
restauradoLyraOS1.1, vendor/Updaterpreservados. Falta publicar/instalar RPMnovo,
proteçãoautomáticaaindapendente. OBSsomenteLeap16.1, sempush/PR/publicaçãoagora.
Retomada: analysis/2026-10-05/release-identity/CURRENT.md.

Atualização 05/10: perfil PAM fechado qualificado local4c613f6; 18testes/694suite/16VM e4restauraçõesPASS, overlayOFF. Adicionado setupSELinux ao perfil, guardintacto. Parada de principal+helper/reentradanegada/peerpreservado. GlobalcontinuaNO-GO; próximo principalexit/helperalive antesautorização. Ver analysis/2026-10-05/parental-pam-unit-stop/CURRENT.md.

Atualização 05/10: principalexit/helperalive qualificado localfdd2a86, 20específicos/696suíte/19VM/4restauraçõesPASS. MainPID0/Job0 nãoquiescência comhelperalive/cgroup1; ConflictantesIPC e freshtentativa recusadaantesauth. Coreguardintacto; atraso closefixture<=30s onlyVM, overlayOFF. Próximohelpernão-drena/recuperaçãosegura. GlobalcontinuaNO-GO. Ver analysis/2026-10-05/parental-pam-main-exit/CURRENT.md.

05/10: entrega lyra-release concluída: RPM 1.1-lp161.2.1 instalado, SR1382519 aceito, publicação pública/gate completo/assinaturas/hash conferidos, PR145 integrada. Proteção local ativa; não reinstalar nem aguardar OBS deste pacote. Qualificação da ISO por checksum permanece pendente. Prioridade volta ao controle parental, recuperação segura do auxiliar PAM que não drena (fdd2a86 já qualifica recusa diante de MainPID0/Job0 e helper vivo).


Atualização 05/10/2026: recuperação PAM com origem retida (fbbe05b), 20 testes específicos/716 suíte/22 controles VM/quatro restaurações/verifier PASS. Um StopUnit real; reautorizações sem reenvio; conclusão após pidfds/cgroup/job drenados. VM desligada. Camada experimental, sem publicação; perda do contexto/restart/reboot e término forçado de PAM travado permanecem pendentes. Controle parental integral NO-GO, #6/#102 abertas. Detalhes: analysis/2026-10-05/parental-pam-helper-recovery/CURRENT.md.


Atualização 05/10/2026: reconciliação PAM em consumidores separados (e6770f5), 28 específicos/744 suíte/29 controles VM/quatro restaurações/verifier PASS. Origem root protegida ligada a operação/boot/rota/fontes/invocação; auxiliar vivo recusado, cold só com autorização nova, sem IPC novo. Sete processos sem pidfds herdados; um StopUnit original. VM OFF. Modelo experimental: restart de serviço real, saída abrupta/crash/powerloss e PAM travado permanecem pendentes. Próximo: injetar saída abrupta nos pontos de persistência/IPC. Controle parental integral NO-GO; #6/#102 abertos. Detalhes: analysis/2026-10-05/parental-pam-daemon-recovery/CURRENT.md.


Atualização 05/10/2026: saída abrupta de consumidor em quatro fronteiras (3a6a57c), 744 testes/4 casos VM18+19+19+19=75 controles/16 leitores restauração/verifier PASS. Os._exit91 sem finally, inclusive após reply real antes de accepted; sem reenvio ou falsa conclusão. Bloqueios/owner/prova/peer preservados. VM OFF. Consumidores experimentais: não daemon produção/reboot/powerloss/atomic em andamento. Próximo: timeout NATIVO do systemd para helper bloqueado além do timeout efetivo, sem kill/policy Lyra. Controle integral NO-GO; #6/#102 abertos. Detalhe: analysis/2026-10-05/parental-pam-crash-recovery/CURRENT.md.


Atualização 05/10/2026: timeout NATIVO systemd (087dd64), 744 suíte/24 controles VM/quatro restaurações +leitor diagnóstico/verifierPASS. Helper fechado held300s morto após90s pelo SIGKILL do PID1 comprovado em kerneltrace filtrado; marker só retirado após drain/reconciliação. UM StopUnit, nenhum kill próprio; guards/prova/owner/máscaras/peer intactos. VM OFF, tracing/loglevel restaurados. Não qualifica D-state/PAM geral/policy SendSIGKILLfalse/daemon real. Próximo: reboot REAL controlado com operação pendente, recusa entre boots sem recuperar PID/job/admissão. Controle integral NO-GO, #6/#102 abertos. Detalhe: analysis/2026-10-05/parental-pam-native-timeout/CURRENT.md.


## Controle parental — reboot real qualificado em 05/10/2026

Worktree desktop-parental-registry-lifetime, branch test/parental-registry-lifetime,
HEAD ff9fb8b12545bf1fde0f1b3cdb9d444a288a91ec, commit local sem push/PR. Evidência
`docs/evidence/parental-pam-reboot/`, verifier PASS. 744 testes da suíte,
14 controles pré-boot + 7 pós-boot; quatro leitores de restauração PASS e
leitor adicional de perfil/marker/effects/SELinux original PASS.

Worker os._exit91 no accepted durável, UM StopUnit, consumidor fresco sameboot
Busy sem reenvio. systemctl reboot REAL, QEMU99804 EXIT0 (-no-reboot), mesmo
qcow2 relançado QEMU71482. UUID ef6d2bf1-1883-47aa-becd-2148c56a7f8e ->
54aaba94-0a4a-4eec-9a63-f2b52e441c47. Dois consumidores distintos recusaram
RecoveryRequired ANTES de autorização, nenhum pidfd herdado/IPC/job reutilizado,
cgroup0/job0 não completam registro de boot anterior. Hash/inode/owner/mode dos
artifacts de prova/ledger/effects e máscara /dev/null idênticos após reboot.
Máscara nega producerStart; teste causal PAM semmask recolocando MESMOinode
falha224; user@1002 também224; peerproof intacta/admissão nova peer1000 PASS.
Cleanup0, SELinux Permissive original, fixture removida. VM
/tmp/lyra-parental-pam-reboot-20261005/system.qcow2 OFF; segundoQEMU71482 EXIT0,
poweroff RPC0; backing /tmp/lyra-parental-identity-20260928/system.raw intacto.
Não é rollback integral FS, nem recuperação autorizada entre boots.

Próximo: desligamento ABRUPTO da VM com efeito pendente; qualificar recusa segura
após boot novo sem equiparar reboot gracioso a powerloss. Escrita/rename/fsync
interrompidos, antirollback, daemon real, PAM geral/D-state/cobertura global,
root compartilhado/notify-reload/caps/threads/subgrupos/NSS/GDM/Polkit UI/
privacidade/ISO continuam pendentes. Controle parental integral NO-GO; #6/#102
abertos. Não instalar/promover este fixture na estação; OBS somente Leap16.1.
Preservar root kiwi/config.xml e drafts usuário; planos root append-only.
Nenhum subagente. Fixture isolada autorizada. Etapas anteriores já PASS:
087dd64 timeout nativo (744/24VM), 3a6a57c quatrocrashes, e6770f5 coldconsumer.


## Controle parental — corte abrupto qualificado em 05/10/2026

Worktree desktop-parental-registry-lifetime, branch test/parental-registry-lifetime,
HEAD 5bd67e19d058703db1785fd11bf3551a1c203600, limpo/local sem push/PR. Evidência
`docs/evidence/parental-pam-powercut/`, verifier PASS: 744 suíte/15 controles
pré-corte + 8 pós-corte; quatro leitores de restauração PASS e adicional
perfil/marker/effects/SELinux original PASS. Sem alteração em módulos produção.

Primeiro ensaio FAILED com cleanup0/quatro leitores PASS preservado em
failed-unflushed-setup/. Módulo PAM recém-compilado pós-corte "file too short",
peer1000 não entrou; cinco controles registrados NÃO qualificam causalmente
PAM224 devido a fontes de instalação não validadas/duráveis. Correção fixture:
os.sync APENAS após instalar/configurar e ANTES de retirada/efeito; snapshot
instalação hash/inode/mode/owner/nlink, conferido antes de controles no bootnovo.
NENHUM sync extra após operação accepted ou logo antes corte. Não qualifica
instalador/RPM contra perdaenergia nem elimina testes das fronteiras de escrita.

Final worker os._exit91 no accepted durável, UM StopUnit, consumidor fresco
sameboot Busy sem reenvio. Precut root/BOTHmarkers/serial/boot conferidos,
MainPID0/job pendente/helper cgroup vivo/marker presente. Host pidfd QEMU com
cmdline/disco exact conferidos, SIGKILL sem shutdown guest: QEMU10383 EXIT137.
Mesmoqcow2 relançado QEMU39421; UUID 82845426-abd2-4078-a8c6-d3cd0d4eed3d ->
18475008-05aa-497a-bb61-a5e89b0eddde. Dois consumidores novos recusam RecoveryRequired ANTES
de autorização, sem pidfd herdado/IPC/job reutilizado. Hash/inode/owner/mode
provas/ledger/effects/máscara idênticos. Cgroup0/job0 não completam efeito antigo.
Fontes PAM/unidades idênticas pós-corte. Máscara nega producerStart; teste
causal PAM com mesma máscara guardada/recolocada falha224; user@1002 também224;
peerproof intacta/admissão nova1000 PASS. Cleanup0; SELinux Permissive original.
VM /tmp/lyra-parental-pam-powercut-20261005/system.qcow2 OFF, QEMU39421 EXIT0,
poweroffRPC0. Primeiro corte QEMU47740 EXIT137. Backing
/tmp/lyra-parental-identity-20260928/system.raw intacto; não rollback integral FS.

Limite: SIGKILL QEMU perde memória guest, host/cache ainda vivos. NÃO equivale
falta de energia física do armazenamento. accepted durável é UMA fronteira.
Próximo: qualificar interrupções reais de write/rename/fsync dos registros
sem completar estado parcial ou reutilizar autoridade antiga. Antirollback,
daemon real/PAM geral/D-state/cobertura global/root compartilhado/notify-reload/
caps/threads/subgrupos/NSS/GDM/Polkit UI/privacidade/ISO permanecem pendentes.
Controle parental integral NO-GO, #6/#102 abertos. Nenhuma instalação/promoção
na estação; OBS somente Leap16.1. Preservar root kiwi/config.xml e drafts usuário;
planos root append-only. Nenhum subagente. Fixture isolada autorizada.
Anteriores já PASS: ff9fb8b reboot gracioso real (744/14+7VM), 087dd64 timeout
nativo (744/24VM), 3a6a57c quatrocrashes, e6770f5 coldconsumer. Não repetir.


## Controle parental — fronteiras reais do registro accepted em 05/10/2026

Worktree desktop-parental-registry-lifetime, branch test/parental-registry-lifetime,
HEAD 5d6de08120c5f7daa5071fb2aaff4ac2478944d3, limpo/local sem push/PR. Evidência
`docs/evidence/parental-pam-atomic-cut/`, verifier PASS. Suíte744; quatrocasos
13 controles pré-corte+9 pós-boot =88VM; 16 leitores restauração+4adicionaisPASS.
Módulos produção intactos. Operação é intent->accepted APÓS UM StopUnit.

Atomic-worker instrumenta os syscalls reais do RegistryStore._atomic existente,
hash fc16655cdd5a2f633bd11566a48c8002617a793061c9175c6be0e282c9b317f3
igual parental-registry-barrier/writer.py (guest nome barrier-writer.py).
Pontos: partial-write (os.write metadepayload), temp-fsynced, renamed ANTES
fsyncdiretório, directory-fsynced. Counters/ready tmpfs e SIGSTOP worker.
Checkpoint gravado ANTESworker; sem auditoria/checkpoint/fsync guestdisco após
pausa. Setup os.sync ANTESwithdrawal, snapshotfontes conferido pós-boot.
Host valida root/BOTHmarkers/serial/boot/workerT/helpercgroupvivo/MainPID0/job
pendente; pidfdQEMU/cmdline/disco conferidos; SIGKILL apenasQEMU, returncode-9.
Cada caso overlayFRESCO, relançado mesmoqcow2 e boot UUIDREAL diferente.

Resultadoscanônico pós-boot: partial-write intent/temp ausente; temp-fsynced
intent/temp837bytes completo ignorado; renamed INTENT (voltou de accepted!
antesdirfsync), temp837bytes ignorado; directory-fsynced ACCEPTED/temp ausente.
Renamed permite intentOUaccepted inteiro; dirfsync exigeaccepted.
Dois consumidores porcaso RecoveryRequired ANTESautorização, sempidfdherdado/
IPC/jobreuso/reenvio. Effectsbytes idênticos duranteconsultas; máscaras/provas/
ledgerhash/inode/owner/mode intactos. PAMproducersem máscara guardada/reposta
mesmoinode falha224; user@1002 falha224; peerproof e novaadmissão1000 PASS.
Restauração0 e quatroleitores+adicional porcaso PASS; SELinuxPermissiveoriginal.
Todas quatroVMsOFF, poweroffRPC0/QEMUfinal0. Caminhos:
/tmp/lyra-parental-pam-atomic-20261005/{partial-write,temp-fsynced,renamed,directory-fsynced}/system.qcow2
backing /tmp/lyra-parental-identity-20260928/system.raw intacto. Driverhost
analysis/2026-10-05/parental-pam-atomic-cut/run.py; exec4459 EXIT0.
Não rollbackintegral FS, não faltaenergia física (host/cachevivos).

Próximo: aplicar fronteiras reais nas gravações ORIGIN e INTENT ANTESStopUnit,
verificar0IPC e falta de origem/efeito nunca permiteadotarprocessos ou liberaradmissão.
Não repetir accepted/cortes/reboot/timeout jáqualificados. Owner/retirada,
outros errosI/O/antirollback/daemonreal/PAMgeral/D-state/coberturaglobal/root
compartilhado/notify-reload/caps/threads/subgrupos/NSS/GDM/PolkitUI/privacidade/
ISO pendentes. Controle parental integral NO-GO; #6/#102 abertos. Seminstalar/
promover na estação; OBSsomenteLeap16.1. Preservarroot kiwi/config.xml/drafts
usuário; planosroot append-only. Semsubagentes;fixtureisoladaautorizada.
Anteriores: 5bd67e1 corteaccepted durável (744/23VM, falhainstalldurabilidade
arquivada e corrigidafrontierasetup); ff9fb8b rebootreal; 087dd64 timeoutnativo;
3a6a57c quatrocrashes/e6770f5 coldconsumer. NÃO repetir.


## Controle parental — origem e intenção interrompidas em 05/10/2026

Worktree: desktop-parental-registry-lifetime. Branch: test/parental-registry-lifetime.
HEAD: 2305303c92daa805d23701b690b560dd463bdb9c. Commit local, sem push ou PR. Módulos de produção intactos.
Evidência: docs/evidence/parental-pam-early-cut/. Verificador PASS.
744 testes; oito casos com 13 controles antes e nove depois = 176 controles VM.
32 leitores de restauração e oito adicionais PASS. Todas as oito VMs OFF.

Cobertura: primeira publicação de ORIGIN e INTENT antes de StopUnit. Cada uma
foi cortada em partial-write, temp-fsynced, renamed e directory-fsynced.
Usou o RegistryStore._atomic existente (hash fc16655cdd5a2f633bd11566a48c8002617a793061c9175c6be0e282c9b317f3),
com syscalls reais instrumentados somente no worker da fixture. Instalação
sincronizada antes da retirada; checkpoint persistido antes do worker. Depois
da pausa, apenas notificação tmpfs, SIGSTOP e leituras; nenhum checkpoint ou
fsync de disco extra. SIGKILL por pidfd no QEMU/disco previamente conferidos.
Retorno do corte -9. Mesmo overlay relançado, UUID real novo.

Em ORIGIN, MainPID e auxiliar ainda vivos, sem autorização de recuperação nem
job. Em INTENT, origem já persistida, SIGTERM pelo pidfd do MainPID verificado,
auxiliar mantido vivo e autorização prévia do worker; publicação intent pausa
ANTES do envio de StopUnit. Contadores de entrada/retorno de StopUnit ZERO em
todos os oito pontos. Job vazio ou 0 antes do envio (não exigir job pendente).

Após boot novo: canônico ausente nos três primeiros pontos; inteiro após fsync
do diretório, para ambos os registros. Rename permite ausência OU documento
inteiro, não garante publicação. Temporários completos ignorados. ORIGIN nunca
criou efeito; INTENT preservou origem e, quando publicado, intent/revision 1/job
null. Dois consumidores por caso recusaram RecoveryRequired antes de autorização;
sem pidfds herdados, adoção de PID/job ou StopUnit. Bytes effects não alterados
nas consultas. Máscaras/provas/ledger com hashes/inodes/permissões/owners iguais.
Fontes PAM/unidades conferidas antes dos testes. Produtor sem máscara guardada/
recolocada no mesmo inode e user@1002 falharam 224/PAM; peer1000 admitido.
Limpezas 0, quatro leitores + adicional por caso PASS; SELinux Permissive original.
Poweroff RPC e QEMU final 0. Discos:
/tmp/lyra-parental-pam-early-20261005/{origin,intent}-{partial-write,temp-fsynced,renamed,directory-fsynced}/system.qcow2
Backing /tmp/lyra-parental-identity-20260928/system.raw intacto.

Falha inicial do verificador preservada em failed-intent-job-guard/: esperava
job pendente antes de StopUnit, mas Job era vazio. Driver saiu com erro e encerrou
sua VM; o retorno do primeiro corte não foi arquivado, então esse ensaio NÃO
qualifica o corte. Depois do relançamento, nove controles pós-boot, limpeza 0
e quatro leitores PASS; poweroff e QEMU final 0. Corrigido o guard para Job vazio/
0 e repetido intent-partial-write em overlay NOVO. Origem já concluída não foi
repetida. Overlay antigo restaurado e OFF, renomeado failed-intent-job-guard.
Driver analysis/2026-10-05/parental-pam-early-cut/run.py: execução inicial 64465
EXIT1; final 7766 EXIT0. Suíte 744 executada uma vez; não repetir sem motivo.

Próximo gate: interrupções na escrita do owner e retirada de admissão. Conferir
os ensaios históricos de parental-registry-barrier para reutilizar as provas
já concluídas e distinguir os cortes reais de VM dos os._exit de processo.
Accepted (5d6de08), origem e intenção já cobertos; não repetir. Erros I/O,
antirollback, daemon real, PAM geral/D-state, cobertura global/root compartilhado,
notify/reload/caps/threads/subgrupos, NSS/GDM/Polkit UI, privacidade e ISO continuam
pendentes. Host/cache vivos durante SIGKILL: NÃO equivale a energia física perdida.
Controle parental integral NO-GO; #6/#102 abertos. Nenhuma instalação ou promoção
na estação. OBS somente Leap16.1. Preservar root kiwi/config.xml e drafts do usuário;
planos root append-only. Sem subagentes; fixture isolada autorizada.
Histórico: 5d6de08 accepted (744/88 VM), 5bd67e1 corte durável, ff9fb8b reboot,
087dd64 timeout nativo, 3a6a57c quatro crashes/e6770f5 consumidor novo.


## Controle parental — cortes do owner e retirada em 05/10/2026

Worktree desktop-parental-registry-lifetime; branch test/parental-registry-lifetime.
HEAD b7c394db75d917edf08cbc40d30762aa4ef1e63d. Limpo, commit local sem push/PR. Nenhum módulo de produção alterado.
Evidência docs/evidence/parental-owner-cut/, verificador PASS. Suíte 744; dez casos
com 6 controles antes e 8 depois = 140 controles VM. 40 leitores de restauração
mais dez adicionais PASS. Todas as dez VMs OFF; limpeza, poweroff RPC e QEMU
final 0. Execução do driver 43029 EXIT0. Sem tentativas falhas nesta etapa.

Revisadas provas históricas: parental-registry-barrier (os._exit em 22 pontos),
parental-operation-journal (oito fronteiras duráveis de processo),
parental-withdrawal-boot (dois reboots ordenados após marcador fsynced). Não
repetidas. Nova cobertura: primeira publicação .deny-1002 (intenção completa),
primeira publicação .operation-1002.json (owner separado), cada uma em
partial-write/temp-fsynced/renamed/directory-fsynced; e unlink da prova 1002
antes/depois do fsync do diretório. Dez overlays novos independentes.

Operations.begin e RegistryStore._atomic existentes, hashes conferidos.
Autorização inicial explícita por callback confiável da fixture, não Polkit.
Syscalls reais interceptados somente no worker; pausa SIGSTOP e notificação
tmpfs. Instalação sincronizada e checkpoint persistido ANTES do worker, sem
checkpoint/auditoria/fsync extra após pausa. MainPID/auxiliar do produtor ainda
vivos e job ausente; owner NÃO revoga produtores nem faz mutações Unix.
Host confirma root, ambos os marcadores, serial, boot, worker T, processo QEMU
e disco por cmdline/pidfd. SIGKILL só QEMU, retorno -9. Mesmo overlay relançado;
novo UUID real e fontes PAM/unidades intactas conferidos antes dos testes.

Resultado: primeiro marcador ausente nos três primeiros pontos (inclusive
rename sem fsync), inteiro no quarto. Sem marcador durável, retirada NÃO
confirmada: prova positiva original conserva admissão, resume recusa
RecoveryRequired sem autorização. Após marcador fsynced, PAM nega com 224 e
causa exata, mesmo com owner ausente/incompleto e prova positiva presente.
Owner separado ausente nos três primeiros pontos, inteiro no quarto; marcador
intenção permanece durável. Antes de remover prova, marcador/journal legado
blocked e owner legacy-blocked/revision2 já persistiram. Unlink sem fsync:
prova voltou após boot; marcador conservou negação. Unlink com fsync: prova
permaneceu ausente e conta negada. Nenhuma promoção de temporário.

Inspeção somente leitura; outra operação recusa antes de autorização; retomada
com autorização NEGADA conserva todos os arquivos. Conta vizinha conserva
prova e nova admissão; tentativas PAM não modificam estado nem recriam prova.
Retomada AUTORIZADA após estes cortes ainda não foi qualificada neste ensaio.
Discos /tmp/lyra-parental-owner-20261005/{marker,owner}-{partial-write,temp-fsynced,renamed,directory-fsynced}/system.qcow2
e /tmp/lyra-parental-owner-20261005/proof-{unlinked,directory-synced}/system.qcow2.
Backing /tmp/lyra-parental-identity-20260928/system.raw intacto. Não é rollback
integral FS ou perda física de energia: host/cache ficaram vivos.

Próximo: qualificar recuperação explicitamente AUTORIZADA após corte, mantendo
negação e sem afirmar quiescência. Reutilizar scripts/cenários; novos cortes
apenas para acrescentar essa validação, não repetir os mesmos controles sem
necessidade. Publicações posteriores do owner/journal, fsync com erro/erros I/O,
antirollback, daemon real, PAM geral/D-state, cobertura global/root compartilhado,
notify/reload/caps/threads/subgrupos, NSS/GDM/Polkit UI, privacidade e ISO pendentes.
Controle parental integral NO-GO, #6/#102 abertos. Nenhuma instalação/promoção
na estação; OBS somente Leap16.1. Preservar root kiwi/config.xml e drafts usuário;
planos root append-only. Sem subagentes; fixture isolada autorizada.
Histórico: 2305303 origem/intent antes StopUnit (744/176 VM), 5d6de08 accepted
(744/88 VM), 5bd67e1 corte durável, ff9fb8b reboot, 087dd64 timeout nativo;
3a6a57c crashes e e6770f5 consumidor novo. Não repetir provas concluídas.


## Controle parental — recuperação autorizada após corte em 05/10/2026

Worktree desktop-parental-registry-lifetime; branch test/parental-registry-lifetime.
HEAD a7f0cac582cd9f2f7a2054bfd826b4a7ed7d23b6. Limpo, commit local sem push/PR. Nenhum modelo/módulo de produção
alterado. Evidência docs/evidence/parental-owner-recovery/, verificador PASS.
744 testes; dez casos com 6 controles antes e 12 depois = 180 controles VM.
40 leitores de restauração e dez adicionais PASS. Todas as dez VMs OFF,
limpeza, poweroff RPC e QEMU final 0. Driver35493 EXIT0, sem tentativas falhas.

Esta etapa acrescentou autorização positiva e retry às consultas/negações já
qualificadas em b7c394d. Novos overlays/cortes necessários porque os anteriores
já tinham sido restaurados; não houve repetição para simplesmente elevar contagem.
Mesmo Operations/Withdrawal/_atomic, hashes conferidos. Dez pontos reproduzidos:
primeiro marcador e primeiro owner em partial-write/temp-fsynced/renamed/
directory-fsynced; prova em unlink antes/depois de fsync do diretório.
Instalação/checkpoint duráveis antes do worker; notificação em tmpfs e SIGSTOP
no syscall real, sem sync extra depois. QEMU/disco confirmados por cmdline/pidfd,
SIGKILL retorno -9, mesmo overlay relançado com UUID real diferente.

Sete estados com marcador durável: nova instância de coordenador, autorização
NOVA fora dos locks reais (probes EX no inventário, withdrawal e ledger),
identidade/operação/proof hash/snapshot/inventário iguais ao owner planejado.
Resume concluiu AdmissionWithdrawnNoQuiescence, owner retired/revision3,
journal legado retired/revision2, marcador blocked/revision1, prova positiva
1002 ausente. Nova instância repetiu mesma operação, exigiu autorização de
novo e não regravou nenhum arquivo: hash/inode/owner/mode/tamanho idênticos.
user@1002 continuou negado 224/PAM com causa exata; peer1000 conservou PID e
prova. Temporários anteriores ficaram idênticos e não foram adotados.

Três estados sem primeiro marcador persistido: resume e retry retornaram
RecoveryRequired ANTES do callback que aprovaria; nenhuma autorização ou escrita.
Prova ordinária e manager já admitido ficaram intactos. Não confirmou retirada
inexistente ou reconstruiu operação a partir de temporário. Autorização é
callback confiável da fixture, NÃO Polkit/transport de produto.

Discos /tmp/lyra-parental-owner-recovery-20261005/{marker,owner}-{partial-write,temp-fsynced,renamed,directory-fsynced}/system.qcow2
e /tmp/lyra-parental-owner-recovery-20261005/proof-{unlinked,directory-synced}/system.qcow2.
Backing /tmp/lyra-parental-identity-20260928/system.raw intacto. Não rollback
integral FS ou energia física perdida; host/cache permaneceram vivos.

Próximo: CONSOLIDAR as provas e revisar gates restantes para integração/ADR #5,
sem criar automaticamente uma nova sequência de testes igual às já concluídas.
Consultar a parte inicial de lyraos-desktop/docs/parental-controls-completion-plan.md:
requisitos/arquitetura ainda aguardam aprovação; #2 serviço, #5 ADR, #6 admissão,
#7 Vega, #8 UX, #9 release, #10 matriz e #102 enforcement continuam pendentes.
Não instalar, promover ou criar daemon/Unix mutation de produto sem cumprir
esse gate. Preparar resultado concreto para revisão, não pedir aprovação vaga.

Lacunas específicas continuam registradas: interrupções DURANTE recuperação,
publicações posteriores do owner/journal, fsync com erro/erros I/O, antirollback,
revogação/global/root compartilhado, PAM geral/D-state, notify/reload/caps/threads/
subgrupos, NSS, GNOME/GDM completo, Polkit/UI, privacidade e ISO. Recuperação
qualificada aqui é retirada de ADMISSÃO; não alegar quiescência ou enrollment.
Controle parental integral NO-GO; #6/#102 abertos. Nenhuma instalação/promoção
na estação. OBS somente Leap16.1. Preservar root kiwi/config.xml e drafts do usuário;
planos root append-only. Sem subagentes; fixture isolada autorizada.
Histórico: b7c394d owner/retirada (744/140 VM), 2305303 origem/intent (744/176 VM),
5d6de08 accepted (744/88 VM), 5bd67e1 corte durável, ff9fb8b reboot, 087dd64
timeout nativo, 3a6a57c crashes/e6770f5 consumidor. Não repetir provas concluídas.

## Consolidação para integração — 05/10/2026

Provas de admissão e recuperação consolidadas no documento
[revisão de integração](../../worktrees/desktop-parental-registry-lifetime/docs/parental-admission-integration-review.md),
commit local e1185c1. Próximo gate: contrato #2/#5, classificação persistente,
lifecycle e autorização real do serviço. Não houve nova rodada de VM, instalação
ou publicação. Revisão local não equivale a autoridade monotônica global; retirada
de admissão não prova quiescência. #6/#102 e aprovação final da ADR permanecem
pendentes; parental de produto segue NO-GO. Status de retomada em
analysis/2026-10-05/parental-integration-review/CURRENT.md.

## Contrato de integração — 05/10/2026

Especificação revisável no
[contrato do serviço](../../worktrees/desktop-parental-registry-lifetime/docs/parental-service-integration-contract.md),
commit local b01d0d1. Detalha módulo integrado ao vegad, lifecycle, classificação
positiva ordinary, negação por ausência, API, Polkit e guard administrativo.
Rollback/referência independente e recuperação do catálogo global seguem gates
abertos. Próximo componente isolado: parser/classificador e planejamento tipado.
Nenhum pacote/instalação/VM novo; produto NO-GO e ADR final pendente. Retomada em
analysis/2026-10-05/parental-service-contract/CURRENT.md.

## Classificador e planejamento isolados — 05/10/2026

Implementados no [laboratório do serviço](../../worktrees/desktop-parental-registry-lifetime/docs/evidence/parental-service-classifier/README.md),
commit local 573d9b7. 22 testes específicos/766 suíte completa PASS. Leitura
restrita, classificação positiva ordinary, estados negativos e planos vinculados
a remetente/revisão/catálogo; testes com owner explícito do laboratório, não root.
Sem execução de retirada, Polkit/D-Bus real ou pacote. Próximo: ligar o plano à
retirada negativa existente, autorização nova fora dos locks e revalidação no
primeiro efeito. Gates e produto NO-GO permanecem. Status detalhado em
analysis/2026-10-05/parental-service-classifier/CURRENT.md.

## Ligação experimental à retirada de admissão — 05/10/2026

Implementada a [ligação de planejamento e operação](../../worktrees/desktop-parental-registry-lifetime/docs/evidence/parental-service-withdrawal/README.md),
commit local df88e67. 14 novos testes/780 suíte completa PASS. Modelo existente
preservado; catálogo/geração selados no inventário persistido pelo journal,
autorização nova fora dos locks e nova instância/retry sem reconstruir plano.
Catálogo/flock reais; inventário/ledger simulados em memória. Próximo: verificar
a composição com armazenamento/locks reais no laboratório, depois transporte/
Polkit e guards. Nenhuma instalação, VM ou publicação nova; produto NO-GO.
Status em analysis/2026-10-05/parental-service-withdrawal/CURRENT.md.

## Composição com armazenamento real — 05/10/2026

Qualificada no [ensaio de armazenamento](../../worktrees/desktop-parental-registry-lifetime/docs/evidence/parental-service-storage/README.md),
commit local af6a7a4. Onze testes root em VM passaram: locks reais, auth fora
dos três locks, intent durável seguido de saída de processo, retomada por novo
processo e retry sem regravar; conta comum/catalog/inventory preservados.
Contas/PAM/SELinux e backing inalterados, fixture removida e VM OFF. Prova é JSON
sintético, sem PAM/login real; Polkit/remetente ainda callbacks. Próximo: testar
transporte/autorização reais numa fixture isolada. Produto NO-GO e gates abertos.
Retomada em analysis/2026-10-05/parental-service-storage/CURRENT.md.

## Transporte e decisão Polkit reais — 05/10/2026

O [ensaio D-Bus/Polkit](../../worktrees/desktop-parental-registry-lifetime/docs/evidence/parental-service-auth/README.md)
passou em oito cenários e retry com servidor/cliente novos, commit 9ec7e1d.
Remetente real, negação, agente retornando Cancelled, capacidade/revisão alteradas
após decisão e replay de outra conexão recusados. Regra positiva restrita da
fixture, sem autenticação por senha ou vínculo persistente de responsável.
Políticas/config temporárias removidas, estado existente/backing preservados e
VM OFF. Próximo: guard isolado das mutações administrativas contra conta
protegida/bloqueada/desconhecida. Produto NO-GO; gates permanecem. Retomada em
analysis/2026-10-05/parental-service-auth/CURRENT.md.

## Guard administrativo e teste local autorizado — 05/10/2026

O [guard isolado](../../worktrees/desktop-parental-registry-lifetime/docs/evidence/parental-administrative-guard/README.md),
commit 1d2eb5b, passou em 13 testes/793 suíte. Update/SetAdmin ordinary conferidos
até callback, supervised/unknown/negative recusados, planos consumidos antes do
efeito. Create/Remove indisponíveis só na fixture; parâmetros e efeito Unix não
implementados. Próximo: selar parâmetros tipados e qualificar adaptador isolado.
O mantenedor autorizou/pediu instalar na estação quando o controle parental
estiver concluído; criará conta local nova de criança/adolescente para teste.
Isso faz parte da entrega, sem pedir a mesma autorização novamente. Concluir
integração, criação/migração/recuperação, pacote e preservação da conta principal
antes de instalar; fixtures atuais não são produto. Status em
analysis/2026-10-05/parental-administrative-guard/CURRENT.md.

## Parâmetros administrativos selados — 05/10/2026

O [envelope tipado](../../worktrees/desktop-parental-registry-lifetime/docs/evidence/parental-administrative-parameters/README.md),
commit 31a8f23, passou em 12 testes/805 suíte. Nome/grupos/GIDs/adminflag fixos
no plano, cópia da autorização não altera efeito, grupos revalidados antes do
adaptador e argv sem shell. Comandos não executados; senha/foto indisponíveis
só na fixture. Próximo: efeito Unix real na VM com restauração verificada.
Instalação local após conclusão continua autorizada para teste com conta nova
de criança/adolescente; preservar conta principal e qualificar integração/
recuperação antes. Produto NO-GO; status em
analysis/2026-10-05/parental-administrative-parameters/CURRENT.md.

## Adaptador com efeito Unix real — 05/10/2026

O [ensaio Unix selado](../../worktrees/desktop-parental-registry-lifetime/docs/evidence/parental-administrative-unix/README.md),
commit 2001ba6, passou em 13 controles, três comandos reais e dois no-ops.
Perfil/grupos/wheel aplicados só na conta fictícia da VM; identidade e peer
preservados, negação/barreira impediram comando. Arquivos de contas/backups
restaurados por hash, fixtures removidas, backing intacto e VM OFF. Auth ainda
callback: próximo é composição com transporte/Polkit reais. Restauração integral
é procedimento do laboratório, não recuperação de produto. Instalação local
após conclusão continua autorizada para conta nova de criança/adolescente.
Produto NO-GO; status analysis/2026-10-05/parental-administrative-unix/CURRENT.md.


## Composição administrativa real no laboratório — 05/10/2026

15 cenários passaram com D-Bus/Polkit e comandos Unix no mesmo fluxo: 11
decisões, quatro comandos e dois no-ops. Negação/cancelamento e mudança de
capacidade/revisão/barreira impediram efeito; parâmetros selados e identidade/
conta vizinha preservados. Restauração, cleanup e VM OFF confirmados.
Evidência no worktree desktop-parental-registry-lifetime, commit 09ce7aa;
docs/evidence/parental-administrative-auth/README.md e verify-evidence.py PASS.
Positivo por regra fictícia, sem senha/guardião/GNOME/MAC; sem produto instalado.
Próximo: implementar classificação/catálogo no Go existente com bootstrap/
recuperação antes de habilitar mutações. Gates #2/#5 e #6/#102 continuam abertos.
Instalação local após concluir controle parental já autorizada pelo mantenedor,
que criará conta nova de criança/adolescente.


## Catálogo e classificação em Go — 05/10/2026

Implementado módulo interno readonly no vegad, worktree vegad-parental-catalog,
commit88a5d58. JSON fechado/limitado e sem duplicatas, ownership/links/locks
conferidos, classificação positiva/identidade exata e cobertura supervisionada
observada. Paridade dos digests com modelo Python em três vetores passou; testes
do módulo/race, vet/regressão do repo e compatibilidade Go1.22 passaram. Ainda
sem ativação UsersService/D-Bus/PAM ou writer/bootstrap/recovery/planner; não
qualifica proteção de produto. Próximo: planos vinculados a remetente/capacidade/
revisão antes de conectar mutações. Instalação local após concluir controle
parental permanece autorizada para teste em conta nova criança/adolescente.


## Planos vinculados ao serviço em Go — 05/10/2026

Vegad commit48012a2, worktree vegad-parental-catalog: plano privado vinculado
a remetente/UID/capacidade, associação/geração/revisão/digest/identidade.
Limite128, expiração60s monotônica, revalidação após observações, restart sem
recuperar autoridade. Testes/race/regressão/vet/Go1.22 passaram. Nenhum efeito
Unix, Polkit ou ativação de produto; Validate ainda não consome ou segura lease.
Próximo: guard de execução com autorização nova fora dos locks, revalidação sob
leases e consumo antes do efeito. Bootstrap/recuperação e gates permanecem
abertos. Instalação local após conclusão segue autorizada para conta nova
criança/adolescente; preservar a conta principal.


## Guard administrativo em Go — 05/10/2026

Vegad commitd854629, worktree vegad-parental-catalog: método/parâmetros selados,
checks de estado negativo e identidade/capacidade/revisão, autorização fora das
leases, consumo antes do efeito e reserva por associação contra duplicação.
Falha parcial/identidade alterada não reexecutam mesmo plano. Testes/race/vet/
regressão/Go1.22 passaram. Backend de leases e efeitos ainda são fixtures; sem
Unix/Polkit reais nesta etapa e sem ativação UsersService. Próximo: backend de
locks/arquivos root em Go, codecs/provas e overlay negativo, depois adaptador
Unix e transporte/autorização reais. Bootstrap/recuperação/gates permanecem
abertos. Instalação local após concluir controles continua autorizada para nova
conta criança/adolescente, preservando a conta principal.


## Backend filesystem em Go — 05/10/2026

Vegad commitc8f72c8, worktree vegad-parental-catalog: leases reais catalogSH,
inventorySH, operationSH/EX mantidas no efeito; rootownership/perms/links/inodes
validados, inventário fechado e overlay negativo antes da prova. Reader reusa
helpers. Testes reais de flocks/release/falhas/arquivos vizinhos/race/regressão/
vet/Go1.22 passaram. Proofcodec dos testes ainda sintético, sem VMroot positiva
ou Unix real neste Go; UsersService continua sem ativação. Próximo: adaptador
Unix fixo + qualificação Go em VM, depois D-Bus/Polkit reais; bootstrap/recuperação
e gates seguem abertos. Instalação local após conclusão permanece autorizada
para teste com conta nova criança/adolescente, preservando conta principal.


## Adaptador Unix e VM Go — 05/10/2026

Vegad commit4403c9c, worktree vegad-parental-catalog: UpdateUser/SetAdmin
com argv fixos, identidade/GIDs antes/depois, timeout e no-op idempotente.
Ensaio positivo com guard+leases root reais: sete checks, três comandos Unix,
duas repetições sem comando, identidade e vizinha preservadas. Negação/barreira
impediram efeito; restauração/backing intacto e VM OFF. Primeiro setup falhou
antes de comandos, preservado separadamente; retry corrigiu apenas a fixture.
Testes/race/vet/regressão/Go1.22/verifier passaram. Prova e autorização continuam
sintéticas; sem ativação/instalação no host. Próximo: D-Bus/Polkit reais em Go,
depois bootstrap/writer/recovery/prova/lifecycle/enforcement e demais gates.
Instalação local após conclusão já autorizada para nova conta criança/adolescente,
preservando conta principal. Detalhes analysis/2026-10-05/vegad-parental-unix/CURRENT.md.


## Composição D-Bus e Polkit em Go — 05/10/2026

Vegad commit936ced2, worktree vegad-parental-catalog: resolução real do UID
do sender, ações Polkit do servidor e execução pelo ID do plano selado.
VM passou13cenários/10consultasPolkit/3comandosUnix/2no-ops; negação/cancelamento/
replay/revogação/mudança de catálogo/barreira impediram efeito. Identidade e
vizinha preservadas, contas/config restauradas, backing intacto, VM OFF.
Testes/race/vet/regressão/Go1.22/verifiers passaram. Prova/capacidade ainda
sintéticas, sem guardian persistido/PAM autoritativo/produção/hostinstall.
Próximo: bootstrap/writer/recovery ordinary em Go preservando contas comuns,
depois provas/lifecycle/guardian/enforcement e demais gates. Instalação local
após conclusão já autorizada para conta NOVA criança/adolescente. Detalhes
analysis/2026-10-05/vegad-parental-bus/CURRENT.md.


## Writer negativo do catálogo em Go — 05/10/2026

Vegad commit95a8d43: BlockOrdinary publica recovering/barrier de associação
conhecida, com CAS, EX no lock existente, temp exclusivo/fsync/rename/fsyncdir.
Preserva outras contas/políticas/tombstones. Falha após rename retorna
PublicationUncertain sem rollback permissivo; retry do snapshot antigo conflita.
Testes/race/vet/regressão/Go1.22 e três cortes reais de processo passaram.
Qualificação rootVM deste writer ainda pendente. Não há bootstrap automático,
recuperação positiva, ativação ou instalação local. Próximo: rootVM e disputa de
dois processos, depois fonte confiável para bootstrap/recuperação. Demais gates
continuam abertos. Instalação após concluir parental já autorizada para nova
conta criança/adolescente, preservando a principal. Detalhes:
analysis/2026-10-05/vegad-parental-writer/CURRENT.md.


## Qualificação root do writer em Go — 05/10/2026

Vegad commit150d03e: nova VM passou quatro casos com factory root sem override.
Dois escritores reais disputaram o mesmo snapshot: um commit, outro Busy, retry
antigo Conflict; Reader Busy durante EX. Três cortes de processo preservaram os
estados esperados e registros ordinary/supervised/tombstone vizinhos. Contas, PAM
e políticas intactos, fixtures removidas, backing intacto, VM OFF. Testes/race/
vet/regressão/Go1.22/verifier passaram. Não há bootstrap, recuperação positiva ou
ativação. Próximo: fonte confiável e protocolo explícito de bootstrap/recuperação,
sem inferir ordinary de UID/ausência ou backup antigo. Instalação após concluir
parental já autorizada para nova conta criança/adolescente, preservando principal.
Detalhes analysis/2026-10-05/vegad-parental-writer-vm/CURRENT.md.


## Inspeção de referência de bootstrap/recuperação — 06/10/2026

Vegad commita5b7c65: referência estrita diferencia first-install e blocked-recovery;
inspeção read-only com capacidade explícita antes de lookup, tupla conferida e
referência/caller reconferidos. Recuperação exige bloqueio e preserva identidade,
geração, política, tombstones e operações pendentes; não cria novo tombstone.
Testes/race/vet/regressão/Go1.22 passaram. Não publica, não libera contas nem
autentica emissor só pelo JSON. ReferenceSource ainda é contrato sem adapter
produtivo; origem/freshness/armazenamento reais e publisher autorizado pendentes.
Instalação após concluir parental permanece autorizada para nova conta de teste,
preservando principal. Status analysis/2026-10-06/vegad-parental-reference/CURRENT.md.


## Fonte filesystem da referência — 06/10/2026

Vegad commit6815931: leitor root-only de current.json/reference.json soblease SH,
issuer/install/seq/digest conferidos e witness de domínio exigido antes/depois.
Files/flocks reais/testes/race/vet/regressão/Go1.22 passaram. Sem witness recusa,
não cria/adota dados. Qualifier/issuer/authorityprovisioning ainda pendentes.
Observação host: /var/lib permanece no subvolume raiz /@; não pode ser tratado
como fora do rootrollback só pelo caminho. Nenhuma alteraçãohost/kiwi/OBS.
Próximo: observerBtrfs/Snapper comescopodeclarado e snapshotrollbackVM real; depois
authorityissuance/journal e publisherautorizado. Status
analysis/2026-10-06/vegad-parental-reference-files/CURRENT.md.


### 06/10/2026 — domínio de rollback Btrfs qualificado em VM

Commit local vegad `3e59e65`, worktree vegad-parental-catalog: callback real
BtrfsSnapshotDomain para FileReferenceSource, conservador para restauração de um
subvolume configurado, raiz montada e referência em outra raiz de subvolume montada.
Consultas limitadas via btrfs-progs, descritores abertos, UUID/árvores/namespace e
recusa de layouts não qualificados. Não configura Snapper nem provisiona autoridade.

Ensaio real em segundo disco Btrfs descartável: catálogo restaurado de snapshot
antigo, referência/pin atuais preservados, diagnóstico BlockedRestoreRequired.
Recusas same-tree/nested-catalog/readonly/stale-reference/missing-pin passaram.
Testes/race/vet/regressão/Go1.22 e verifier dos recibos passaram. Preparação e
recusas anteriores preservadas; somente guest recebeu btrfs-progs oficial assinado,
antes do baseline. Contas/PAM/DBus/Polkit/SELinux sem mudanças durante ensaio, backing
raw intacto, disco desmontado e todas as VMs desligadas. MAC Permissive de laboratório
não qualifica produção. Nenhuma alteração de mounts/fstab/subvolumes/pacotes do host.

Próximo gate: procedimento efetivo Snapper e receita de armazenamento para Leap16.1/ISO,
seguido de provisionamento/emissão transacional da autoridade completa e recuperação
bloqueada autorizada. Não cobre rollback conjunto do filesystem/VM, nem instala ou
conclui parental. /var/lib da estação continua no subvolume raiz e não serve como
autoridade independente sem mudança de layout qualificada. Status detalhado:
analysis/2026-10-06/vegad-parental-btrfs-domain/CURRENT.md; evidências:
worktrees/vegad-parental-catalog/docs/evidence/parental-btrfs-domain/.


### 06/10/2026 — referência vinculada à configuração Snapper

Commit local vegad `4bc34c8`, worktree vegad-parental-catalog. SnapperSnapshotDomain
combina leitura root segura e limitada da configuração com BtrfsSnapshotDomain real.
Exige scope/Btrfs/ACL root explícitos; recusa configuração insegura/ambígua/delegada
ou alterada durante a leitura. Witness contém conteúdo/configuração e topologia.

VM Leap16.1 com Snapper0.12.1: snapshot criado pelo CLI real, conteúdo do catálogo
conferido, restauração offline de um subvolume preservou referência/pin atuais e
exigiu recuperação bloqueada. Configuração delegada recusou; mudança de comentário
alterou witness. Testes/race/vet/regressão/Go1.22/verifiers novo e anterior passaram.
VM OFF/QEMUexit0, backing qcow2 e raw intactos, contas/PAM/DBus/Polkit/Snapper iguais
durante ensaio, configuração fixture removida e disco desmontado. Dependências/rede
de laboratório foram preparadas somente no guest antes do baseline. Host intacto.

Não executou snapper rollback/default-subvolume/reboot/GRUB/ISO, nem certificou mounts
persistentes de authority/.snapshots após rollback. Esse gate continua aberto para
a distribuição. Próximo núcleo: provisionamento/emissão transacional da referência
com manutenção autorizada, owners/tombstones e journal, depois recuperação bloqueada
publicada. Nenhuma ativação/instalação de parental. Status detalhado:
analysis/2026-10-06/vegad-parental-snapper-domain/CURRENT.md; evidências:
worktrees/vegad-parental-catalog/docs/evidence/parental-snapper-domain/.


### 06/10/2026 — atualização transacional de referência existente

Commit local vegad `2ff125b`, worktree vegad-parental-catalog. ReferenceWriter
Advance/Resume com EX no lock existente, journal completo before/after/issuer/op,
publicação staged/fsync/rename/dirsync e retomada autorizada exata. FileReferenceSource
recusa qualquer journal pending; nunca limpa/reconstrói. CAS/seq+1, owners/gens/
policy/tombstones/pendingops preservados; nenhuma escrita do catálogo/admissão.

Testes/race/vet/regressão/Go1.22/verifier passaram. Nova VM root/Btrfs real: três
processos terminados com exit73 após journal/ref/pin duráveis; leitores recusaram,
wrong-op/nil recusaram e resume exato concluiu. Lockinode/catalog/stateaccount-policy
intactos, mounts desmontados, VM OFF/QEMUexit0 e três backingfiles preservados.
Falha inicial do harness (campo legado de Snapper), apesar do teste Go passar, foi
preservada; repetição em discos novos aprovada. Não é ensaio de perda física de
energia. Callbacks de maintenance e issuer completo ainda são fixtures, sem Polkit
ou guardian produtivos. Host intacto; nada de parental instalado/ativado.

Próximo: PRIMEIRA emissão/provisionamento com prova de instalação nova e selo
durável para impedir reinitialização após perda de pin/ref/lock. Diretório vazio
não prova instalação nova. Store existente só é atualizado; bootstrap segue aberto.
Depois issuer/maintenance reais e publicação de recuperação bloqueada. Gates
boot/Snapper/default-subvol/GRUB/mounts persistentes/ISO/MAC continuam pendentes.
Status: analysis/2026-10-06/vegad-parental-reference-writer/CURRENT.md; evidências:
worktrees/vegad-parental-catalog/docs/evidence/parental-reference-writer/.
Manifests anteriores continuam históricos nos seus commits qualificados; não
afirmam os hashes do checkout atual após mudança intencional do leitor pending.


### 06/10/2026 — biblioteca de primeira emissão parental

Implementada em vegad, commit c1ecec8: ReferenceProvisioner.Initialize/ResumeInitial,
selo e confirmação permanentes, prova obrigatória de instalação nova por callback
trusted, manutenção fresh, publicação durable e retomada somente da mesma operação.
O leitor bloqueia estados parciais e não recria autoridade perdida. Testes passaram:
4 processos interrompidos sem defers, 8 falhas fsync, perdas/arquivos unsafe, suíte
completa, race/vet e Go1.22. Prova/domínio ainda fixtures; adapter do instalador e
qualificação deste provisioner em VM Btrfs real PENDENTES. Não equivale a produto
concluído ou pronto para instalação. Next: VM/root factory + domínio real, depois
integração da autoridade e catálogo. Status: analysis/2026-10-06/vegad-parental-reference-provisioning/CURRENT.md.
Nenhuma alteração da máquina local/publicação OBS neste passo.


### 06/10/2026 — primeira emissão qualificada em VM Btrfs

Commit d33ce83 (vegad): novo teste com factories root padrão, domínio Btrfs real e
4 interrupções de processos em VM descartável. Emissão pendente bloqueia leitura;
retomada requer operação exata e proof ainda válida. Após conclusão, perdas de
ref/pin/both/lock não reinicializam a autoridade. Advance preserva selo/commit/lock
e catálogo. VM OFF/QEMUexit0, políticas/contas e três backings intactos; verifier,
suíte, race/vet/Go1.22 passaram. Fonte de freshness/issuer/manutenção ainda fixtures,
sem integração real/instalação local/OBS. Próximo: prova do instalador e preparação
confiável da autoridade, depois bootstrap/recuperação do catálogo. Status em
analysis/2026-10-06/vegad-parental-reference-provisioning-vm/CURRENT.md.
