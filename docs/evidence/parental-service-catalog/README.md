# Declarações de serviços e duplicidade — 04/10/2026

8 controles na VM e 586 testes Python PASS (16 novos). Primeira execução nativa,
rc0/stderr vazio. VM restaurada/desligada; produto/host/PAM/receitas/RPM/OBS/ISO
intactos. #6/#102 abertas; controle parental integral NO-GO.

`catalog.py` decodifica um subconjunto conservador de [D-BUS Service] em tipos
imutáveis: caminho/hash, Name, identidade local declarada, argumentos simples e
referência SystemdService. UTF-8/tamanho até 8KiB, nome igual ao arquivo, uma seção,
campos conhecidos não repetidos, identidade literal conferida pelo resolvedor
local da fábrica e argumentos sem quoting/escape/shell ou executável relativo.
Não executa comandos, expande variáveis ou aceita sintaxe desconhecida. As
restrições são deliberadas; não é implementação completa do parser upstream.

O catálogo recusa qualquer nome repetido, mesmo com conteúdo idêntico em duas
raízes. Não escolhe o primeiro/último nem presume precedência pela ordem da lista.
Duplicidade exige qualificação/reconciliação explícita. require_adapters exige
vínculo interno da fábrica para cada declaração; User=root não dispensa adaptador.
O retorno limitado é CheckedDeclarationsWithinBoundAdapters, sem cobertura global,
Active, liberação de barreira ou API de capabilities/caminhos do cliente.

A VM usa as três raízes reais anteriormente observadas, SourceSet histórico,
leitura root por descritores e hashes vinculados ao snapshot. Resolução de usuário
consulta bytes de /etc/passwd e /etc/group, recusa resultados ausentes/ambíguos e
confere sua estabilidade; não recorre a NSS remoto. O inventário instalado contém
13 declarações: 12 com SystemdService e uma somente Exec (systemd1).

Foram consultados campos reais de systemctl show, sem iniciar as unidades:
Id, LoadState, User/Group, DynamicUser, PAMName, FragmentPath e DropInPaths.
Todos os 12 resultados estavam loaded. Duas divergências confirmam por que
User do arquivo D-Bus não pode substituir a consulta da unidade:

| Serviço | User na definição D-Bus | User observado na unidade |
|---|---|---|
| PolicyKit1 | root | polkitd |
| timesync1 | root | systemd-timesync |

User vazio foi registrado como campo vazio; a comparação diagnóstica usa root
como padrão da unidade. Esses campos não provam UID do processo, execução real,
credenciais dinâmicas, descendentes ou capacidade de trocar usuário. Não foram
vinculados fontes/drop-ins/ExecStart/binários da unidade nem política de chamada
D-Bus. Serviços compartilhados root também podem mediar criação de processos para
outras contas; nenhuma declaração foi excluída do gate por sua identidade.

Controles nativos recusam ausência de adaptadores para as 13 declarações e para
uma declaração reservada ordinaryuser/UID1002. Definições de fixture com mesmo
Name são criadas em /usr/share e /usr/local/share: conteúdo idêntico ou Exec
divergente gera AmbiguousProducerCatalog. Campo FutureActivation desconhecido gera
UnsupportedServiceDefinition. Não é ativado nenhum nome, iniciado payload/unidade,
revogado processo ou alterada conta. As definições reservadas são removidas,
ReloadConfig retorna à lista original de nomes e o broker457 mantém PID.

Os 16 testes novos cobrem esquema, declaração systemd/Exec, duplicidade/campos,
identidade local, arquivo-nome divergente, quoting/shell/caminho relativo,
argumentos simples, limites e exigência de adaptadores inclusive para root.
Os callbacks de binding em testes são internos/sintéticos, não qualificação de
produtores. A matriz nativa não instala adaptadores permissivos para passar o gate.

Restauração independente confere hashes das 13 definições e passwd/group/PAM,
alias /lib, ausência das raízes opcionais/definição reservada/lock e brokerPID.
PAM compara a evidência original da etapa SourceSet. Helpers/logs root ficam na
VM; não é rollback de todo disco nem auditoria completa de processos/kernel.
Nenhum RPM instalado. Suíte no worktree, sem alegação de export limpo.

Benefício: elimina aceite silencioso de definições ambíguas ou fontes sem adaptador
e distingue declaração D-Bus da unidade observada. Risco: sintaxe legítima fora do
subconjunto ou overrides intencionais serão recusados. Por isso é protótipo isolado,
com reversão já executada pela remoção dos caminhos reservados/reload.

Próximo: vincular referências SystemdService às unidades/fontes/drop-ins e à
identidade de execução efetiva, recusando configurações dinâmicas/não qualificadas.
Qualificar Exec direto separadamente. Depois verificar inibição das rotas e
serviços compartilhados; este catálogo não resolve precedência upstream, todos
os produtores, política carregada ou cobertura completa do controle parental.

Verificação offline: `python3 docs/evidence/parental-service-catalog/verify-evidence.py`.
