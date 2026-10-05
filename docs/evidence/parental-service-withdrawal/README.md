# Ligação experimental entre planejamento e retirada de admissão

[binding.py](binding.py) conecta o [planejador](../parental-service-classifier/README.md)
aos modelos existentes [Operations](../parental-operation-journal/README.md) e
[Withdrawal](../parental-ordinary-withdrawal/README.md). Não altera seus arquivos,
schemas, fases ou writer. Não é integração ao vegad, D-Bus, Polkit ou PAM real.
O [contrato de serviço](../../parental-service-integration-contract.md) e os
respectivos gates continuam aplicáveis.

## Garantias do componente isolado

Planejamento server-side sela também a prova positiva e o inventário registrado.
O identificador gerado pelo servidor é a operação do journal histórico.
Execute recebe somente ID de plano, encontra o plano de operação guardado no
servidor, revalida remetente/TTL/capacidade/catálogo e chama Operations.begin.
O controlador do laboratório serializa as chamadas. Chamadas reentrantes de
execução/retomada da mesma associação recebem Busy; planejamento de outra conta
pode avançar durante o diálogo. Não há promessa de concorrência multithread.

BoundInventory mantém a ordem catálogo SH -> inventário -> withdrawal. O lock
SH do catálogo fica retido durante a conferência final e publicação do intent,
mas todos os locks são liberados antes de solicitar autorização. O callback
consegue adquirir EX no lock real do catálogo durante o diálogo. O primeiro
efeito histórico continua sendo o marcador negativo; a publicação desse
marcador impede EX concorrente no catálogo no ensaio. Escritores de catálogo
precisam cooperar com o mesmo inode estável; root irrestrito continua confiável.

A revisão/digest do inventário original e associação/geração/revisão/digest do
catálogo compõem o inventory_digest persistido pelo journal. Isso permite uma
nova instância conferir o mesmo vínculo ao retomar, sem reconstruir um plano
em memória. É composição de fixture; não define migração de journal de produto.
Um journal antigo com digest sem essa composição será recusado por conflito.
Nenhum hash no mesmo snapshot oferece autoridade monotônica/antirollback.

Antes do primeiro efeito, Operations revalida prova e inventário sob locks;
BoundInventory revalida também catálogo, identidade e capacidade do remetente.
O callback não altera o owner selado: recebe uma cópia. Mudança de catálogo,
TTL, capacidade ou remetente detectada dentro do callback aborta sem escrita,
reportada como AuthorizationFailure pelo wrapper histórico. Prova/inventário
alterados depois da autorização retornam Conflict antes do marcador.

Após bloqueio persistido, perda de capacidade não apaga o marcador nem restaura
prova. Resume pede autorização nova, confere registro canônico/identidade/vínculo
persistido e conclui apenas retirada negativa. Novo processo não recupera planos
como autoridade: Execute de ID antigo é negado; Resume usa a operação persistida.
Retry concluído exige autorização nova e não regrava o ledger.

inspect_admission é um diagnóstico do laboratório para conta ordinary com
capacidade explícita: confere catálogo/inventário/prova sob locks, e presença
de marcador, journal ou owner nega mesmo com registro positivo no catálogo.
Ele **não substitui** um leitor PAM ou guard de UsersService. O classificador
anterior isolado ainda não consulta esse overlay por conta própria.

## Validação e limites

Executar na raiz do worktree:

```sh
python3 -m unittest discover -s tests -p test_parental_service_withdrawal.py -v
python3 -m unittest discover -s tests
```

Resultado: **14 testes específicos e 780 na suíte completa PASS**.
[Saída arquivada](tests-output.txt) e [escopo/hashes](results.json) desta execução.

Os 14 testes específicos exercitam autorização nova fora dos locks, negação e
cancelamento/erro, mutação do payload, TTL/remetente revogados, conflitos de
catálogo/prova/inventário, SH retido no primeiro efeito, bloqueio preservado
após falha, nova instância e retry, checkpoints do owner histórico, ausência
de marcador, operação alheia, geração trocada e conta comum vizinha.

Catálogo/permissões e flock são reais em diretórios temporários com proprietário
explicitamente definido como o usuário do laboratório. Inventário, ledger e
suas escritas são **em memória**; checkpoints usam exceção, não crash de processo
nem corte de VM. As evidências históricas de fsync/VM qualificam o writer no
escopo original, não esta composição nova. Não extrapolar esses 14 testes para
qualificação do armazenamento integrado, D-Bus/Polkit, produtores ou ISO.

Não implementa publicação do catálogo, revisão confiável/rollback, supervisão,
quiescência, execução StopUnit, mutação Unix ou enrollment. Ordinary continua
sendo a única classe suportada para retirada neste componente. Produto NO-GO,
#6/#102 e ADR final abertos. Nenhum pacote ou host foi alterado.

Próximo: qualificar a composição com armazenamento/locks reais no laboratório
antes de conectar transporte e autorização reais. Reutilizar o writer e provas
existentes quando compatíveis; não reiniciar toda a série de cortes de VM.
Depois, transportar o contrato para o serviço exige os gates #2/#5, guard de
mutações administrativas e classificação/recuperação/rollback de produto.
