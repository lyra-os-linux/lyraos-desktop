# Admissão real e recursos de sessão — 22/09/2026

Continuação do [ensaio de admissão](../parental-admission/README.md).
Todos os arquivos são experimentais, para a VM marcada
`lyra.parental-selinux-test=1`, e não habilitam proteção na distro.

## Entrada real do gerenciador

A VM preserva o nome PAM `systemd-user` e copia sua pilha oficial para
`/etc/pam.d/systemd-user`, acrescentando os dois controles de sessão
registrados em `systemd-user.pam`. `pam_succeed_if` pula o guard para GID
primário diferente de 1004. A conta fictícia supervisionada passa pelo guard
de [parental-admission](../parental-admission/pam-guard.c).
O arquivo PAM é evidência da base desta VM, não um substituto universal para
as pilhas de outras versões.

Uma tentativa anterior de substituir PAMName por uma pilha que incluía
systemd-user deixou o gerenciador aguardando a sessão. Foi descartada;
o drop-in está desativado. A integração final conserva a identidade original
do serviço. Não modifica common-session, GDM, login ou SSH.

`real-admission.py` / `admission-result.json`: 12 cenários no serviço real
`user@UID.service`, incluindo saúde, mapeamento removido, módulo ausente,
grupo privado renomeado, modo global permissivo e recuperação. Em cada
falha injetada por root, a conta supervisionada não inicia (224/PAM) e a comum
inicia. Isso amplia o ensaio anterior, que usava somente uma pilha dedicada.
Os IDs e contexto continuam fixos de fixture; produção, NSS, sessões já
abertas e todas as entradas alternativas permanecem pendentes.

## Recursos da sessão sem execução dos dados gravados

`diagnostics.json` identifica o rótulo `session_dbusd_tmp_t` do socket e
negação de escrita no memfd de serialização do systemd. `domain.cil` adiciona
permissões para esse socket, metadados/cgroups observados e um tipo dedicado
`lyra_parental_runtime_t` para arquivos criados em tmpfs. Esse tipo recebe
escrita, mas não execução. Não foi liberada execução genérica de `bin_t`,
`shell_exec_t` nem `execute_no_trans` de `lib_t`.

`diagnostics-after.json`: socket D-Bus passa a escutar e desaparece a falha
de serialização; tmpfiles chega à etapa de execução, que segue negada.
`services-result.json` confirma os dois gerenciadores ativos, mas o broker
restrito não executa. D-Bus da conta comum responde normalmente. Portanto,
**não há sessão GNOME funcional ou proteção integral da conta comprovadas**.
Os diagnósticos desabilitam dontaudit temporariamente e restauram-no em
finally; os resultados funcionais finais usam a configuração normal.

`write-exec.py` / `write-exec-result.json`: processo no domínio escreve uma
cópia válida de true (hash conferido), mas execução e mmap executável são
negados. O mesmo arquivo executa fora do domínio com o mesmo UID, excluindo
arquivo inválido ou impedimento Unix como explicação. Também grava um memfd
com o novo tipo e recebe EACCES tanto em mmap executável quanto fexecve.
Este último caso verifica negações; não é qualificação completa de todos os
formatos de código ou mecanismos de memória.

`execution-regression.py` / `execution-result.json`: os onze cenários
anteriores mantêm os resultados esperados, incluindo os positivos. O mesmo
UID fora do domínio ainda executa Python. Proibir esse caminho em toda a
conta ainda exige integrar e testar as demais entradas.

## Reprodução e retomada

Usar a fixture e os pré-requisitos dos ensaios anteriores; compilar probe.c
com `gcc -Wall -Wextra -Werror`, restaurar seu rótulo aprovado, instalar
`domain.cil` como `/tmp/lyra-parental-probe.cil` via semodule e reproduzir a
configuração PAM apenas nas contas fictícias. Os scripts verificam o marcador,
ativam enforcing durante os testes e restauram permissive no final. Não
executar os ensaios simultaneamente, pois alteram o estado global da fixture.

VM desligada após sync. Disco persistente mais recente:
`analysis/2026-09-22/parental-services/system-checkpoint.raw` (não versionado).
Launcher/control: `analysis/2026-09-21/parental-selinux/`.

Próximo: autorizações específicas e isolamento para dbus-broker, tmpfiles e
auxiliares; depois GNOME/portais e entradas GDM/TTY/SSH/cron/lingering,
identidade de produção e recuperação. Issues #6/#102 continuam abertas.
Sem pacote OBS, mudança de receita ou ISO.
