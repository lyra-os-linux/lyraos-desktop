# Fronteira de execução Flatpak para contas supervisionadas

Status: **contrato de implementação, ainda sem componente de produto**.
Controle parental integral e issue #102 continuam NO-GO. Este documento
descreve condições verificáveis para um protótipo; não autoriza instalar ou
publicar um broker, uma regra SELinux ou uma alteração no Flatpak.

## Problema comprovado

O RPM oficial `flatpak-1.16.6-160100.2.6` do Leap 16.1 foi construído com
`-Dmalcontent=disabled`. Na VM, `malcontent-client` negou o ref e `flatpak run`
o executou. Dois apps com payload igual compartilharam o mesmo inode OSTree;
`chcon` num deployment mudou também o rótulo do outro. Quando o launcher foi
permitido num domínio SELinux restrito, a execução real falhou em operações
do repositório, bubblewrap e memfd; a mesma conta fora do domínio executou.
Evidências:
[reprodução do RPM](../../analysis/2026-10-07/parental-flatpak-current-rpm/CURRENT.md),
[inode compartilhado](../../analysis/2026-10-07/parental-flatpak-inode-identity/CURRENT.md),
[fronteira do launcher](../../analysis/2026-10-07/parental-flatpak-launcher-boundary/CURRENT.md).

## Autoridade e identidade

Uma aprovação pertence à conta local supervisionada e a **um app** Flatpak
identificável. O registro deve incluir ref completo (tipo, ID, arquitetura e
branch), escopo de instalação (sistema ou usuário), origem exibida ao
responsável e identidade verificável do publicador/assinatura. Nome de remote
sozinho não é prova de publicador. O commit ativo identifica o deployment
usado em um lançamento, mas não substitui a identidade aprovada: atualizações
assinadas da mesma origem podem preservar a aprovação, conforme as
[decisões de produto](parental-controls-product-decisions.md). Mudança de
origem, assinatura ou publicador exige aprovação nova. Se a origem não oferecer
uma identidade verificável estável, o broker não deve presumir continuidade da
aprovação após atualização.

O pedido de execução vindo da sessão contém somente um identificador de app,
sem opções livres de linha de comando, caminho, FD, runtime ou ambiente
fornecido como autoridade. Um serviço confiável resolve o ref instalado,
confere a política local válida da conta e fixa o deployment e runtime que
serão usados. Deve rejeitar ambiguidade entre instalações, ref inexistente,
política expirada/inconsistente e mudança entre a conferência e o lançamento.
O SRPM oficial aceita `--app-fd`, `--app-path`, `--usr-fd` e `--usr-path` em
`app/flatpak-builtins-run.c`; essas opções não podem ser controladas pela
conta supervisionada na fronteira de autorização. O mesmo vale para chamadas
diretas a `libflatpak` e binários alternativos que iniciem bubblewrap.

No [ensaio com dois apps](../../worktrees/vegad-parental-flatpak-admission/docs/evidence/parental-flatpak-commit-pin/CURRENT.md),
`--commit` e `--runtime-commit` lançaram o par correto e recusaram commits
errados. Porém `--app-fd` permitiu pedir A e montar o conteúdo de B. Um FD
somente fixa um diretório, não autentica qual app ele representa. O broker
deve derivar ref, commits e quaisquer FDs da própria autoridade e bloquear
as rotas de chamada direta no domínio supervisionado.

## Fronteira de processos

O kernel deve impedir que a conta supervisionada lance diretamente `flatpak`,
`bwrap`, cópias desses binários, scripts, AppImages ou executáveis genéricos.
O caminho aprovado precisa conservar um contexto MAC restrito até o app e
seus auxiliares; apenas permitir `flatpak` no domínio da criança não basta.
GNOME e serviços essenciais podem iniciar a sessão com zero apps aprovados,
mas qualquer execução de código escolhida pela criança deve cruzar a mesma
fronteira. Um serviço ativado por D-Bus, systemd-user, portal ou desktop file
não pode voltar a um contexto comum para lançar o app em nome da criança.

O broker não deve confiar em UID, app ID, `FLATPAK_ID`, `/.flatpak-info`,
variáveis de ambiente ou PID informados pelo próprio cliente. Deve obter a
identidade de origem de credenciais do kernel/canal autenticado, consultar a
política correspondente e associar a autorização à criação real do processo.
O launcher e auxiliares somente recebem permissões mínimas para o app
selecionado; permitir genericamente `bin_t`, `var_lib_t` ou `file_type` como
executáveis abriria novamente outras rotas. A prova de inode compartilhado
impede tratar xattr do payload como identidade do app.

Ao revogar: bloquear novas admissões antes de notificar o app, dar até dez
segundos ao processo já aberto para encerrar e então terminar todo o grupo de
processos do app. Reentrada, auxiliares tardios e processos que sobrevivam ao
launcher devem ser cobertos. Contas comuns continuam com o comportamento
atual, sem depender da saúde do broker parental.

## Gate para aceitar uma implementação

1. Em SELinux Enforcing, com dois apps de teste cujo payload compartilha o
   mesmo inode, a conta supervisionada executa só o ref aprovado. O ref
   negado falha com launcher oficial, cópia/cliente alternativo, desktop file,
   D-Bus, systemd-user e chamada direta ao runtime/bubblewrap. Outra conta
   supervisionada pode ter a autorização inversa; conta comum permanece
   funcional.
2. Origem, assinatura, escopo, branch, runtime e deployment trocados entre
   autorização e lançamento são recusados ou revalidados sem janela de
   evasão. Atualização assinada preserva a aprovação apenas quando as
   condições de produto permanecem verdadeiras. Downgrade/rollback não
   restaura permissão revogada.
3. Ausência do serviço, política inválida/expirada, falha MAC, portal ou
   barramento indisponível não permite execução silenciosa. O login da conta
   comum e a infraestrutura mínima da sessão supervisionada continuam
   disponíveis conforme seus contratos próprios.
4. Revogação durante execução impede processos novos imediatamente, encerra
   o grupo inteiro após o prazo de dez segundos e mantém a política correta
   após reboot. FileChooser/ScreenCast e GNOME Software são testados com app
   aprovado e negado antes de chamar o recurso de público.

O próximo experimento deve começar pelo caminho de processo/credenciais em
uma VM descartável, mantendo o produto desligado. Só depois de existir
autorização verificável de ref/deployment vale ampliar a política SELinux para
bubblewrap e auxiliares; permissões diagnósticas da VM não são base segura.
