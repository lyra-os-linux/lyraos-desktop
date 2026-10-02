# Coordenador para retirada de acesso comum e disputa de operações

Continua o [gate após reboot](../parental-withdrawal-boot/README.md). Integra o
protocolo de retirada ao mesmo conjunto REQUIRED do [coordenador anterior](../parental-coordinator/README.md).
É código experimental de evidência, sem serviço/GUI/Polkit, NSS, enrollment,
publicação ou pacote. Guard C, withdrawal.py e coordenador anterior permanecem
inalterados; ordinary-coordinator.py compõe suas interfaces e requisitos.

## Sequência e fronteira

O plano e a retirada usam o backend root-only anterior: mesmo UID/operação/hash
de declaração/snapshot, autorização seguida de revalidação e lock exclusivo.
Primeiro grava marker/journal e retira declaração, conservando autoridade
negativa. Só depois verifica classificação bloqueada e REQUIRED inteiro:
classification/gdm/user-manager/ssh/system-units/dbus-activation/cron.

Ausência de adaptadores retorna UnsupportedProducer mesmo com zero processos.
Cada adaptador precisa confirmar inhibit, quiescent e inhibited; revoke só com
pedido explícito e após inhibit. Exceções/retorno não literalTrue mantêm recusa.
Revalida autoridade negativa depois dos callbacks. Sem método para publicar,
mutar Unix ou remover marker; CheckedWithinAdapterScope só descreve callbacks,
nunca autoriza concluir migração. Resultados positivos de adaptadores falsos
são APENAS testes de decisão/ordem, não cobertura real.

Target é referência imutável de UID/operação/hash da declaração verificada, não
PID/unidade/comando fornecido pelo cliente. Na retomada, autorização recebe
cópia do registro; não pode mudar a referência verificada usada pelos callbacks.
Autorização aqui é função de controlador confiável, NÃO Polkit. API/credenciais
reais, identificação NSS atual, revisões monotônicas globais e capacidades
continuam pendentes. Digests detectam snapshots diferentes, não rollback/ABA.

state só consulta o backend de retirada. Sem marcador, uma declaração existente
é ExistingOrdinaryProofNeedsVerification, não Ordinary comprovado. Com marker
ou journal é BlockedUntilAuthorizedRecovery. Isso integra autoridade NEGATIVA;
não implementa toda classificação persistente ou captura de todos os produtores.
Falhas de armazenamento/autorização/adaptador são recusas tipadas, sem fallback.

## Disputas nativas

Duas contas comuns já existentes: alvo1002 e controle1000. Nenhuma alteração de
contas/grupos/mapping. Ambos managers são admitidos inicialmente. Negação de
autorização não altera arquivos. Pedido autorizado retira a prova de Ordinary,
mas recusa cobertura ausente e conserva o manager antigo: lacuna de revogação.
Depois de parar explicitamente o manager fixture, ausência de atividade ainda
não satisfaz REQUIRED. Nova admissão do alvo nega por PAM224/causa exata.

Em três cenários independentes, dois PROCESSOS de controlador criam planos do
mesmo snapshot e encontram-se dentro da autorização, antes da mutação exclusiva.
O controlador principal confirma digests/hashes iguais e libera ambos. Exige
exatamente uma operação com UnsupportedProducer após retirada persistida; a
outra retorna Busy ou Conflict. Marker e journal devem conter APENAS a operação
vencedora. Retry do perdedor é Conflict; retry autorizado do vencedor permanece
bloqueado/UnsupportedProducer sem mudar conteúdo, revisão ou inodes dos locks.
Nova admissão negativa e PID/prova do controle comum preservados em cada cenário.

Por fim, enquanto o lock do alvo está EXCLUSIVO, um plano de outro UID continua
consultável e sua nova admissão PAM real continua possível. Autorização negada
para essa outra conta conserva sua declaração. Não se retiram duas contas
simultaneamente nem se qualificam todos os escalonamentos possíveis. Os resets
entre disputas são ações explícitas root da fixture com alvo parado; não são
recuperação, boot, método produtivo ou reenrollment automático.

## Verificação, limites e reversão

19 testes Python novos verificam decisões, ordem, autorização negada/falha,
revalidação, cobertura ausente, adaptação/quiescência/reativação e referência
imutável da retomada. Usam fake storage/adapters: não qualificam filesystem,
autorização, produtor ou concorrência real. A VM testa locks, escrita, processos
concorrentes e PAM com backend real de retirada e ZERO adaptadores produtivos.
Não substituir esses zeros por callbacksTrue para alegar conclusão da transição.

Helpers /root/ordinary-coordinator, guard histórico /root/withdrawal-pam-guard.c,
writer /root/barrier-writer.py. Exige root, dois marcadores de kernel e serial
lyra-admission-test. Executar nativo desacoplado com stdout/stderr/exit-status;
não depender de um comando foreground maior que120s. A fixture drena runtime/
logind entre admissões e usa processos/release-files próprios na autorização.
No finally, trabalhadores pendentes são encerrados apenas por referências Popen
criadas pelo ensaio; cleanup remove módulo/estado e restaura PAM original.
restore-check inspeciona independentemente bytes/modo/vendor/contas/managers/
processos/sessões e Permissive; VM desligada após inspeção. Helpers/root e backups
permanecem evidência. Não restaura todo arquivo home criado normalmente pelo
manager; não modifica host, receita, OBS ou ISO.

Não reexecuta boot; aproveita a evidência anterior somente para fontes compatíveis.
Sem powerloss, crash novo, falha fsync, rollback/update/downgrade, GDM/GNOME/login
completo ou reuso realNSS. Não qualifica cobertura produtiva de inibição/revogação,
quiescência geral, revisão monotônica, retenção/sinal/UX/Polkit ou candidataISO.
Outra operação pode concorrer durante autorização; snapshot obsoleto/busy é
recusado e não se abre uma geração. Não prometer resistência a root irrestrito.
Parental completo permanece NO-GO #6/#102.

Próximo: adaptadores reais de inibição/revogação e verificação de cobertura,
journal/revisão global e integração com ciclo de contas; nenhum Unix/publish
antes de qualificar esses requisitos. Não repetir indiscriminadamente fixtures
já verificadas nem interpretar resultado de callback como quiescência geral.

## Resultado de 02/10/2026

16 controles nativos PASS, processo rc0/stderr vazio; três disputas com exatamente
um UnsupportedProducer (operação gravada) e um Busy. Retry do perdedor produziu
Conflict, retry do vencedor continuou UnsupportedProducer com dados/revisão
inalterados. Zero processos alvo não permitiu dispensar cobertura. Um controle
reproduziu manager antigo ainda ativo: nenhuma prova de revogação/quiescência.
Outra conta comum manteve PID/prova nas três disputas e conseguiu nova admissão
com lock do alvo ocupado. 313 testes Python PASS, incluindo19novos. Verificador
offline e diffcheck PASS; limpeza/inspeção independente PASS, QEMU desligado rc0.
PAM/mode/vendor/passwd/group preservados, sem fixtures ativas. Sem warnings
backlog neste boot, auditoria completa ainda não comprovada. Nenhum host/receita/
OBS/ISO parental alterado; sem adaptadores produtivos qualificados/publicação.
