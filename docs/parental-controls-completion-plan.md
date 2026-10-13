# Plano para concluir os controles parentais

**Status:** planejamento; integração parental continua `NO-GO` para a Alpha 8.
**Atualizado:** 06/10/2026
**Épico:** [Desktop #11 — ECA Digital](https://github.com/lyra-os-linux/lyraos-desktop/issues/11)

**Decisões de produto em 07/10/2026:** ver
[registro consolidado](parental-controls-product-decisions.md). O mantenedor
optou por publicação experimental se os gates técnicos passarem, sem tornar um
novo parecer pago requisito automático da Alpha 8; revisão conjunta da matriz
#10 é objetivo antes da Beta 1. Uma falha de evasão adia apenas o recurso
parental. O status técnico `NO-GO` abaixo permanece vigente.

**Estado consolidado em 06/10:** vegad tem bibliotecas locais para referência,
primeiro enrollment, autorização Polkit e leitura de uma referência assinada;
os domínios Btrfs/Snapper foram exercitados em sondagens e VMs descartáveis.
Isso ainda não é fluxo de produto: `installedParentalLayoutReady()` permanece
fechado, faltam endpoint/chave/configuração oficiais, a composição não está
ligada ao D-Bus e a topologia produzida pelo instalador ainda não foi qualificada
em reboot/upgrade/reinstalação. A matriz #10 segue aguardando revisão profissional;
#102, enforcement e demais gates também seguem abertos. O build local de ensaio
é Alpha 7, não release Alpha 8. A VM de instalação foi fechada antes da seleção
do disco e não gravou o QCOW2; nada foi instalado na máquina do mantenedor nem
publicado no OBS.

## Estado de partida

- A auditoria da referência BigLinux foi concluída e rejeitou seu reuso como
  backend. O parecer jurídico foi obtido e aprovado pelo mantenedor; a matriz
  de responsabilidades e sua ligação com o gate ainda precisam ser concluídas
  em [#10](https://github.com/lyra-os-linux/lyraos-desktop/issues/10).
- GNOME `malcontent` é a opção upstream prioritária no Leap 16.1, mas ainda não
  está qualificada para o produto. A issue P1
  [#102](https://github.com/lyra-os-linux/lyraos-desktop/issues/102) reproduz
  execução de um Flatpak mesmo após a política negar o aplicativo.
- Testes recentes qualificaram partes de admissão de conta, sessão, login e
  caminhos de CLI. Eles não demonstram que a política parental está aplicada.
- A `origin/main` já contém evidência experimental até 28/09: componentes
  GNOME, portais e partes da sessão gráfica na VM descartável; login GDM com
  senha; admissão em systemd-user,
  GDM, login local e SSH; barreira de transições; acessibilidade e auxiliares.
  O domínio SELinux continua sendo uma fixture, não política de produto.
- A própria evidência registra lacunas: identidade de produção, ciclo autorizado
  de contas, revogação de conexões/processos antigos, entradas persistentes
  restantes, sessão completa sem builds de diagnóstico, atualização/rollback e
  integração Vega. Nada disso autoriza ativar a funcionalidade.
- Em 29/09, um diagnóstico na VM descartável confirmou que a associação PAM
  experimental admite uma conta recriada com a mesma tupla Unix. Foi um teste
  executado como root e não demonstra que a conta supervisionada possa recriar
  contas. A proposta da ADR #5 agora recomenda geração aleatória, tombstones e
  transação fail-closed. A prova PAM confirmou tombstones e negação de estados/
  registros inválidos em 12 cenários. Um helper separado de transação passou
  16 cenários de interrupção de processo e concorrência, mas não é serviço,
  nem testa perda de energia. Uma terceira prova ligou o lease do handle PAM
  ao lock exclusivo: sessão aberta retorna `Busy`, e novas sessões são negadas
  durante `transitioning`; GDM/TTY/SSH e processos persistentes ainda não foram
  qualificados. Os requisitos continuam sem aprovação nem implementação de
  produto. Veja a
  [reprodução original](../../worktrees/desktop-parental-identity/docs/evidence/parental-identity/reuse-result.json),
  a [prova de registro](../../worktrees/desktop-parental-identity/docs/evidence/parental-identity/registry-result.json),
  a [prova transacional](../../worktrees/desktop-parental-identity/docs/evidence/parental-identity/registry-transaction-result.json),
  a [prova de lock PAM](../../worktrees/desktop-parental-identity/docs/evidence/parental-identity/registry-pam-lock-result.json)
  e a [proposta revisada](parental-identity-lifecycle-proposal.md).
- Em 01/10, o mesmo registro por geração foi conectado ao PAM vendor de
  `systemd-user` em VM descartável: 30 checks nativos passaram. O keeper
  `(sd-pam)` retém o lease inclusive em lingering e após reexec; geração antiga,
  registro/módulo ausentes e permissive são recusados, preservando conta comum.
  O PAM agora usa lock não bloqueante, e a recusa com escritor exclusivo foi
  exercitada. As regressões PAM passaram 12+9 checks com esse fonte; o escritor
  manteve seu fonte e os 16 checks anteriores; 262 testes Python passaram.
  [Evidência nativa](../../worktrees/desktop-parental-registry-lifetime/docs/evidence/parental-identity/native-registry-manager-result.json)
  e [relatório](../../worktrees/desktop-parental-registry-lifetime/docs/evidence/parental-identity/README.md).
  Essa etapa não testa logout/boot com lingering nem revoga conexões antigas.
  O lock do registro ainda é global, e `Busy` preserva `active`, sem a barreira
  persistente contra novas admissões da fixture anterior. A extensão ao GDM
  com senha e autenticação pendente está registrada abaixo;
  ainda é necessário reconciliar essa barreira e fechar revogação e produtores
  persistentes antes de um ciclo autorizado de contas ou serviço de produto.
- O ensaio GDM por geração também foi concluído em 01/10: 22 checks nativos e
  270 testes Python passaram. Worker e sd-pam mantêm lease; geração antiga e
  senha correta enviada após `transitioning` numa conversa já pendente são
  recusadas. Conta comum e restauração preservadas. O ensaio continua com
  worker diagnóstico e sessão ELF mínima; não qualifica GNOME completo,
  enrollment sem guard ou revogação. Houve perdas de audit por backlog, então
  não se declara inventário AVC completo. Veja o
  [relatório GDM](../../worktrees/desktop-parental-registry-lifetime/docs/evidence/parental-registry-gdm/README.md).
  Próximo: reconciliar barreira persistente e isolamento por conta; depois
  revogação e produtores persistentes. O estado parental continua NO-GO.
- A ADR de dados e arquitetura (#5), o serviço de políticas (#2), UX (#8),
  integração Vega (#7) e gate de release (#9) seguem abertos.
- Para alimentar a revisão de #5, há uma
  [proposta de ciclo de vida da identidade](parental-identity-lifecycle-proposal.md).
  Ela separa criação, migração, recuperação e exclusão, e deixa retirada da
  supervisão bloqueada até decisão de produto/jurídica.

## Princípios de conclusão

1. Uma conta apresentada como supervisionada precisa mostrar quais controles
   estão ativos e não pode receber uma garantia que o sistema não consegue
   cumprir. Falha de adaptador ou estado desconhecido deve aparecer como
   `Unavailable`/`Blocked`, não como permissão silenciosa.
2. Fechar a cobertura suportada por canal. `malcontent` não é um bloqueio
   universal de `execve`, RPM, navegador, container, VPN ou DoH. O produto deve
   testar e documentar limites por canal, sem chamar defesa complementar de
   enforcement completo.
3. Reusar primeiro a interface e o serviço mantidos pelo GNOME. Construir no
   Lyra somente a integração residual demonstrada pelos testes; não criar uma
   segunda loja nem duplicar política já fornecida pelo GNOME Software.
4. Não armazenar documento, biometria, data de nascimento exata ou histórico de
   navegação/processos para inferir idade. Não escolher método de aferição antes
   da aprovação de privacidade e da revisão jurídica aplicável.
5. Não declarar conformidade jurídica neste plano. Ele organiza engenharia e
   evidências; interpretação legal permanece com o parecer profissional e deve
   ser revisada quando a ANPD publicar orientação definitiva.

## Sequência de execução

### Atualização 06/10 — topologia em implementação

Após aprovação do plano, o worktree local do instalador recebeu o layout schema
4: scope Snapper `@lyra-parental`, autoridade irmã `@lyra-parental-authority`,
subdiretórios privados `catalog`/`inventory`/`ledger` no scope, locks estáveis,
configuração Snapper própria e montagem explícita do `.snapshots` parental no
`fstab`. A permissão ESP só é gravada no finalizador depois de operações e
desmontagem bem-sucedidas. O código vegad mantém o gate de topologia fechado.

Este layout ainda não foi compilado nem qualificado em VM para reboot ou
rollback, e o fluxo não está integrado ao daemon. Go não está disponível nesta
sessão; não houve build/testes. Sem instalar na máquina local, publicar RPM ou
ativar D-Bus. O próximo passo é revisão/qualificação da topologia em VM; depois
fechar o formato assinado do emissor e a autorização de manutenção.

### Bloqueio técnico atual — primeira emissão e integração do instalador

A biblioteca de emissão inicial do vegad e o registro one-shot na ESP estão em
worktrees locais, mas ainda não são chamados pelo daemon e não constituem fluxo
de produto. O layout atual do instalador coloca `/var/lib` dentro de `@`; por
isso, criar os diretórios parentais ali não os protege contra rollback. Também
faltam um emissor autenticado da referência inicial e a ação Polkit específica
com revalidação pós-prompt.

Ordem para fechar esse bloqueio:

1. Qualificar `@lyra-parental` como scope Snapper separado de `@` e
   `@lyra-parental-authority` como subvolume irmã; catalog/inventory/ledger e
   `catalog.lock` ficam no scope restaurável, enquanto `reference.lock` fica na
   authority fora dele. Qualificar mounts, reboot e rollback real.
2. Definir formato e chave confiável do emissor para a referência completa
   inicial; o cliente D-Bus não pode fornecer referência, owners ou chave.
3. Implementar bootstrap root-only retomável que consuma a permissão ESP e
   publique referência/markers com o protocolo durável existente.
4. Criar ação Polkit e revalidar sessão, capability e topologia depois do
   diálogo e sob o lock.
5. Conectar o serviço vegad, provar recusas sem escrita, concorrência e
   interrupções em VM Leap 16.1 com ESP VFAT/Btrfs/bus/Polkit reais.
6. Só após estes e os demais gates parentais, publicar Leap 16.1 e instalar
   localmente para o teste já autorizado com nova conta infantojuvenil.

Detalhe e critérios de aceite: `worktrees/vegad-parental-catalog/docs/parental-reference-provisioning.md`.
O construtor `NewESPBackedReferenceProvisioner` permanece fail-closed até o
layout independente ser provisionado. Sem daemon/issuer/Polkit reais, não expor
API de emissão nem declarar essa parte concluída.

### 1. Fechar escopo, responsabilidades e decisão de privacidade — #10 e #11

**Entrega:** atualizar a matriz existente para separar Lyra/OS, GNOME,
GNOME Software/Flatpak, fornecedores de aplicativos, responsável e usuário
supervisionado; registrar quais fluxos o Lyra controla e quais não controla.

**Atualização 06/10/2026:** a matriz agora classifica explicitamente as
afirmações técnicas, as guardas/decisões provisórias de produto e as atribuições
que continuam pendentes de revisão profissional. Ela não resume o parecer
confidencial nem afirma uma conclusão jurídica. O item permanece aberto até o
mantenedor e o profissional responsável conferirem a redação e registrarem a
aprovação na issue #10.

Rascunho técnico inicial: [matriz de responsabilidades](eca-digital-responsibility-matrix.md).
Ela ainda precisa ser revisada contra o parecer aprovado pelo mantenedor antes
de representar a posição jurídica do projeto.

**Aceite:** parecer aprovado é referenciado sem publicar material confidencial;
cada dado, finalidade, retenção, responsável e evidência tem dono; os limites
do Vega como configurador e do GNOME Software como loja ficam explícitos;
nenhum método de aferição ou dado sensível é presumido.

### 2. Resolver o bloqueio de enforcement do Flatpak — P1 #102

O caso foi reproduzido em VM descartável Leap 16.1 com os RPMs oficiais. A
investigação upstream esclareceu que Flatpak trata malcontent como filtro de
UX/catálogo, não como fronteira de segurança: falhas do barramento são ignoradas
porque o usuário pode iniciar seu próprio barramento ([PR upstream #6663](https://github.com/flatpak/flatpak/pull/6663),
[issue upstream #5076](https://github.com/flatpak/flatpak/issues/5076)). Não
manter fork local que simplesmente transforma esses casos em negação. O PR #6663
foi integrado ao `main` upstream, mas trata falha de acesso ao barramento; não
resolve por si só o cenário distinto de #102. Reproduzir/refutar #102 com os RPMs
oficiais exatos do Leap 16.1 continua sendo um passo explícito antes de decidir
se o defeito requer correção upstream, mudança de empacotamento ou permanece
confirmado. A evidência arquivada de 21/09 usa
`flatpak-1.16.6-160100.2.3`; em 07/10 o sistema local informa
`1.16.6-160100.2.6`, enquanto o índice público OSS consultado lista `.2.5`.
Essa diferença de revisão exige capturar origem, assinatura e RPMs efetivos
dentro de uma VM descartável nova; nenhuma política parental foi alterada no
host. O disco vazio do ensaio de instalação de 06/10 foi preservado e não será
reutilizado por um helper que o recria automaticamente.

O requisito aprovado é “aplicativos aprovados e proteção contra evasão”. Para
satisfazê-lo, qualificar uma fronteira MAC dedicada que cubra Flatpak como uma
origem de processos entre outras. Malcontent pode ser controle complementar de
UX/política, mas não conta como enforcement. Se o confinamento e seus caminhos
de entrada não forem qualificados, a conta supervisionada não deve ser
habilitada na Alpha 8.

**Reprodução atualizada em 07/10/2026:** o RPM oficial assinado
`flatpak-1.16.6-160100.2.6` foi instalado apenas em overlay de VM Leap 16.1.
Com AccountsService ativo, `malcontent-client check-app-filter` negou o ref
(`rc=3`), mas `flatpak run org.lyra.TestApp` pela conta de teste retornou
`rc=0`. A falha #102 permanece na revisão atual; a imagem-base ficou íntegra
e a VM foi desligada. [Relatório e verificador](../../analysis/2026-10-07/parental-flatpak-current-rpm/CURRENT.md).
O SRPM oficial `.2.6` confirma `-Dmalcontent=disabled` no `flatpak.spec` e
registra a desativação como contorno para problemas de `xdg-desktop-portal`.
Assim, não reativar a opção ou criar pacote Lyra sem qualificar portais; mesmo
reativada, ela não substitui o gate MAC contra evasão.

O domínio experimental já negou binários genéricos e cópias, shell, Python,
carregador ELF, `mmap(PROT_EXEC)` e `mprotect(PROT_EXEC)` em enforcing. PAM/GDM,
systemd-user e ensaios gráficos ampliaram a cobertura, mas continuam presos a
UIDs/estados fictícios, patches de diagnóstico ou sessões que não qualificam
uma conta inteira. A próxima prova deve fechar uma lacuna de produção por vez,
começando por ciclo autorizado de identidade e revogação segura, antes de
transformar qualquer fixture em pacote.

**Prova de separação em 07/10/2026:** dois domínios SELinux em Enforcing na VM
permitiram binários de teste diferentes para duas contas supervisionadas e
negaram a execução cruzada com `EACCES`. Ambos negaram o launcher Flatpak; a
conta comum continuou executando. [Evidência e verificador](../../analysis/2026-10-07/parental-selinux-account-isolation/CURRENT.md).
Um segundo overlay confirmou seleção distinta por `pam_selinux.so` numa pilha
PAM isolada, com execução recíproca permitida/negada em Enforcing. A prova não
autentica pelo GDM nem permite um app Flatpak aprovado. O próximo gate é a
vinculação de conta no login real e a execução identificada de um Flatpak permitido e
outro negado, incluindo helpers, sem abrir rotas alternativas. #102 continua
aberta e a proteção parental integral permanece NO-GO.

**Limite de rótulo por arquivo, 07/10/2026:** dois apps Flatpak locais com
payload idêntico compartilharam dispositivo/inode e rótulo SELinux. `chcon`
em A mudou também B; a restauração de A restaurou B. Os dois executaram
depois, e o overlay foi desligado. [Evidência e verificador](../../analysis/2026-10-07/parental-flatpak-inode-identity/CURRENT.md).
Portanto, não usar só xattr/tipo do executável do deployment como identidade
de app. O próximo protótipo de enforcement deve vincular o ref aprovado à
criação/confinamento do processo e provar isolamento entre apps que compartilham
objetos OSTree, além de rollback e revogação.

**Diagnóstico da entrada em 07/10/2026:** permitir somente o executável
`/usr/bin/flatpak` no domínio restrito não fez o app funcionar em Enforcing.
O launcher falhou primeiro ao abrir o repositório; após duas permissões amplas
usadas só para diagnóstico, falhou em `ftruncate`. O audit registrou recusas
de bubblewrap, memfd e objetos OSTree. O mesmo UID/contexto comum executou o
app. [Relatório e verificador](../../analysis/2026-10-07/parental-flatpak-launcher-boundary/CURRENT.md).
O SRPM oficial aceita caminhos/FDs alternativos de app e runtime; qualquer
broker futuro deve fixar a identidade e os deployments, validar a política sem
confiar em argumentos do usuário, e confinar launcher, bubblewrap, app e
auxiliares sem liberar entradas diretas. Não copiar as permissões diagnósticas
para uma política de produto. #102 segue aberta/NO-GO.
O [contrato da fronteira de execução Flatpak](parental-flatpak-execution-boundary.md)
define identidade, entradas proibidas, revogação e provas de aceitação.

**Protótipo de admissão em 07/10/2026:** branch vegad isolada
`feat/parental-flatpak-admission` implementa um frame com só `app_id`, rejeita
campos forjados/duplicados, e lê UID/GID/PID e contexto SELinux pelo socket
Unix. Testes Go 1.22.12 e VM em Enforcing passaram: UID 1003 observado,
`uid:0` no payload recusado. Uma segunda VM em Enforcing passou quatro casos
com UIDs 1003/1011 e domínios `lyra_test_child_a_t`/`lyra_test_child_b_t`:
pedido válido de cada um aceito e UID forjado recusado. São clientes `runcon`
de fixture, não login real. O componente não autoriza nem lança apps. Próximo
gate: comparar o peer com UID/GID/domínio e geração ativa do catálogo, testar
transferência de socket e resolver ref/origem/deployment sem usar dados do
cliente como autoridade. #102 permanece OPEN/NO-GO.

**Vínculo de snapshot e remetente em 07/10/2026:** `BindFlatpakLaunchPeer`
reutiliza classificação parental para exigir conta ativa, identidade, geração
e política dos adaptadores, GID e domínio SELinux exatos. É uma observação de
snapshot, sem lease ou autorização de app. A leitura passou a usar
`SO_PASSCRED`: VM em Enforcing passou seis casos nas duas contas, aceitando
pedidos válidos e recusando UID forjado e escrita por processo filho que
herdou o socket. A fixture usa `runcon`; login real, mudança de contexto no
mesmo PID, resolução de deployment, revogação e execução confinada seguem
pendentes. Evidência em `worktrees/vegad-parental-flatpak-admission/docs/evidence/parental-flatpak-admission/`.
#102 segue OPEN/NO-GO.

**Seleção de deployment em 07/10/2026:** função pura no protótipo vegad exige
um único ref instalado para o app, escopo/UID/origem/publicador aprovados,
commit íntegro e runtime de arquitetura compatível. Sem identidade verificável
do publicador, atualizações não herdam aprovação: o commit deve coincidir.
Testes de ambiguidade, alteração de origem, branch, assinatura e runtime
passaram. Ainda faltam inventário confiável/atômico, fixação do deployment e
lançamento MAC confinado; #102 permanece OPEN/NO-GO.

**Inventário real em VM, 07/10/2026:** dois apps de fixture exibiram refs,
commits e links `active` distintos; ambos usam o mesmo runtime. Seus remotes
locais têm verificação GPG desligada, logo o nome da origem não prova o
publicador. [Evidência](../../worktrees/vegad-parental-flatpak-admission/docs/evidence/parental-flatpak-inventory/CURRENT.md).
Chamadas separadas a `flatpak info` não fixam um snapshot até o processo
nascer. O próximo gate permanece um leitor confiável/atômico e a fixação do
deployment; o probe de diagnóstico não deve alimentar autorização.

**Commit e FD em VM, 07/10/2026:** `flatpak run` com `--commit` e
`--runtime-commit` lançou A/B com os pares corretos e recusou commit de B
para A e runtime inexistente. Mas `--app-fd` aceitou conteúdo de B ao pedir A
e executou um binário presente só em B. [Evidência](../../worktrees/vegad-parental-flatpak-admission/docs/evidence/parental-flatpak-commit-pin/CURRENT.md).
O broker precisa construir os commits/FDs de fonte confiável e bloquear
execução direta pelo domínio da criança; o ensaio foi Permissive, sem
enforcement. #102 segue OPEN/NO-GO.

**Chamada fechada em 07/10/2026:** o protótipo vegad compõe argumentos
Flatpak somente do deployment selecionado, sem argv/FD do cliente. O Go gerou
chamadas com escopo, arquitetura, branch, runtime e commits completos; quatro
casos no Flatpak 1.16.6 da VM passaram (A/B permitidos, app/runtime trocados
recusados). [Evidência](../../worktrees/vegad-parental-flatpak-admission/docs/evidence/parental-flatpak-run-args/CURRENT.md).
Ainda Permissive e com inventário de fixture; não autoriza app nem substitui
MAC, origem verificada e revogação. #102 OPEN/NO-GO.

**Lease de admissão em 07/10/2026:** o vegad ganhou `WithFlatpakLease` para
reler catálogo, inventário, prova e marcadores sob os locks existentes e
comparar peer/geração antes do callback síncrono. Testes com arquivos reais
verificam locks retidos e recusa de catálogo alterado, bloqueio, prova inválida,
inventário ausente e adaptador defasado. Ainda não há callback de lançamento,
integração com aprovação de apps, qualificação de todos os escritores nem
prova de MAC/SELinux. #102 OPEN/NO-GO.

**Matriz mínima:** aplicativo permitido e negado; instalação por usuário e por
sistema; `flatpak run`; GNOME Software; xdg-desktop-portal (FileChooser e
ScreenCast); AccountsService ausente/reiniciado; barramento indisponível;
cancelamento/negação de autorização; atualização, downgrade e rollback.

**Contrato de produto consolidado em 07/10:** qualificar uma conta local nova
com sessão GNOME e zero apps de usuário aprovados, mantendo a infraestrutura
mínima da sessão. Provar aprovação por **app identificável**, não por pacote
RPM inteiro, e auxiliares somente quando pertencem ao app autorizado. Para a
mesma conta, testar Flatpak e RPM permitidos/negados, AppImage/script/cópia sem
identidade negados, execução por atalho, CLI e carregador, interpretação e
memória executável, instalação do usuário sem aprovação, troca de origem ou
publicador, e revogação durante processo aberto (novas execuções imediatas,
encerramento em até dez segundos). TTY/SSH/remoto da supervisionada devem negar
login; contas comuns e administração local devem funcionar como antes. A
interface não pode indicar proteção ativa até que esses testes e as transições
de falha/recovery passem na imagem candidata exata.

**Aceite:** para conta supervisionada, falhas relevantes negam a operação ou
exibem estado indisponível antes de apresentá-la como protegida; contas comuns,
login inicial e funções administrativas autorizadas continuam funcionando.
Registrar limitações upstream e não afirmar bloqueio de execução universal.
Este aceite depende de confinamento imposto pelo sistema; o filtro Flatpak
sozinho não pode satisfazê-lo.

Se não houver solução segura e suportável no ciclo, documentar precisamente os
canais disponíveis e retirar a alegação/UX de proteção dos canais sem
enforcement. Não promover o pacote com apenas a opção de build habilitada.

### 3. Concluir a qualificação upstream no Leap 16.1 — #6

Atualizar a qualificação para a revisão testada: origem SUSE, repositórios
oficiais, assinaturas, dependências, versões, política D-Bus/polkit e interação
com GNOME Software. Validar a correção do passo 2 com RPMs reais em staging,
sem repositório comunitário ou pacote local não reproduzível na imagem.

**Aceite:** testes e logs ligados a versões/hash de fonte; instalação e remoção
limpas; política persiste ao reiniciar AccountsService, sessão e máquina;
rollback restaura estado consistente; issue #102 resolvida ou marcada como
limitação que remove formalmente aquele canal do escopo.

### 4. Aprovar arquitetura e UX final — #5 e #8

Reconciliar a ADR proposta com a qualificação GNOME. Desenhar papéis de
administrador, responsável e usuário supervisionado; sinal mínimo e finalidade;
consentimento, contestação, retificação, revogação e recuperação; estado offline
e estado desconhecido. Revisar a UX nativa do GNOME e decidir quais links,
estados ou operações pequenas o Vega precisa oferecer.

Usar a [proposta de ciclo de identidade](parental-identity-lifecycle-proposal.md)
como entrada de revisão, especialmente para recuperação, tombstones e a
distinção entre exclusão e retirada da supervisão. Ela ainda não foi aprovada.

**Aceite:** ADR aceita após revisão de segurança, privacidade e acessibilidade;
protótipos e textos deixam claro o que está e não está aplicado; fluxo funciona
em `en-US`, `pt-BR` e `es-ES`; nenhum texto induz falsa sensação de proteção.

### 5. Implementar apenas a lacuna comprovada — #2 e #7

Depois da ADR, decidir por componente se há código Lyra necessário. Se houver,
implementar adaptadores pequenos e tipados para identidade, estado de política,
GNOME Software e Vega. Manter autorização no serviço apropriado, fora da GUI;
usar operações privilegiadas mínimas mediadas por polkit. Se GNOME já satisfaz
um requisito, documentar e integrar a UI em vez de criar backend duplicado.

**Aceite:** API versionada e autenticada; armazenamento root-only, atômico,
com versão e recuperação; alteração transacional; Vega mostra revisão e saúde
real dos adaptadores; ausência do Vega não desativa enforcement; falha não muda
uma conta para adulta nem apaga política.

### 6. Completar o gate técnico e de release — #9 e #11

Automatizar testes negativos onde possível e guardar resultados reproduzíveis
para o artefato exato. Incluir pelo menos: múltiplas contas, CLI, D-Bus, mudança
de privilégios, instalação/execução por canal, metadados ausentes/conflitantes,
adaptador indisponível, persistência/corrupção, update/rollback, recovery,
acessibilidade e i18n. Versionar relatório de impacto à proteção de dados
quando aplicável; evidência não deve incluir dados pessoais desnecessários.

**Aceite:** a candidata passa a matriz aprovada; documentação apresenta limites
residuais; o resultado ECA Digital da Alpha 8 referencia revisões jurídica,
segurança e privacidade e contém testes de negação/evasão. Nenhum P0/P1 parental
fica aberto para qualquer funcionalidade anunciada como suportada.

### 7. Decisão de disponibilização

Publicar a integração parental somente se os passos anteriores passarem e a
candidata limpa repetir os testes. Se não passar, manter a funcionalidade fora
da imagem/escopo anunciado e registrar o motivo e o trabalho remanescente. O
parecer jurídico favorável, isoladamente, não substitui esse gate técnico.

## Dependências e paralelismo

O trabalho de escopo (#10) pode avançar em paralelo à reprodução técnica de
#102. A qualificação #6 depende da resolução ou delimitação formal do #102. A
ADR/UX (#5/#8) devem usar essa qualificação; backend e Vega (#2/#7) só começam
depois das decisões correspondentes. O gate #9 executa durante cada fase e é
fechado na candidata final, não por mocks ou resultados de versões anteriores.

## Fontes normativas para revisão profissional

- [Lei nº 15.211/2025 — Planalto](https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2025/lei/l15211.htm)
- [Decreto nº 12.880/2026 — Planalto](https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2026/decreto/d12880.htm)
- [Página ECA Digital e cronograma da ANPD](https://www.gov.br/anpd/pt-br/assuntos/eca-digital/)
- [Orientações preliminares de aferição etária da ANPD](https://www.gov.br/anpd/pt-br/assuntos/eca-digital/mecanismos-confiaveis-de-afericao-de-idade-orientacoes-preliminares.pdf/@@display-file/file)

As orientações da ANPD continuam em evolução; revisar a fonte oficial e pedir
reavaliação profissional antes de congelar a decisão de release.


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

### 06/10/2026 — sondagem parcial do layout Snapper

Uma VM Leap 16.1 descartável confirmou que Snapper 0.12.1 registra a
configuração `lyra-parental` em `SNAPPER_CONFIGS`, cria o snapshot inicial e,
após reboot, monta scope, authority e `.snapshots` pelas linhas do `fstab`.
Assim, o instalador não precisa editar `SNAPPER_CONFIGS` manualmente. A
sondagem usou raiz ext4 e um segundo disco Btrfs descartável; não qualifica o
instalador Rust nem o rollback da raiz Lyra.

O comando `snapper rollback` recusa configurações sobre subvolumes que não
sejam `/`. Para o scope parental, o critério correto é restaurar os dados do
snapshot e confirmar que o vegad detecta a divergência do pin/witness. O
rollback normal da raiz Btrfs deve ser qualificado separadamente, verificando
que scope e authority irmãs permanecem íntegros. Evidência parcial:
[`parental-layout-probe-20261006`](../../worktrees/vegad-parental-catalog/docs/evidence/parental-layout-probe-20261006/README.md).
O gate de prontidão continua fechado até teste do instalador, raiz Btrfs,
upgrade e reinstalação em VM descartável.

### 06/10/2026 — rollback raiz Btrfs qualificado em imagem de ensaio

Uma segunda VM Leap 16.1 foi preparada com raiz Btrfs `/@` e scope/authority
como subvolumes irmãs no mesmo filesystem. `snapper --no-dbus -c root --ambit
classic rollback 1` selecionou snapshot 1, criou a cópia gravável #5 e, após
reboot, montou `/` em `@/.snapshots/5/snapshot`. Um marcador criado depois do
snapshot inicial desapareceu; testemunho do catálogo e `reference.lock` ficaram
com os mesmos hashes, e scope, authority e ambos os `.snapshots` permaneceram
montados. A tentativa sem `--ambit classic` foi recusada porque Snapper não
inferiu o modo.

Essa sondagem montou subvolumes/configuração/fstab manualmente numa imagem
qcow2 descartável copiada de outro guest; não executou a sequência Rust nem
qualificou ISO, upgrade ou reinstalação. O gate permanece fechado até repetir
sobre a saída real do instalador. [Evidência e logs](../../worktrees/vegad-parental-catalog/docs/evidence/parental-root-btrfs-rollback-20261006/README.md).

### 06/10/2026 — verificação reforçada de persistência

Repeti o rollback clássico até o snapshot #7 com sentinelas no catálogo e na
authority. Depois do reboot, ambos mantiveram hash e inode, o marcador pós-
snapshot na raiz sumiu e os cinco mounts continuaram ativos. Isso fecha a
sondagem manual de isolamento do rollback raiz; a sequência do instalador,
upgrade e reinstalação continuam pendentes.
