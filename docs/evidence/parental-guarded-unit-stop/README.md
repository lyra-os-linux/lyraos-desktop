# Parada de unidades com referência de processo — integração isolada

O adaptador SystemUnits anterior, o protocolo de máscaras com proprietário, a classificação negativa, o journal de operação e o backend Linux são reutilizados. `guard.py` acrescenta conferência das referências de processo antes de permitir os comandos do adaptador existente. O benefício é recusar a parada se a aprovação corresponder a uma execução que mudou enquanto a autorização estava em andamento.

## Resultado

638 testes Python passaram, incluindo 18 novos. A sexta execução nativa passou em 17 verificações, com cleanup0 e stderr vazio. As quatro tentativas falhas e a quinta execução com divergência no registro estão arquivadas, com fontes exatas/resultados/stderr. O controle parental integral continua NO-GO; #6/#102 abertas. Não há alteração no host, produto, RPM, OBS ou ISO.

A matriz reaproveita os helpers de owned-live units em novo diretório root e prefixo reservado. Apenas os caminhos da fixture são ajustados. Admissão e journal são reais na VM; autorização usa callbacks de fixture root, não diálogo/API Polkit de produção. UID1002 é alvo fictício e UID1000 é a conta comum independente; contas, grupos, senhas e mappings MAC não mudam. PAM e um módulo experimental são instalados somente na VM, testados com SELinux Enforcing e depois restaurados. PAM de produto/host permanece intacto.

## Ligação entre configuração, inibição e processo

A referência de configuração é capturada antes de instalar máscaras. Após daemon-reload, uma unidade ainda executando aparece como masked e deixa de expor sua configuração original; a identidade configurada não deve ser reconstruída desses campos vazios. `MaskedSources` conserva a referência anterior e exige fonte/executável/contas com os mesmos fingerprints, propriedades tipadas Id/Names/LoadState/FragmentPath/NeedDaemonReload, caminho exato `/etc/systemd/system/<nome>` e máscara verificada pelo CheckedMasks/OwnedInhibitions. O symlink efetivo /dev/null, namespace, inode, proprietário, digest e journal são conferidos pelo protocolo anterior. Nenhuma máscara é adotada ou reparada silenciosamente.

`GuardedExecution.batch()` fixa todos os processos principais de serviço antes do callback de autorização do SystemUnits. Os pins permanecem abertos durante a autorização. A população conhecida inteira, referências e máscaras são verificadas antes de cada comando, inclusive antes da primeira parada do timer. Só aceita `systemctl stop` de nomes fechados registrados; fora do lote uma parada é recusada. Daemon-reload é encaminhado somente fora do lote, pela fase de inibição já autorizada do adaptador anterior.

Depois de uma parada bem-sucedida, o pin original precisa ter saído e MainPID precisa ser inteiro0 para permitir o próximo efeito. Uma falha conserva efeitos parciais e estado negativo; não há unmask, liberação ou rollback permissivo. A saída do contexto fecha os pins inclusive se a autorização negar/falhar. A ordem timer → serviços e a conferência final de cgroups/UID/processos/mascaras permanecem no adaptador histórico. O núcleo anterior não foi reescrito.

## Casos reais

O lote contém dois serviços dedicados e um timer: plain usa o payload C de troca de executável, tick usa sleep. A definição guarded/PAM também existe no inventário fechado, mas fica inativa e fora deste lote; sua integração continua pendente. O catálogo confere todas as definições conhecidas, incluindo essa exclusão explícita. As máscaras registradas e owned routes são somente as três do lote; isso não certifica cobertura da família inteira.

- A retirada da admissão/logind conserva os produtores system.slice sem PAM; todos os payloads são fixados inicialmente.
- As referências são capturadas antes de preparar máscaras sob o mesmo owner negativo. A autorização testa locks EX livres, fora de locks de classificação/inventário/prova/ledger.
- Negação da revogação não executa comandos de parada nem muda processos/proprietários.
- Durante a autorização, SIGUSR1 faz o payload executar sleep conservando PID/ticks/pidfd. A conferência recusa antes de qualquer parada do timer ou serviços.
- Em outro callback, manutenção root explícita reinicia exclusivamente a fixture, recolocando o MESMO inode da máscara. O pin antigo saiu e o novo processo não é parado pelo pedido antigo.
- Um novo lote conferido permite que o SystemUnits original pare primeiro o timer e depois os dois serviços. Cgroups/alvo ficam vazios e pins antigos saíram. Serviço plain e manager da conta comum conservam PIDs; sua prova conserva bytes.
- Reiniciar os três nomes mascarados falha. Bytes/inodes do ledger e todos os arquivos da negação permanecem iguais.
- PAM do manager alvo nega com224 e registro causal; manager comum permanece ativo. O coordenador integral recusa famílias sem adaptadores, sem conceder cobertura global.

