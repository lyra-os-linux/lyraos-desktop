# Ensaios SELinux/PAM — 21 e 22/09/2026

**Somente fixtures descartáveis. Não instalar estas fontes no host ou na ISO.**
Os nomes de usuário, grupo e contexto são fixos de propósito. Não há pacote
de produção nem proteção completa de conta implementada aqui.

## Execução no domínio (21/09)

`execution-domain.cil`, `execution-probe.c`, `execution-exercise.py` e
`execution-result.json` preservam o ensaio original. Kernel
`6.12.0-160100.4-default`, política oficial targeted
`20260826+git0.492b478c7-160100.1.1`, UID fictício 1003.

Dois positivos internos e sete negações EACCES: binário genérico, cópia,
shell, Python, carregador ELF, mmap executável de arquivo e mprotect de
memória anônima. Conta comum executa Python; o mesmo UID fora do domínio
também executa Python. São onze cenários e duas verificações de preparação.
O domínio não é permissivo e o kernel ficou enforcing durante o ensaio.

Permissões de leitura/map são amplas para isolar a execução. Isso não é
uma política de privacidade; aplicações e bibliotecas aprovadas ainda devem
ser auditadas. Negar Python não equivale a confinar um Python aprovado.

## Sessão PAM dedicada (22/09)

`session-domain.cil` acrescenta papel próprio e transições de entrada ao
protótipo anterior. `setup.py` prepara o mapeamento SELinux da conta fictícia.
`fix-fixture.py` permite exclusivamente o controle positivo do agente para
o domínio da conta comum. O módulo instalado mantém o nome
`lyra-parental-probe`; não instalar os dois CIL simultaneamente.

`pam-probe.py` chama a biblioteca PAM, abre sessão, lê o contexto de execução,
reduz UID/GID e executa o processo de teste. Exige root e marcador da VM;
**não autentica uma sessão real**. A pilha isolada `lyra-parental-probe`
contém `pam_selinux.so close/open nottys`, sem alterar GDM/login.

`pam-baseline.json`: contexto restrito selecionado e Python negado;
conta comum funciona. Remover o mapeamento com root faz o PAM selecionar
`unconfined_u:unconfined_r:unconfined_t:s0` e Python executa. A injeção de
falha não demonstra que a conta supervisionada consiga remover o mapeamento.

`pam-guard.c` é um módulo PAM experimental, compilado na VM com headers
oficiais `pam-devel` e `libselinux-devel`, `-Wall -Wextra -Werror`, ligado a
libpam/libselinux. `setup-guard.py` instala-o somente na pilha de ensaio como
`session required`, depois de `pam_selinux.so open`. Confere associação ao
grupo fictício, contexto selecionado, enforcing global e flag de domínio
permissivo retornada pelo kernel. Não monitora sessões já abertas.

`exercise-guard.py` e `pam-guard-result.json` registram doze casos:

| Caso | Resultado |
| --- | --- |
| Programa aprovado / Python não aprovado | Executa / EACCES |
| Conta comum, configuração íntegra | Executa |
| Mapeamento supervisionado ausente | PAM rejeita; conta comum ainda executa |
| Kernel permissivo ou domínio permissivo | PAM rejeita |
| Cadastro de supervisão ausente | PAM rejeita ambas as contas |
| Módulo obrigatório ausente | PAM rejeita |
| Configuração restaurada | Aprovado e conta comum voltam a executar |

**Bloquear a conta comum quando o cadastro fica indisponível é uma limitação
de disponibilidade do protótipo, não um critério de entrega atendido.**
É necessário definir identificação persistente e recuperação que não
transformem falhas de supervisão em indisponibilidade das contas comuns.
Não copiar esta pilha para `common-session` antes dessa correção.

## Serviço real systemd-user

`systemd-probe.py` inicia somente os serviços das duas contas fictícias em
enforcing. `systemd-result.json` registra conta comum ativa e restrita
rejeitada com `224/PAM`: `pam_selinux` não conseguiu definir contexto de
criação de keyring. O gerenciador restrito não chegou a executar.
Esse teste precede a instalação do guard e usa o PAM oficial de systemd-user.
Não é qualificação de GNOME, D-Bus, TTY/SSH, cron, lingering ou recuperação.

## Reprodução e estado preservado

Scripts de preparação não são idempotentes (`semanage ... -a`, criação de
grupo e extensão de CIL). Rever o estado antes de executá-los. Os runners
exigem `lyra.parental-selinux-test=1`; nunca remover essa verificação.
Os scripts de exercício restauram configuração injetada em `finally` e
voltam a permissive ao terminar. O boot da fixture permanece permissivo.

Infraestrutura, logs e checkpoints persistentes estão no workspace em
`analysis/2026-09-21/parental-selinux/` e
`analysis/2026-09-22/parental-session/`. A VM foi desligada após coleta.
Nenhum pacote ou política do host foi alterado.

Próximo: resolver disponibilidade da conta comum na falha do cadastro e
permissões mínimas de sessão/keyring; depois qualificar todas as entradas e
serviços da conta. Issues #6/#102 continuam abertas. Sem promoção OBS ou ISO.
