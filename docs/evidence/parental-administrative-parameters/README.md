# Parâmetros administrativos selados no plano

[parameters.py](parameters.py) envolve o [guard existente](../parental-administrative-guard/README.md)
sem alterar seus fontes. Fecha a lacuna de autorizar somente método/alvo e
buscar parâmetros mutáveis da GUI depois do diálogo. Escopo: fixture isolada,
sem integração ao vegad ou execução de comandos Unix.

## Contrato implementado

UpdateUser aceita somente full_name, groups e is_admin. SetAdmin aceita somente
is_admin. Schema/tipos fechados, limite de nome/grupos, nomes de grupo validados,
grupo desconhecido ou falha no resolver recusados. Senha/foto retornam
UnsupportedOperation; não são guardadas ou hasheadas neste plano experimental.
A entrega final continua exigindo seus fluxos próprios, sem redução silenciosa
da API publicada.

O plano guarda Parameters congelado, grupos como tuplas ordenadas (nome,GID) e
digest canônico dos valores. Mudança da lista/dicionário de entrada não muda o
plano; dados mostrados à autorização são uma cópia. O serviço guarda o plano
associado ao ID server-side; Execute não recebe novo grupo, booleano, perfil ou
alvo. O guard de base continua conferindo remetente/geração/revisão/ledger.

is_admin é estritamente booleano. UpdateUser com is_admin=false e wheel na lista
é recusado, eliminando a divergência entre flag e efeito. Com true, wheel entra
no conjunto autorizado. SetAdmin descreve adição/remoção de wheel, preservando
os demais grupos em vez de substituir toda a lista. Isso representa a semântica
de wheel, não afirma que todo privilégio do sistema deriva desse grupo.

O resolver confiável de grupos fornece GID no planejamento. Nomes/GIDs são
revalidados antes/depois do callback de autorização e imediatamente no limite
do adaptador. Troca/ausência/inconsistência de GID impede despacho; não troca
silenciosamente o grupo autorizado. Esse resolver ainda é callback da fixture,
não descoberta NSS completa ou geração persistente de grupos. Recriação de
grupo com a mesma tupla não é detectada; não há lease global de mutações NSS.

O adaptador recebe apenas método, Account imutável vindo do catálogo e
Parameters selado. command produz argv fixo para usermod/gpasswd, com alvo
proveniente do servidor, separador -- quando aplicável e nenhum shell.
Metacaracteres do nome de exibição permanecem num único argumento literal.
**Os comandos são construídos, mas não executados nos testes.** Falha no
adaptador consome o plano em ambas as camadas e não dispara compensação.

Nome de exibição é dado de perfil: permanece em memória no plano efêmero e no
payload de autorização autorizado; esta fixture não o persiste em journal de
operações. Qualificar redaction, armazenamento e UX na integração de produto.
Não registrar payloads pessoais completos como log administrativo de produção.

## Validação e limitações

Na raiz do worktree:

```sh
python3 -m unittest discover -s tests -p test_parental_administrative_parameters.py -v
python3 -m unittest discover -s tests
```

**12 testes específicos e suíte completa de 805 testes PASS**.
[Saída arquivada](tests-output.txt) e [escopo/hashes](results.json).

Os 12 testes específicos cobrem valores mutados após plano/diálogo, imutabilidade,
ordenação/digest, add/remove wheel, entrada inválida, senha/foto indisponíveis,
permissão antes da resolução de grupos, GID trocado/ausente, rechecagem no limite
do adaptador, argumento literal, plano consumido após falha e wheel oculto com
flag administrativa falsa. Catálogo/flock reais no usuário do laboratório;
inventário/ledger/resolução de grupos simulados, adaptador registra argv.

Não houve nova VM, Polkit, usermod/gpasswd, mudança de usuários ou instalação
na estação. As evidências reais anteriores qualificam os seus componentes,
não automaticamente este novo envelope/adaptador. Produto parental continua
NO-GO; gates #2/#5, #6/#102, papéis, lifecycle, rollback, UX/ISO permanecem.

Próximo: qualificar o adaptador com efeito Unix real em conta fictícia na VM,
com identidade preservada, parâmetros selados e restauração verificada. Depois
conectar ao transporte/autorização reais, antes do UsersService de produto.
A instalação na máquina do mantenedor após conclusão está autorizada e integra
a entrega: ele criará conta local nova de criança/adolescente para testar.
Preservar conta principal e concluir criação/migração/recuperação e pacote antes
dessa instalação; não instalar as fixtures atuais como controle parental pronto.