A manutenção root de reinício move temporariamente a máscara para backup, recarrega, para/inicia a unidade reservada e recoloca a máscara original. Não é fluxo público de reparo ou bypass disponível ao usuário supervisionado. O agendamento SIGUSR1/restart é escolhido pela fixture, não uma exploração exaustiva de interleavings.

## Tentativas e qualificação

1. O prefixo novo continha a palavra guarded, e a antiga condição por substring colocou PAMName em todos os serviços da fixture. O núcleo recusou corretamente; oito controles anteriores passaram e cleanup0. A condição foi corrigida para o sufixo exato do serviço guarded.
2. A referência masked esperava FragmentPath=/dev/null; esta base retorna o caminho do symlink em /etc/systemd/system. Dez controles passaram e cleanup0. O núcleo passou a exigir o caminho exato do namespace de máscaras registrado. A suíte completa foi rerodada depois dessa mudança e dos dois novos testes (638).
3. O observador de teste leu cmdline no instante transitório do exec e lançou UnsupportedRuntime dentro da autorização, convertido em AuthorizationFailure. Onze controles e cleanup0. O harness passou a aguardar a imagem sleep e argumentos estáveis, com timeout, antes da conferência do adaptador. Nenhuma recusa do backend foi relaxada.
4. Os casos reais e16controles passaram, mas a chamada final a OrdinaryCoordinator._check omitiu o argumento revoke. Cleanup0. A chamada foi corrigida para False; a quinta matriz passou17, mas o verificador encontrou a divergência de registro descrita abaixo.

5. A quinta matriz nativa passou17/rc0, mas um registro negativo guardou a mesma lista mutável de comandos. Paradas de um lote autorizado posterior apareceram naquele resultado final; o stdout original guardou corretamente a lista vazia no momento da recusa. O mesmo defeito de lista existe na quarta tentativa, que permanece passed=false por sua falha final. Todos os arquivos da quinta execução e sua restauração/desligamento estão em artifact-attempt-5. O harness passou a copiar a lista no registro; a sexta matriz foi repetida e sua serialização confere exatamente. Não é apresentada como falha do núcleo.

O campo scoped_guarded_stop_tested das tentativas falhas reflete a intenção do harness e não certifica seus resultados. Somente passed=true, retornos0, controles e fontes conferidas qualificam a matriz final. O núcleo/testes finais da suíte638 permaneceram iguais nas últimas quatro matrizes; mudanças posteriores foram somente do harness. Históricos de outros gates permanecem imutáveis.

## Preservação, risco e próximos gates

Quatro leitores independentes confirmaram PAM original/hash/mode e vendor, passwd/group, ausência de registro/roles/proofs/módulo/ledger/inventário/linger/unidades/mascaras/probe/backup, managers/runtime/sessões/processos alvo ausentes, unidade comum removida apenas no cleanup e arquivos das referências anteriores preservados. A VM voltou ao baseline Permissive, GDM parado e SSH desativado. QEMU das duas sessões48714 e71184 terminou exit0 após poweroff. Helpers/logs/binários de compilação root ficam em /root/guarded-unit-stop; não se afirma rollback de todo disco/cache nem auditoria completa de kernel.

Risco futuro: divergência ou falha de autorização/parada pode manter a conta bloqueada; a recuperação precisa conservar a política. Nesta entrega isolada, remover o commit local reverte fontes/testes e a fixture foi removida. Nenhum serviço compartilhado privilegiado foi parado. Não há proteção de produto entregue na máquina real.

Os checks não são snapshot atômico nem StopUnit condicionado por PID. Uma mudança entre a última leitura e a aceitação do comando, jobs enfileirados/resposta perdida, descendentes/threads, serviços compartilhados root, cold/no-MainPID, timers indiretos e população completa permanecem pendentes. A chamada autoriza efeito sobre a unidade fechada; não prova autoridade para arbitrariamente sinalizar um pidfd. Uma conta alvo/geração e seus recursos são definidos pela fábrica root/classificação/catalog/owner anteriores; estes objetos não são aceitos da GUI. full/global/production/shared-privileged/monotonic/power-loss permanecem false.

Próximo: qualificar trabalhos de parada e ativação concorrente entre a última conferência e o efeito upstream, com resultado incerto preservando bloqueio e observação completa do cgroup. Integrar a recuperação desse efeito ao journal existente. Cobertura completa, serviços root, persistência/antirollback, NSS, GDM/Polkit e ISO continuam gates separados, sem fingir que callbacks fechados os satisfazem.

## Verificação offline

Execute `python3 docs/evidence/parental-guarded-unit-stop/verify-evidence.py`. Confere hashes de todas as fontes, versões de cada tentativa, logs, resultados, controles, restauração e suíte. Testes foram executados na worktree, sem export limpo. Provenance é consistência local, sem assinatura independente.
