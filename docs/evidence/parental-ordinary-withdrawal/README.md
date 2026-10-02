# Retirada durável da autorização comum — ensaio isolado

Continua a [declaração independente](../parental-ordinary-attestation/README.md).
Ela isolou a conta comum de falhas parentais, mas uma declaração antiga com MAC
comum ainda poderia conceder acesso. Esta variante implementa somente a retirada
de novas admissões; não cria contas, aplica supervisão, publica gerações nem
conclui migração. Código exclusivo de evidência, não pacote/PAM produtivo.

## Ordem e autoridade negativa

Todos os leitores de classificação usam um lock estável root0600 por UID no
diretório root0700 de declarações. O PAM abre esse lock sem criação e tenta
LOCK_SH|LOCK_NB durante o snapshot de admissão. O controlador tenta LOCK_EX|LOCK_NB
para a mudança; se houver leitor, retorna Busy antes de qualquer efeito. Se
houver escritor, uma nova admissão é recusada. O lock é fechado ao terminar o
snapshot PAM, não acompanha a vida de um processo já admitido. Não trocar seu
inode. A lease da geração supervisionada continua separada e inalterada.

O plano contém UID, operação aleatória, hash do conteúdo da declaração e digest
do snapshot. Revalida antes e depois da autorização e sob lock exclusivo.
Identidade/geração da declaração são conferidas pelo decoder; autorização é
callback de controlador fixture, NÃO Polkit nem transporte autenticado. Plano
obsoleto retorna Conflict. Esse digest NÃO revisão monotônica do produto.

A operação grava e sincroniza `.deny-UID` antes de qualquer retirada; depois
grava journal revision1/blocked, apaga a declaração e sincroniza o diretório,
grava journal revision2/retired. `_atomic` histórico executa fsync/rename/fsync.
O PAM nega por presença de qualquer marker ou journal, inclusive arquivo
corrompido, symlink ou modo inseguro. Não parseia o journal para escolher Ordinary.
Se o marker sumir mas o journal existir, mantém a negação. Sem lock confiável,
recusa admissão. Nenhum desses arquivos é criado pelo leitor.

`inspect` só consulta: blocked continua BlockedUntilAuthorizedRecovery, não
regenera declaração, não enrolla e não remove barreira. Falha de leitura retorna
erro, nunca Ordinary. `resume` requer autorização explícita, marker confiável,
mesma operação/hash e snapshot revalidado; pode terminar a retirada interrompida
sem reabrir. A mesma operação permanece revision2/retired em retries. Outra
operação ou declaração substituta divergente retorna Conflict, conservando
bloqueio. Marker ausente/journal órfão exige RecoveryRequired; não tentar consertar
recriando Ordinary. Journal inválido não é ignorado na retomada.

Esta revision1→2 pertence a UMA retirada pendente. Não é contador monotônico
entre operações nem impede rollback completo do armazenamento por root/backup.
Não há método para concluir supervisão ou remover markers. Root irrestrito é
autoridade confiável; atualização/downgrade com PAM antigo e rollback de ambas
as fontes ainda precisam de qualificação. Não prometer resistência a root.

## Matriz

| Caso | Critério observado |
|---|---|
| Baselines | Managers comum e supervisionado admitidos com contexto correto |
| Autorização negada | Sem marker, declaração preservada e comum ainda admitida |
| Plano com declaração modificada | Conflict antes de publicar marker |
| Leitor concorrente | Busy do controlador sem marker |
| Escritor concorrente | Nova admissão negada por PAM224 |
| Interrupção após marker/journal/unlink/journal final | Processo termina91, marker persistente e nova admissão negada |
| Inspeção e retry após interrupção | Consulta sem efeito, autorização negada sem retirada adicional, retomada autorizada só retira; mesma operação idempotente |
| Declaração antiga restaurada | Negação preservada por marker; retry autorizado retira outra vez |
| Marker ausente, journal existente/corrompido | Nova admissão negada, sem fallback |
| Outro manager supervisionado | PID/contexto preservados durante a matriz |
| Manager comum admitido antes da retirada | PID permanece: lacuna de revogação/sem prova de quiescência |

Os processos de controlador são interrompidos por os._exit(91) DEPOIS de fsync
nas quatro fronteiras instrumentadas. Prova persistência entre processos e
retomadas na mesma VM/mesmo boot; NÃO queda de energia nem reinício de kernel.
Os controles negativos exigem MainPID0/status224 e causa exata deste módulo
após cursor de journal. Admissões verificam PID e contexto; runtime/logind são
drenados após cada tentativa antes da próxima.

O teste não usa dois coordenadores mutando a mesma conta simultaneamente; os
locks reais leitor/escritor e mudança durante o plano não qualificam toda a
concorrência do lifecycle. Não testa segunda conta comum intacta durante a
retirada: preserva o outro manager supervisionado existente. Não extrapolar
essa evidência para todas as contas/produtores.

## Reprodução, limites e reversão

VM com AMBOS marcadores de kernel e serial lyra-admission-test. Helpers em
/root/ordinary-withdrawal, C /root/withdrawal-pam-guard.c; writer V2 histórico
não alterado. Executar nativo desacoplado registrando stdout/stderr/exit-status,
pois o agente limita cada comando a120s. Entre os quatro cenários, o controlador
root restaura explicitamente uma baseline com managers alvo parados; esse reset
é parte do experimento, NÃO API de recuperação nem boot automático.

PAM vendor e contas locais fictícias já existentes. Nenhuma mutação NSS, mapping
SELinux ou pacote novo. Fixture MAC anterior da VM, não política stock de ISO.
O formato de journal aceita somente blocked1/retired2, campos fechados e IDs
exatos; nega duplicação JSON. Oito testes Python verificam schema/refusals;
segurança de arquivos/locks/crash/admissão é verificada nativamente na VM.

Retirada de nova admissão não encerra payloads/sessões/managers antigos, não
inibe SSH/cron/D-Bus/unidades sem este PAM, não comprova quiescência. Produtores
reais obrigatórios e a autoridade de revogação permanecem gates anteriores à
mutação Unix ou publicação. A declaração de Ordinary não deve ser recriada no
boot/reparo e a supervisão não deve ser publicada com essa autoridade ativa.
Falta integrar esse protocolo ao coordenador, revisão/journal global, boot real,
falhas antes do fsync, duas contas comuns, backup/update/downgrade, lifecycle
NSS/reusoIDs, reparo da mesma política, Polkit/UX e candidata ISO.

Reversão exclusiva do ensaio: native.py remove declarações/markers/journals/locks,
restaura PAM original e executa cleanup.py. restore-check.py verifica de forma
independente bytes/modo PAM, vendor, contas, processos/sessões/managers e SELinux.
Helpers/backup/resultados root permanecem só como evidência. Nenhum host/receita/
OBS/ISO alterado. Parental completo continua NO-GO, sem integração produtiva.

## Resultado de 02/10/2026

33 controles nativos concluídos, processo rc0/stderr vazio; quatro interrupções
91, novas admissões negadas, retomadas sem liberação, restauração de declaração
antiga bloqueada. Um controle reproduz manager antigo ainda ativo: lacuna de
revogação, sem quiescência. 294 testes Python PASS, incluindo8novos; verificador
offline confere hashes/causas/contextos/limites. Limpeza e inspeção independente
PASS, VM desligada com QEMUrc0. PAM/mode/vendor/passwd/group preservados; sem
módulo/índices/locks/markers/journals/linger/managers/processos/sessões de fixture.
Auditlost1–4: não inventárioAVCcompleto. Sem host/receita/OBS/ISO alterado.
