# Transporte D-Bus e decisão Polkit reais no laboratório parental

Resultado: **oito cenários PASS**, mais retomada por outro processo com nova
consulta Polkit. Limpeza confirmada, contas/PAM/SELinux/configurações existentes
preservados, backing com hash/metadados iguais à etapa anterior e VM OFF/QEMU 0.

A fixture usa o barramento de sistema real, dbus-python, GetConnectionUnixUser
e pkcheck --system-bus-name para o remetente único recebido pelo método D-Bus.
Reutiliza [classificador/planejador](../parental-service-classifier/README.md),
[ligação](../parental-service-withdrawal/README.md), Inventory, Operations,
Withdrawal e writer histórico sem alterar fontes. Catálogo/inventário/ledger
são arquivos root-owned com locks reais, como no [ensaio anterior](../parental-service-storage/README.md).

## Cenários e aceites

| Cenário | Resultado observado |
|---|---|
| Permissão | Chamador UID1000 resolvido pelo bus; ação exclusiva retorna pkcheck 0; retira prova e conserva conta vizinha/catálogo/inventário |
| Negação | Ação exclusiva retorna pkcheck 1; Denied, ledger idêntico |
| Cancelamento | Agente da fixture registra-se para processo do cliente; BeginAuthentication retorna PolicyKit1.Error.Cancelled; pkcheck 3; Denied, ledger idêntico |
| Capacidade revogada após decisão | Polkit 0, mas revalidação recusa com AuthorizationFailure antes da escrita |
| Catálogo alterado após decisão | Polkit 0, mas revisão/digest novos impedem primeira escrita com AuthorizationFailure |
| Outra conexão do mesmo UID | Plano da conexão anterior não é aceito pela nova; Denied antes de Polkit |
| Chamador sem capacidade | UID1002 identificado pelo bus; Plan negado sem consulta Polkit e sem escrita |
| Consulta própria | UID1000 lê OrdinaryEligible sem interação/consulta Polkit e sem escrita |

Após permissão, o processo servidor é encerrado e recriado com os mesmos
arquivos. Outro cliente, com outro nome único, retoma a operação persistida
com nova consulta Polkit 0. TODOS os arquivos de catálogo/inventário/ledger
conservam hash/inode/UID/GID/modo/tamanho. Não reconstrói plano como autoridade.

Em cada consulta de autorização, probes reais tomam EX nos três locks antes
de pkcheck: catálogo, inventário e withdrawal. O serviço não recebe UID de
chamador ou nome de remetente como argumento; dbus-python fornece sender_keyword
para métodos com entradas tipadas Plan(st), Execute(s), Resume(ss) e OwnState().
Objetos e erros públicos não devolvem dumps ou stderr do pkcheck.

## Política do ensaio e limites

Nome temporário: org.lyraos.ParentalFixture1. Ações temporárias:
org.lyraos.parental.fixture.allow/deny/challenge. A permissão positiva vem de
uma regra Polkit restrita à ação allow e ao usuário fictício installeduser;
**não houve autenticação positiva por senha nem diálogo GNOME qualificado**.
Cancelamento usa um agente programático que devolve Cancelled, sem ler senha.
A ação challenge usa auth_self sem cache. Não equivale a testar perda de todas
as credenciais ou recuperação de responsável.

Capacidade técnica permanece uma tabela/callback da fixture que aceita UID1000;
não implementa vínculo de responsável, cadastro, papel persistente ou aprovação
final de ações do produto. Revogação/revisão são alterações controladas pelo
servidor de teste depois da decisão real, para exercitar a revalidação do bridge.
UID0 do servidor não é tratado como responsável pelo chamador. A conta alvo é
fictícia e a prova positiva é JSON sintético, sem hook PAM/login real.

Somente na VM foram criados, depois removidos:

- /etc/dbus-1/system.d/lyra-parental-fixture.conf;
- /usr/share/polkit-1/actions/org.lyraos.parental.fixture.policy;
- /etc/polkit-1/rules.d/00-lyra-parental-fixture.rules;
- /run/lyra-parental-dbus-test e o subtree fixtures da pasta exclusiva de ensaio.

O bus recarregou configuração; o Polkit carregou/removeu ações pelo mecanismo
upstream. Servidores foram encerrados e o agente foi desregistrado. Hashes das
configurações preexistentes de D-Bus/Polkit, contas e PAM ficaram iguais, e o
SELinux permaneceu Permissive. Não qualifica Enforcing/MAC, GNOME completo,
API do vegad, política contra evasão, guard UsersService, boot, rollback,
quiescência ou a ISO. Produto NO-GO e #2/#5 finais/#6/#102 continuam abertos.

## Artefatos e próximo passo

[result.json](result.json) guarda respostas, decisões, snapshots e checks de
restauração; [execution.json](execution.json) registra retorno 0.
[source-hashes.json](source-hashes.json) sela os onze módulos usados.
[cleanup-check.json](cleanup-check.json), [poweroff.json](poweroff.json) e
[vm-off.json](vm-off.json) confirmam limpeza/desligamento e backing preservado.
[manifest.json](manifest.json) registra hashes dos artefatos e fontes.

```sh
python3 docs/evidence/parental-service-auth/verify-evidence.py
```

[fixture.py](fixture.py) adapta somente o prefixo de preparação do guest do
ensaio de armazenamento (nova pasta, sem seu runner de testes).
[server.py](server.py), [client.py](client.py) e [guest.py](guest.py) são executáveis
de laboratório, não instaladores. [host-run.py](host-run.py), [vm.py](vm.py) e
[host.py](host.py) arquivam o controle usado em analysis/2026-10-05/parental-service-auth.
O host-run opera uma VM já lançada/guardada; não é um driver completo de
criação/desligamento. Exige overlay exclusivo e serial/marcadores de laboratório.
Disco: /tmp/lyra-parental-service-auth-20261005/system.qcow2.

Fontes/testes existentes estão inalterados por hashes; não repetimos a suíte
780 ou os cortes históricos para adicionar estes cenários independentes.
Próximo componente isolado: guard das mutações administrativas que respeite
classificação/barreira e recuse operação não suportada sem liberar/remover dados.
Integração e instalação de produto ainda dependem dos gates de arquitetura,
persistência/rollback, papéis, enforcement e release; não promover pacote parental.
