# Revisão de admissão e início de systemd-user — 22/09/2026

Continuação do [ensaio anterior](../parental-selinux/README.md). Código
exclusivamente experimental: não instalar no host, em logins reais ou na ISO.

## Identificação independente da consulta de grupo suplementar

O primeiro guard precisava consultar o cadastro de grupos antes de distinguir
contas comuns de supervisionadas. Esta revisão identifica a conta fictícia
pelo seu **GID primário privado 1004**, preservado no registro da conta, e só
depois valida a entrada de grupo e o contexto SELinux. A conta comum não
depende dessa consulta. Nenhum grupo compartilhado foi criado.

`pam-guard.c` mantém GID, nome de grupo e contexto fixos de fixture. Isso não
é uma política de alocação de IDs para produção. Criação, migração, reutilização
de GID, mudanças de cadastro e fontes NSS ainda precisam de contrato e testes.
Falha do próprio cadastro de identidade (`getpwnam_r`) continua rejeitando a
admissão; não declarar independência de toda infraestrutura de contas.

`exercise.py` e `admission-result.json`: doze cenários passaram. Na injeção
de inconsistência, root **renomeia** o grupo privado e restaura em `finally`.
A conta supervisionada é rejeitada e a comum continua executando. Isso não
é uma simulação de todas as falhas NSS nem de destruição de `/etc/passwd`.
Mapeamento ausente, permissividade global/do domínio e módulo ausente seguem
bloqueando a conta supervisionada; a restauração permite acesso novamente.

O guard só está na pilha PAM de ensaio. Não foi adicionado ao PAM oficial de
`systemd-user`, GDM ou login. Módulo PAM obrigatório ausente ainda pode afetar
contas comuns na mesma pilha; cobertura e recuperação finais seguem pendentes.

## Gerenciador de usuário em enforcing

`domain.cil` inclui permissões específicas de keyring de `init_t` para o
domínio fictício e marca o destino como `process_user_target`, conforme as
constraints da política oficial. Isso resolveu a falha anterior `224/PAM`
e a negação de transição de identidade. Foram acrescentados execução de
`init_exec_t`, leitura de configuração/unidades, dados temporários, cgroups
e comunicação local necessária à preparação do gerenciador. A propriedade
Unix/delegação continua aplicável; o ensaio não comprova isolamento completo
entre todas as contas ou serviços. Nenhum `allow` de execução genérica para
`bin_t` ou `shell_exec_t` foi acrescentado.

Também foram corrigidos rótulos de links `/bin`, `/sbin`, `/lib` e `/lib64`
na raiz descartável. Não são alterações na receita da distribuição.
O diagnóstico `semodule -DB` foi temporário; `semodule -B` restaurou o
logging normal antes dos resultados finais.

`systemd-probe.py` e `systemd-result.json`: **os dois gerenciadores ficaram
active/running em enforcing**, com UID 1003 no contexto
`lyra_parental_u:lyra_parental_r:lyra_parental_probe_t:s0` e a conta comum no
domínio padrão. O gerenciador restrito alcançou `default.target`, mas seu
`dbus.socket` e `systemd-tmpfiles-setup.service` falharam. Portanto, gerenciador
ativo **não equivale a sessão utilizável**, GNOME aprovado ou proteção completa.

`execution-regression.py` e `execution-result.json` repetem os onze cenários
do ensaio original após a política mudar: dois positivos internos, sete
negações EACCES, controle da conta comum e mesmo UID fora do domínio.
O último continua executando Python — a cobertura da conta inteira não foi
demonstrada. A escrita em runtime foi adicionada, mas a criação de novos
arquivos pela conta seguida de tentativa de execução ainda exige ensaio
específico; o teste de cópia atual usa fixture preparada pelo administrador.

## Estado e próximo passo

VM desligada. Checkpoint persistente do disco em
`analysis/2026-09-22/parental-admission/system-checkpoint.raw`; não versionar
o disco. Launcher/control preservados em
`analysis/2026-09-21/parental-selinux/`. Boot permanece permissivo; os testes
ativam enforcing e restauram permissive ao terminar.

Próximo: testar escrita seguida de execução em runtime, resolver serviços
essenciais de sessão sem permitir clientes alternativos, definir identificação
de produção e integrar a checagem de admissão às entradas reais. Depois
qualificar GDM/D-Bus, TTY/SSH/cron/lingering e recuperação. Sem pacote OBS,
sem alteração de receita, sem ISO. Issues #6/#102 permanecem abertas.
