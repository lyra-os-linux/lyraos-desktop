# Primeiro gate do coordenador experimental — 02/10/2026

O mantenedor respondeu `continue` após a apresentação e o pedido de aprovação
do [contrato técnico](../../parental-lifecycle-recovery-contract.md). Isso
autoriza esta direção para implementação isolada, sem aprovar a ADR inteira,
aferição, retirada de supervisão, publicação ou os gates restantes.

Implementado um gate de transição com planos de snapshot, revalidação após a
autorização de fixture, barreira persistente antes de avaliar produtores e
reconciliação que não reinscreve uma conta bloqueada. Não existe aqui método
para publicar uma geração, alterar NSS ou tombstonar. O writer e guard V2
permanecem idênticos às evidências anteriores.

## Verificações

A versão final passou **10 controles nativos** na VM marcada e **286 testes
Python**, incluindo 16 testes novos do gate. Uma primeira versão passou nove
controles; a conferência foi ampliada para distinguir uma associação saudável
não verificada de uma associação realmente bloqueada. Os totais não somam as
rodadas. `result.json`, `cleanup.json`, `restored.json` e `provenance.json`
vinculam os resultados aos fontes finais. `verify-evidence.py` confere offline.

Com manager supervisionado real, contexto MAC exato e lease em sd-pam:
autorização negada não modifica arquivos; ausência de adaptadores retorna
UnsupportedProducer depois de persistir barreira/journal. A lease continua Busy.
Após encerrar o manager e drenar logind, o writer isolado já passa no teste de
lease exclusivo, mas o coordenador ainda retorna UnsupportedProducer. Assim,
leases vazias não são usadas como prova de cobertura. Novo manager é negado
por PAM224 com causa exata; a conta comum conserva o PID. Reconciliação deixa
recovering/barreira e não permite plano de transição sem recuperação separada.

A reconciliação de associação saudável não cria bloqueio nem declara o
controle aplicado: retorna ExistingAssociationNeedsVerification. Essa diferença
é importante para a consulta de saúde futura do serviço.

## Especificação dos adaptadores e próximo gate

O conjunto obrigatório é fechado no coordenador: classification, gdm,
user-manager, ssh, system-units, dbus-activation e cron. O cliente não escolhe
um subconjunto. Cada adaptador terá operações internas inhibit, revoke,
quiescent e inhibited. Inibição de todos antecede qualquer revogação; após
quiescência, a inibição é conferida novamente, antes de repetir o teste de lease.
Falha, retorno desconhecido ou cobertura ausente conserva a barreira. Revogação
não é implícita: deve integrar a autorização do efeito solicitado.

| Adaptador | Identificação confiável necessária | Gate ainda pendente |
|---|---|---|
| classification | Fonte persistente que identifica a associação, distinta do processo Vega | Perda/corrupção/identidade parcial nunca vira Ordinary; preservar contas comuns por fonte independente qualificada |
| gdm | Worker, sessão e conversa vinculados à geração | Handles antigos, bloqueio antes de open, login/logout/desbloqueio GNOME completos |
| user-manager | Unit/cgroup, sd-pam e classe manager do logind | Inibição durável antes de drenar manager/runtime, incluindo lingering e corridas |
| ssh | Transportes/monitores/PAM e geração | Encerrar transportes antigos e impedir reuso de mux/autenticações pendentes |
| system-units | Unidades e timers atribuídos à conta, com versões conferidas | Inibir ativação e novas unidades User=, não apenas parar uma fixture |
| dbus-activation | Rotas de ativação e donos de nomes, incluindo broker→systemd | Inibir rotas/nome antigo sem encerrar o barramento compartilhado |
| cron | Tabelas/job/payload e monitor que retém lease | Impedir rodada nova e revogar árvore atribuída sem sinalizar root genérico |

Não há adaptadores reais cadastrados nesta versão. O ensaio nativo comprova
recusas por cobertura ausente, não uma transição completa aprovada. Os testes
positivos usam objetos sintéticos e seu resultado CheckedWithinAdapterScope
não é prontidão da máquina. A próxima entrega precisa ligar classificação e
inibição a fontes upstream reais e demonstrar as pós-condições acima. Onde
não houver cobertura, manter a operação indisponível; não preencher o método
com um retorno True nem reduzir REQUIRED para fazer a transição passar.

## Limites e segurança de reprodução

`classify()` é somente um modelo de decisão com rosters confiáveis de teste:
colisão parcial mantém o caminho bloqueado e ausência de vínculo retorna
Unknown. Não é classificação persistente, não integra PAM/NSS/MAC e não resolve
remoção de configuração nem recriação idêntica por root. Não foi testada como
proteção da conta inteira.

Plan usa digest de snapshot para detectar plano obsoleto; não implementa revisão
monotônica, idempotência durável, API D-Bus ou Polkit. O controlador deve
serializar mutações. Corridas entre coordenadores/escritores, cancelamento real
de Polkit, desconexão GUI, deadlines de adaptadores e crash do coordenador
precisam implementação/ensaios. O journal durável usado é apenas o writer V2.
O gate não pode ser copiado como um serviço de produção.

A fixture instala temporariamente o módulo/PAM systemd-user e o registro na
VM descartável serial lyra-admission-test com os dois marcadores de kernel.
`native.py` restaura pelo `cleanup.py` mesmo se uma verificação falhar;
`restore-check.py` inspeciona independentemente PAM/modes/vendor/passwd/group,
managers/sessões/processos, lingering e SELinux. Helpers/resultados/backup em
/root permanecem só como evidência. A VM foi desligada após restauração.
Nenhum host, receita, pacote OBS ou ISO foi alterado. O diretório dos helpers
precisa existir antes de usar host.py push; a primeira tentativa de transferência
falhou sem esse diretório e não executou instalação da fixture.

Reprodução: transferir os cinco fontes para /root/registry-coordinator/, mantendo
barrier-writer.py e barrier-pam-guard.c das etapas anteriores. Rodar native.py,
restore-check.py, recolher JSON e desligar a VM. Os testes locais estão em
../../../tests/test_parental_coordinator.py. Proteção parental completa continua
NO-GO (#6/#102); o contrato aprovado não fecha classificação ou inibição geral.
