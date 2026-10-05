# Guard isolado do despacho administrativo de contas

[guard.py](guard.py) acrescenta ao [bridge](../parental-service-withdrawal/README.md)
um gate de despacho para UpdateUser/SetAdmin em conta ordinary positiva.
É componente experimental, sem comandos Unix, hook no UsersService ou RPM.

## Comportamento

O serviço gera plano imutável e vincula método, remetente/revisão/catálogo,
geração, inventário e snapshot da prova/marker/journal/owner. O cliente devolve
somente ID. Conta supervised, desconhecida, identidade divergente, prova ausente
ou qualquer componente negativo impedem despacho. Até um marcador corrompido
prevalece sobre o registro positivo; não é tratado como conta comum.

Autorização recebe payload separado com método/alvo/revisão, fora dos locks.
Após o diálogo, o guard revalida capacidade, remetente, TTL, catálogo, inventário
e ledger. Mantém catálogo SH/inventário/withdrawal EX durante a chamada ao
adaptador confiável. Um escritor cooperativo de withdrawal não publica intent
entre conferência final e despacho. O controlador serializa chamadas; usa o
mesmo gate reentrante por associação do bridge. Não é qualificação multithread.

O plano é consumido ANTES de chamar o adaptador, inclusive se este lançar erro:
não repetir uma possível mutação parcial com o mesmo plano. Falha não dispara
userdel, remoção de home, exclusão de política ou compensação permissiva.
Após callback concluído, identidade observada deve continuar igual à tupla.
Resultado OrdinaryMutationDispatched informa só que o callback retornou e a
conferência passou; não atesta aplicação real, durabilidade ou quiescência.

## Fronteira dos métodos existentes

Inspeção local de vegad/internal/dbusserver/users.go, HEAD
1c671bac5ce6a813d0732bbcb847dce314ae9417: CreateUser chama useradd/chpasswd e
possui compensação userdel -r; UpdateUser e SetAdmin podem alterar grupos; RemoveUser
chama userdel -r. Hoje esses métodos não consultam a classificação parental.
Não foram alterados neste ensaio.

| Método | Comportamento desta fixture | Trabalho antes de integrar produto |
|---|---|---|
| UpdateUser/SetAdmin | Dispatch apenas ordinary íntegra sem barreira; adapter simulado deve preservar tupla | Selar parâmetros/efeitos específicos, validar inputs no servidor e aplicar autorização administrativa adequada |
| CreateUser | UnsupportedOperation | Reserva e classificação antes de login possível, journal e publicação protegida |
| RemoveUser | UnsupportedOperation, inclusive ordinary | Retirada/inibição/quiescência, tombstone e retenção antes de liberar IDs/remover dados |
| Qualquer método em supervised/unknown/blocked | Recusa antes do callback administrativo | Operação parental própria, com papéis e lifecycle qualificados |

A recusa de criação/remoção limita **esta etapa experimental**; não altera a
API administrativa publicada nem retira esses requisitos da entrega final.
Falta selar booleano de administração, grupos e outros argumentos no plano real;
aqui o adaptador é do controlador confiável e não recebe inputs mutáveis da GUI.
Não usar este guard como autorização genérica de shell ou usermod.

## Validação

Na raiz do worktree:

```sh
python3 -m unittest discover -s tests -p test_parental_administrative_guard.py -v
python3 -m unittest discover -s tests
```

**13 testes específicos e suíte completa de 793 testes PASS**.
[Saída arquivada](tests-output.txt) e [escopo/hashes](results.json).

Os 13 testes específicos cobrem: ordinary e peer preservados, métodos indisponíveis,
supervised/unknown, overlay negativo/corrompido, identidade divergente, negação/
erro de autorização, payload adulterado, nova barreira durante diálogo,
conflitos catálogo/inventário/prova, capacidade/remetente/TTL alterados,
restart/plano alheio, reentrância, plano consumido e erro sem compensação.
Catálogo/flock são reais no usuário do laboratório. Inventário/ledger são
simulados em memória e o callback administrativo só registra chamadas.
Não houve useradd/usermod/userdel, nova VM, ensaio Polkit ou mudança na estação.
As evidências anteriores reais continuam separadas; não qualificam este novo
guard automaticamente.

Próximo: qualificar a conexão do guard ao adaptador administrativo isolado com
armazenamento/transporte reais e parâmetros selados, antes de modificar métodos
de produto. Permanecem gates #2/#5, identidade/persistência/rollback, papéis,
#6/#102, UX e ISO. Controle parental de produto continua NO-GO.

## Teste local autorizado pelo mantenedor

Nesta conversa o mantenedor pediu que, **assim que o controle parental estiver
concluído**, seja instalado na estação para teste com uma conta local nova de
criança/adolescente, que ele criará. A instalação local passa a fazer parte da
entrega e está autorizada; não pedir essa autorização novamente.
Antes dessa instalação, concluir integração e validação de criação/migração/
recuperação, pacote e manutenção da conta principal. A autorização não converte
as fixtures atuais em proteção pronta. Preservar o diagnóstico de falhas e
um procedimento qualificado de recuperação que conserve a política.
