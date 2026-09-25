# Unidades gravadas pela conta e geradores nativos — 22/09/2026

Continuação da [ativação restrita](../parental-activation/README.md), somente
na VM descartável. Não habilita controle parental no host ou na receita.

## Arquivos criados pelo processo restrito

`writer.c` cria o diretório de unidades runtime e os arquivos com o UID e
contexto do chamador. O teste não grava seu conteúdo como root. O harness
confere propriedade Unix, conteúdo e contexto emitido pelo escritor; os
arquivos da supervisionada recebem user_tmp_t. Executa a recarga e tenta
iniciar três unidades: programa aprovado, Python e programa aprovado com
pedido de contexto unconfined.

`exercise.py` / `result.json`: os três pedidos da conta restrita são rejeitados
por **service:start sobre user_tmp_t**, antes da execução, inclusive o programa
aprovado. A recarga também é negada; o teste não a libera. Um serviço oficial
(tmpfiles) continua aceitando start, e a conta comum grava e inicia as mesmas
três unidades. Portanto, a evidência é de bloqueio de unidades runtime escritas
pela conta, não de seleção do executável dentro desses arquivos. Unidades
transitórias e arquivos oficiais têm cobertura separada no ensaio anterior.

O cliente pode solicitar um nome novo sem daemon-reload; o journal confirma
que o gerenciador encontrou o arquivo recém-gravado e aplicou a mediação.
Não estender esse resultado a arquivos persistentes no home, links, overrides
ou todas as formas de autostart. Os arquivos de teste são removidos ao terminar.

## Aprovação específica de dois geradores

A política acrescenta `lyra_parental_generator_exec_t` e permite sua execução
sem sair do domínio restrito. `setup-generators.py` associa somente os caminhos
oficiais de 30-systemd-environment-d-generator e systemd-xdg-autostart-generator
a esse tipo na fixture. Não concede execute_no_trans a lib_t. Os dois arquivos
são ELF nativos; 60-flatpak é um script /bin/sh e continua bloqueado.

`generators.py` / `generators-result.json` usa arquivos fictícios do sistema,
removidos em finally, e confirma em enforcing:

- Variável de /usr/lib/environment.d aparece no ambiente do gerenciador.
- O gerador de ambiente executado diretamente pelo helper restrito também
  emite a variável; UID/contexto aparecem antes da execução.
- O gerador autostart produz uma unidade para o executável aprovado, enquanto
  a entrada de Python não produz unidade nesse ensaio.
- A tentativa direta de executar o script Flatpak recebe EACCES.

**Gerar a unidade não qualifica sua execução automática nem a sessão GNOME.**
O próximo passo inclui ativação do target gráfico, condições de autostart,
portais e aplicativos reais. A integração do gerador Flatpak precisa de solução
específica; não liberar o shell genérico da conta para contornar essa pendência.

## Regressões e reprodução

Unidades runtime foram revalidadas após a aprovação dos geradores. A regressão
de ativação D-Bus/transitória e troca de contexto passou novamente
(`activation-result.json`, [script](../parental-activation/exercise.py)).
Os onze cenários de execução anteriores mais duas preparações passaram
(`execution-result.json`, [script](../parental-services/execution-regression.py));
seu hash coincide com domain.cil. Escrita/execução em arquivo e memfd preservou
as negações (`write-exec-result.json`, [script](../parental-services/write-exec.py)).
Os checks de admissão PAM não foram modificados nesta etapa.

Compilar writer.c na fixture com `gcc -Wall -Wextra -Werror`, instalar em
/opt/lyra-parental-probe/unit-writer e rotular com lyra_parental_probe_exec_t.
Carregar domain.cil sob o nome de módulo `/tmp/lyra-parental-probe.cil` antes
de executar setup-generators.py, que não é idempotente. As associações locais
não são empacotamento de produção; rollback remove as duas entradas fcontext,
restaura os rótulos oficiais e recarrega a política anterior. Nunca executar
esses procedimentos no host ou nas contas reais.

VM desligada após sync. Checkpoint mais recente:
`analysis/2026-09-22/parental-user-units/system-checkpoint.raw` (não versionado).
Launcher/control preservados em `analysis/2026-09-21/parental-selinux/`.
Próximo: ativação gráfica/autostart e integração GNOME/GDM/Flatpak; ainda faltam
TTY/SSH/cron/lingering, identidade de produção e recuperação. Mesmo UID fora
do domínio ainda executa Python. #6/#102 abertas; sem OBS/ISO nesta etapa.
