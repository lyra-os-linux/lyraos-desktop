# Classificação e planejamento isolados do serviço parental

Implementação experimental read-only em [classifier.py](classifier.py), derivada
do [contrato de integração](../../parental-service-integration-contract.md).
Não é serviço de produto nem módulo instalado no vegad. Nenhum formato aqui
está aprovado como ABI ou armazenamento de produção.

## Comportamento implementado

O parser exige schema fechado, revisão local, associação e geração opacas,
identidade Unix exata, classe explícita, estado, operação e digests. Limites:
64 KiB, 128 contas e 32 adaptadores por registro. Rejeita campos/nomes duplicados,
colisões de UID/nome/associação/geração, tipos incorretos e JSON não finito.
O snapshot retornado é imutável. Tombstone e reutilização de UID no mesmo
catálogo são deliberadamente recusados: migração/recriação não foi implementada.

O leitor consulta somente catalog.json com lock SH não bloqueante no inode
pré-existente catalog.lock. Valida diretório, arquivos regulares, proprietário,
0600, ausência de symlink/hardlink e tamanho; não cria arquivo/lock nem adota
um temporário quando falta o nome canônico. O proprietário padrão é root; os
testes usam explicitamente o UID do laboratório em diretório temporário.
Isso testa permissões e leitura, sem alegar um ensaio com arquivos de root.
Ancestrais do diretório e escritores cooperativos são confiáveis; escritor
precisa adquirir EX no mesmo inode. O modelo não fornece esse escritor.

Ordinary exige registro positivo e observação NSS exata. Barreira ou estado
não ativo bloqueia antes da admissão. Supervised exige o conjunto obrigatório
fornecido pelo controlador e observação dos adaptadores com geração/política/
digests idênticos; o campo armazenado sozinho não basta. Esse resultado é
somente elegibilidade da fixture, não prova de enforcement ou login real.

Planner usa adaptadores confiáveis de transporte/capacidade/identidade, não
UID alegado pela GUI. Verifica capacidade antes de consultar alvo conhecido ou
inexistente. Plano é objeto imutável criado pelo servidor, vinculado a remetente
único, UID observado, associação, geração, revisão e digest do catálogo.
Prazo experimental: 60 segundos pelo relógio monotônico injetado. Até 128 planos
vivos; expirados são descartados no planejamento seguinte. Nova instância não
reconstrói planos, e ID de plano não é credencial. Revalidação confere novamente
capacidade/remetente, catálogo e identidade; revogação durante leitura também
é recusada. Nenhuma dessas consultas escreve no catálogo.

Planejamento de retirada suporta somente ordinary nesta etapa, retomando o
escopo das provas anteriores. Supervised retorna UnsupportedOperation. Não
remove criação/migração dos requisitos finais. validate **não executa** nem
autoriza uma retirada: publicação negativa, Operations/Withdrawal e Polkit
real ainda não estão conectados. Não existem boot hooks, PAM ou guard de
UsersService instalados por este código.

## Validação reproduzível

Na raiz do worktree:

```sh
python3 -m unittest discover -s tests -p test_parental_service_classifier.py -v
python3 -m unittest discover -s tests
```

Resultado desta execução: **22 testes específicos e 766 na suíte completa PASS**.
Saída arquivada em [tests-output.txt](tests-output.txt); escopo e hashes em
[results.json](results.json).

Os 22 testes específicos cobrem negação por estados/ausência/corrupção, conta
vizinha ordinária, identidade divergente, observação dos adaptadores, parsing,
colisões, imutabilidade, inode/permissões/bytes preservados, lock EX ocupado,
symlink/hardlink/FIFO, temporário órfão, remetente perdido/alheio, capacidade
revogada durante leitura, revisão alterada, TTL e limite de planos.

## Limites e próxima etapa

Persistência aqui significa **leitura de um catálogo preexistente**, sem
protocolo de publicação ou recuperação global. Revisões e hashes não protegem
contra rollback de snapshot. Barreiras estão representadas dentro do catálogo;
a conexão com marcadores independentes das fixtures antigas não existe.
Resolução de remetente/NSS e observação de adaptadores são callbacks confiáveis;
não é D-Bus, Polkit, inventário completo ou certificação de quiescência.

Próximo componente isolado: ligar plano/revalidação à retirada negativa existente,
com autorização nova fora dos locks e rechecagem de bindings no primeiro efeito.
Antes de produto, resolver classificação/persistência/rollback, guard de métodos
administrativos e transporte/Polkit reais. #6/#102 e ADR final continuam abertos.
Controle parental integral NO-GO. Não executar este código como instalador ou
adicionar ao RPM. Reversão dos testes: remoção dos diretórios temporários;
nenhuma modificação em contas, serviços, VM ou na estação.
