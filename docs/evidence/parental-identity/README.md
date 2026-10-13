# Identidade e admissão supervisionada — 28/09/2026

O módulo anterior tinha GID1004 e grupo compilados no código. Este ensaio usa
vínculos explícitos `nome:UID:GID:grupo_privado` em configuração PAM de root e
exercita duas contas com IDs diferentes. Continua exclusivamente experimental:
nada instalado em logins reais, host, receita ou pacotes OBS.

## Contrato ensaiado

`bindings.py` gera um fragmento único com seletor e argumentos do módulo. Se
**qualquer** nome, UID ou GID coincidir com um vínculo, o módulo exige que todos
os componentes coincidam com exatamente um vínculo, incluindo o grupo privado.
Renomear a conta/grupo ou alterar só UID/GID não a transforma em conta comum.
IDs reservados, sintaxe inválida e vínculos duplicados são recusados.

O seletor usa o módulo oficial
[`pam_succeed_if`](https://man7.org/linux/man-pages/man8/pam_succeed_if.8.html):
todas as condições de conta comum precisam ter sucesso para pular o módulo
experimental. Erro no seletor segue para o módulo obrigatório. Assim, quando
o módulo experimental está ausente, as duas contas supervisionadas são
recusadas e a comum continua executando. Isso depende da integridade do
fragmento completo e do PAM oficial; não cobre remoção da configuração inteira.

O guard exige SELinux globalmente enforcing, domínio não permissivo e contexto
de execução pendente exato. O contexto ainda é fixo da política experimental;
somente os identificadores Unix deixaram de estar compilados no módulo.
O fragmento deve ser substituído inteiro, com propriedade de root e sem escrita
pela conta. O gerador puro não instala configuração nem cadastra supervisão.

## Resultado

[47 cenários nativos](result.json) passaram, usando libpam e libselinux reais,
compilação `-Wall -Wextra -Werror` e a política já existente na VM:

| Grupo de cenários | Evidência |
| --- | --- |
| Duas contas, UID1003/GID1004 e UID21000/GID23000 | Probe aprovado executa no contexto restrito; Python recebe EACCES |
| Módulo ausente | Ambas recusadas; conta comum executa Python |
| SELinux global/domínio permissivo ou mapeamento ausente | Supervisionada recusada; comum preservada |
| Nome, UID, GID ou nome do grupo alterado de verdade | Supervisionada recusada; comum preservada |
| GID de uma conta coincide com outro vínculo | Conta ambígua recusada; outra supervisionada e comum preservadas |
| 16 configurações inválidas | PAM_SERVICE_ERR, sem executar payload |
| Recuperação | Duas contas voltam ao probe aprovado; Python continua negado; comum executa |

O harness `pam-probe.py` é chamado por root e abre apenas uma **sessão PAM**:
não autentica senha, não simula login gráfico e não prova cobertura de todas as
entradas da conta. A lista de nomes/programas do harness é intencionalmente
limitada às fixtures. Os testes Python de geração rejeitam injeção de novas
linhas/opções, IDs inválidos e cadastros ambíguos antes de produzir texto PAM.

`exercise.py` só executa no disco `lyra-admission-test` com marcador
`lyra.parental-identity-test=1`. Compila um módulo separado e usa somente
`/etc/pam.d/lyra-identity-probe`. Cria uma conta temporária com IDs livres e
desfaz alterações em `finally`. O resultado confirma retirada de conta,
mapeamento, grupo, módulo e arquivo PAM, preservação dos IDs das contas
originais e retorno ao estado permissivo inicial da VM. Não afirma restauração
byte a byte de toda a base de contas após ferramentas como `useradd`/`userdel`.

A VM é cópia descartável da fixture anterior, com boot direto de kernel,
não uma ISO candidata. O hash do disco de origem antes/depois da cópia foi
`8699b33a0672f497d0fd949b62a7163bd6fb5569feff5a74bae007a4c839ce26`.
As versões e hashes dos fontes usados estão em [provenance.json](provenance.json).

## Limites e próxima etapa

- O contrato cobre contas locais com identidade parcialmente divergente.
  NSS remoto, aliases, indisponibilidade de passwd e identidade inteiramente
  substituída não foram qualificados. Uma conta que deixe de coincidir em
  **todos** os identificadores pode cair no caminho comum.
- Remoção/recriação com os mesmos identificadores pode herdar um vínculo
  antigo. Cadastro, renomeação, migração e remoção precisam de uma transação
  autorizada que cuide também de sessões existentes e processos persistentes.
- Mudanças de política não revogam processos já abertos. Este ensaio não
  integra GDM, systemd-user, D-Bus, TTY, SSH, cron ou lingering; não substitui
  as fixtures antigas dessas entradas nem qualifica recuperação administrativa.
- O seletor e o guard consultam a identidade separadamente. Atualizações
  concorrentes da base precisam de controle no ciclo de cadastro; atomicidade
  do arquivo PAM sozinho não resolve essa corrida.

Próximo: definir o ciclo autorizado de identidade e integrá-lo às entradas reais,
ensaiando falhas e recuperação com conta comum preservada. Depois concluir
evasão, identidade dos aplicativos e integração conforme a
[fronteira aprovada](../../parental-protection-boundary.md). #6/#102 seguem
abertas. Este avanço não autoriza promoção de produção ou conclusão da Alpha8.

### Diagnóstico de reutilização de identidade — 29/09/2026

`reuse-diagnostic.py` reproduz uma lacuna do protótipo, sem alegar uma evasão
iniciada pela conta supervisionada: depois de remover a conta fictícia e sua
entrada SELinux, o controlador recria um registro de conta com o mesmo nome,
UID, GID e grupo. A configuração PAM persistente contém somente essa tupla;
por isso a nova conta é admitida no mesmo domínio SELinux. O resultado esperado
do diagnóstico é `stale_binding_reused: true`, não um gate de segurança aprovado.

Isso confirma que a tupla identifica os atributos atuais, mas não a geração da
conta. O ciclo de produção precisa invalidar a associação antiga e exigir
reinscrição/revisão autorizada, com tombstone e transação protegida contra
concorrência. A reprodução usa privilégios de root na VM, não demonstra que o
usuário supervisionado consegue remover/recriar contas e não implementa o
registro de geração.

O runner exige simultaneamente os marcadores `lyra.parental-selinux-test=1`,
`lyra.parental-identity-test=1` e o disco virtio `lyra-admission-test`; remove
módulo PAM, configuração, usuário, grupo e mapeamento ao terminar. Na VM
descartável, prepare os quatro arquivos fonte em `/root` a partir da raiz do
repositório e execute:

```sh
python3 analysis/2026-09-28/parental-identity/host.py push \
  worktrees/desktop-parental-identity/docs/evidence/parental-identity/pam-guard.c /root/identity-pam-guard.c
python3 analysis/2026-09-28/parental-identity/host.py push \
  worktrees/desktop-parental-identity/docs/evidence/parental-identity/bindings.py /root/identity-bindings.py
python3 analysis/2026-09-28/parental-identity/host.py push \
  worktrees/desktop-parental-identity/docs/evidence/parental-identity/pam-probe.py /root/identity-pam-probe.py
python3 analysis/2026-09-28/parental-identity/host.py push \
  worktrees/desktop-parental-identity/docs/evidence/parental-identity/reuse-diagnostic.py /root/identity-reuse-diagnostic.py
python3 analysis/2026-09-28/parental-identity/vm.py virtualization cmd \
  python3 /root/identity-reuse-diagnostic.py
```

O diagnóstico foi executado e sua cópia está em
[reuse-result.json](reuse-result.json). `passed: true` significa que a
reprodução e a limpeza terminaram com sucesso; o achado continua sendo uma
lacuna, pois `stale_binding_reused: true`. O JSON contém apenas a identidade
fictícia usada no teste. Nunca versionar o disco da VM nem substituir a matriz
anterior de 47 cenários. Esse resultado informa #5 e o desenho do ciclo, mas
não fecha a lacuna de reutilização.

### Prova do registro de geração no PAM — 29/09/2026

O protótipo alternativo
[`pam-registry-guard.c`](pam-registry-guard.c) lê um registro em diretório
root-only, valida proprietário, tipo, modo, links, tamanho e sintaxe, e confere
tupla e geração com os argumentos da configuração PAM. Estados `blocked`,
`provisioning`, `transitioning`, `recovering` e `tombstone` não admitem sessão.
O registro e a configuração PAM precisam ser atualizados pelo mesmo
controlador; o módulo não inventa nem persiste gerações.

Os [12 cenários](registry-result.json) passaram na VM descartável. A geração A
ativa admitiu sessão no domínio experimental; gravar seu tombstone antes de
remover a conta fez a recriação com a mesma tupla ser recusada. Uma nova geração
B só foi admitida após enrollment explícito e atualização da configuração; a
configuração obsoleta de A continuou recusada. Registro bloqueado, ausente,
malformado, gravável ou legível por outros usuários foi recusado, a conta comum
continuou executando e o estado válido foi recuperável. O hash do módulo
compilado e os hashes dos fontes estão no JSON.

Esta prova mostra que o PAM consegue aplicar o tombstone produzido pelo fluxo
autorizado; não demonstra que PAM detecta uma remoção feita manualmente por
root. Também não implementa o serviço, journal durável, `fsync`, lock de
transição ou coordenação com sessões concorrentes. O ensaio continua sendo uma
sessão PAM aberta por root, não login GDM/TTY/SSH nem cobertura completa de
entradas. É caracterização arquitetural, não qualificação de produto.

Para reproduzir esta prova, transfira `pam-registry-guard.c`,
`registry-diagnostic.py` e o `pam-probe.py` já usado acima com `host.py push`,
depois execute:

```sh
python3 analysis/2026-09-28/parental-identity/host.py push \
  worktrees/desktop-parental-identity/docs/evidence/parental-identity/pam-registry-guard.c /root/identity-pam-registry-guard.c
python3 analysis/2026-09-28/parental-identity/host.py push \
  worktrees/desktop-parental-identity/docs/evidence/parental-identity/registry-diagnostic.py /root/identity-registry-diagnostic.py
python3 analysis/2026-09-28/parental-identity/vm.py virtualization cmd \
  python3 /root/identity-registry-diagnostic.py
```

### Prova do escritor transacional — 29/09/2026

[`registry-transaction.py`](registry-transaction.py) é um helper experimental,
não um daemon. Ele usa lock `flock`, journal root-only, arquivo temporário
criado com exclusividade, `fsync` do arquivo, `rename` atômico e `fsync` do
diretório. O tombstone é durável antes de publicar a nova geração. Recuperação
mantém transações incompletas em `recovering`/`tombstone`; só limpa o journal
como commit quando a fase e os registros persistidos concordam.

Os [16 cenários](registry-transaction-result.json) passaram: interrupção de
processo nos checkpoints antes/depois da publicação do journal e do registro,
limpeza de temporários deixados antes do `rename`, recuperação fail-closed e
duas tentativas concorrentes de início, das quais só uma foi aceita. Uma
interrupção antes de publicar o journal deixou o estado original ativo porque
nenhuma mutação tinha começado; depois que o journal se tornou durável, a
recuperação manteve as gerações não concluídas bloqueadas.

O ensaio injeta `os._exit` em uma VM descartável. Não é corte de energia nem
falha real de armazenamento, não executa `userdel` como parte do escritor, não
liga o escritor ao módulo PAM e não adquire o lock nos caminhos PAM. Portanto,
não prova durabilidade diante de hardware que ignora `fsync`, corrida entre
uma abertura de sessão e uma transição, recuperação automática no boot ou
integração com GDM/TTY/SSH. Esses passos ainda faltam antes de qualquer serviço
de produto.

Para reproduzir, transfira os dois fontes para a VM com `host.py push` e rode:

```sh
python3 analysis/2026-09-28/parental-identity/host.py push \
  worktrees/desktop-parental-identity/docs/evidence/parental-identity/registry-transaction.py /root/identity-registry-transaction.py
python3 analysis/2026-09-28/parental-identity/host.py push \
  worktrees/desktop-parental-identity/docs/evidence/parental-identity/registry-transaction-diagnostic.py /root/identity-registry-transaction-diagnostic.py
python3 analysis/2026-09-28/parental-identity/vm.py virtualization cmd \
  python3 /root/identity-registry-transaction-diagnostic.py
```

### Lock entre PAM e transição — 29/09/2026

O módulo experimental agora mantém um lock `flock` compartilhado no estado do
handle PAM até `pam_sm_close_session`; o escritor tenta o lock exclusivo sem
esperar e retorna `Busy` se uma sessão admitida ainda estiver aberta. A prova
integrada está em [registry-pam-lock-result.json](registry-pam-lock-result.json)
e usa o mesmo arquivo de lock, módulo e registro nas duas pontas.

Os nove checks passaram: com sessão aberta a transição não alterou o estado;
depois do fechamento, ela gravou `transitioning` e uma nova admissão foi
recusada; após tombstone, a conta recriada com a mesma tupla continuou recusada;
uma geração nova foi admitida somente após enrollment explícito. Isso testa um
handle PAM sintético e o `close_session` correspondente, não confirma que GDM,
TTY, SSH, lingering ou todos os serviços mantenham o mesmo handle por toda a
vida da sessão. Também não prova que o encerramento do handle significa que não
restam processos ou conexões do UID. O estado de sessões reais ainda precisa
ser integrado e qualificado.

### Cobertura por canal de entrada e vida do usuário — 29/09/2026

| Canal/componente | Evidência existente | O que ela prova | Lacuna para o lease/transição |
| --- | --- | --- | --- |
| `systemd --user` | PR139, [admissão de gerenciadores](https://github.com/lyra-os-linux/lyraos-desktop/blob/25c2d46868de58b378a920e87db041e601182a0f/docs/evidence/parental-managers/README.md) | 19 cenários nativos: lease retido por sd-pam, reexec preserva lock, falhas recusam supervisionada e preservam conta comum. | Usa a barreira anterior, sem registro por geração; lingering e processos sobreviventes ainda precisam de prova. |
| GDM | PR139/140, [senha real e autenticação em andamento](https://github.com/lyra-os-linux/lyraos-desktop/blob/3419a1e56569b4febabeb69fa9fbedb4ee642711/docs/evidence/parental-password/README.md) | 14 cenários de autologin e 18 de senha; worker/sd-pam retêm lease, autenticação pendente é recusada após blocked. | Worker de diagnóstico e sessão ELF mínima; não qualifica GNOME completo, geração de identidade, desbloqueio ou revogação. |
| TTY/login local | PR138, [entradas CLI nativas](https://github.com/lyra-os-linux/lyraos-desktop/blob/a619b9637335d08476f67797cf65c260052fb49a/docs/evidence/parental-entries/README.md) | Login nativo com senha em PTY é recusado pela barreira account; conta comum e restauração passam. | Não é getty/console da ISO nem lease por geração; autenticações iniciadas antes da instalação continuam pendentes. |
| SSH | PR138, [entradas CLI nativas](https://github.com/lyra-os-linux/lyraos-desktop/blob/a619b9637335d08476f67797cf65c260052fb49a/docs/evidence/parental-entries/README.md) | Novos comandos, SFTP e túnel sem shell recusados pela barreira account, preservando conta comum. | Um túnel autenticado antes da barreira continuou transportando dados; revogação e autenticações antigas não estão resolvidas. |
| Cron/timers | Sem resultado de canal real localizado | Nada sobre execução sem login interativo. | Decidir se tarefas agendadas da conta supervisionada são permitidas; testar cron e timers de usuário sob a política aprovada. |
| Lingering/user manager | `loginctl enable-linger` e encerramento após logout não foram exercitados nos resultados consultados | Não há prova de que o user manager pare após o último login. | Testar lingering habilitado e desabilitado, unidades persistentes e processos após `pam_close_session`; a transição precisa bloquear ou encerrar explicitamente esse estado. |
| Registro e escritor | [teste do lease sintético](registry-pam-lock-result.json) | Exclusão mútua entre um handle PAM de teste e a transação; geração antiga recusada após tombstone. | O handle sintético não reproduz os módulos PAM de GDM/TTY/SSH nem rastreia processos que sobrevivem a `close_session`. |

Este inventário impede interpretar um teste de componente como cobertura do
sistema inteiro. O próximo ensaio deve partir das PRs138–140 já integradas, inventariar
em VM descartável as pilhas PAM e as opções de `systemd-logind` (incluindo
lingering), e conectar o registro por geração aos serviços nativos. Não
repetir os ensaios anteriores sem alteração relevante. Registrar o
serviço PAM efetivamente chamado, abertura/fechamento, sessões de logind,
processos e `user@UID.service` antes e depois do logout. A transição só pode
prosseguir quando não houver sessão, conexão ou processo da geração; se algum
canal não oferecer essa garantia, o desenho precisa de quiescência e encerramento
controlado. Não instalar PAM global nem ativar `KillUserProcesses` como atalho:
isso poderia interromper contas comuns e não substitui a medição por canal.

Os testes também devem confirmar que uma falha ou timeout preserva a conta
comum, mantém o registro bloqueado e recuperável e não reutiliza a identidade
antiga. Só depois dessa matriz passar faz sentido trocar o handle sintético por
integração com sessões de produto. As evidências atuais não autorizam ativar o
mecanismo no host ou fechar #6/#102.
