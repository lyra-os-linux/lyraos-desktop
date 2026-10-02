# Índice persistente de papéis no PAM — ensaio isolado

Continuação do [gate do coordenador](../parental-coordinator/README.md). A
variante C é derivada do guard V2; o writer anterior permanece inalterado.
O módulo recebe zero argumentos de associação e consulta um índice root-only
em /var/lib/lyra-parental-roles-test/role-index. Assim o vínculo deixa de depender
de argumentos estáticos account= e de um skip por tupla Unix no override PAM.
O índice não é arquivo do Vega e é separado do registro de transações.

O índice exige schema e framing próprios, tamanho limitado, arquivos regulares
root-only sem symlinks/hardlinks, diretório protegido, tupla completa, geração
válida e ausência de colisões. Só possui papéis explícitos active(supervisionado)
e ordinary. Ausência de vínculo ou identidade parcial nunca vira Ordinary.
Uma conta explicitamente comum só segue essa rota quando o contexto pendente
SELinux também é unconfined; marcar a supervisionada como ordinary não basta
para mudar a rota MAC. A supervisionada mantém exigências de geração ativa,
barreira ausente, lease, Enforcing e contexto exato do guard V2.

## Cenários e critério

O ensaio usa managers systemd-user reais e o PAM vendor, sem autenticação de
login nem alteração real de nomes/UIDs/grupos. Cada negação exige MainPID0,
status224/PAM e a causa exata desta variante após cursor de journal; cada
admissão exige PID ativo e contexto correto. Depois de cada tentativa, o manager,
runtime e registro logind são drenados antes do próximo caso.

| Falha/controlador root da VM | Supervisionada | Conta comum |
|---|---|---|
| Índice íntegro e geração ativa | Admitida | Admitida |
| Registro parental ausente/corrompido | Negada | Admitida pelo índice independente |
| Entrada supervisionada ausente do índice | Unknown/negada | Admitida pela entrada explícita |
| Índice ausente/corrompido/modo inseguro | Negada | Negada: lacuna de disponibilidade |
| Supervisionada marcada ordinary com MAC ainda supervisionado | Negada | Admitida |
| Tupla parcial no índice (GID diferente) | Negada | Admitida |
| Arquivos restaurados após injeções | Admitida | Admitida |

Os controles de indisponibilidade da conta comum reproduzem uma lacuna, não
satisfazem o requisito de preservá-la em falhas do classificador. Não aprovar
esta variante para a estação/ISO nem apresentar a matriz como proteção pronta.
O próximo gate deve qualificar a fonte MAC/persistente independente para a rota
comum e o comportamento diante de falha do classificador, sem fallback que
converta Unknown em Ordinary. Não remover o módulo ou permitir todos os
usuários por ausência do índice para fazer a disponibilidade passar.

## Reprodução e limites

Executar exclusivamente na VM com os dois marcadores de kernel e serial
lyra-admission-test. Helpers em /root/role-index/, C em /root/roles-pam-guard.c,
writer V2 em /root/barrier-writer.py. O controlador grava o índice por temporário
exclusivo, fsync/rename/fsync de diretório. O índice e registro não constituem
uma publicação atômica entre si: criação/migração de produto precisará do
coordenador e sua barreira; a fixture só injeta alterações com managers parados.
Não inserir este código em pacote ou pilha PAM real.

Não testa GDM/GNOME completo, SSH/cron/outros produtores, boot, reautenticação,
remoção real de conta ou recriação de IDs. Não detecta alteração externa de root
que recrie identidade idêntica. Fonte de papéis e autorização para escrever
índice/mapeamento continuam sujeitas ao contrato; isto não implementa backend,
Polkit, revisão monotônica ou migração. A política MAC anterior da VM é de
fixture, não a da candidata. Logs de audit não são inventário completo.

`native.py` remove índice temporário e executa `cleanup.py` em finally;
`restore-check.py` inspeciona independentemente os arquivos, managers/sessões,
processos e estado SELinux. Helpers/backup/resultados em /root podem permanecer
como evidência. A VM é desligada após inspeção; sem alterações no host, receita,
OBS ou ISO. Os JSON e provenance.json registram resultados e hashes;
verify-evidence.py faz conferência offline sem alterar o sistema.

## Integridade do procedimento

A primeira execução excedeu o limite de 120 segundos do agente de comandos;
foi interrompida, restaurada e não conta como resultado. A segunda, já em
processo desacoplado, chegou a 18 controles, mas falhou ao readmitir a
supervisionada no controle final. O harness restaurava um arquivo removido com
`write_bytes`, sem reaplicar `0600`: os casos posteriores poderiam receber
negações pela permissão residual, em vez da falha pretendida. Essa rodada não
qualifica nenhum cenário. `failed-result.json`, `failed-cleanup.json`,
`failed-restored.json` e `failed-stderr.log` preservam o diagnóstico e a
restauração independente bem-sucedida. `failed-native.py` preserva o harness
original, conferido pelo hash capturado nessa execução.

A correção usa o writer atômico root-only anterior, aplica restorecon e verifica
bytes e modo `0600` antes de cada nova injeção e depois da restauração. A rodada
final usa processo desacoplado com código de saída gravado, sem aumentar o
limite do agente. Os arquivos `result.json` e `provenance.json` identificam
exclusivamente essa rodada; não somar as tentativas preliminares aos controles.

## Resultado de 02/10/2026

Rodada final: **20 controles nativos concluídos**, processo retornou **0**, sem
stderr; limpeza e inspeção independente PASS, QEMU desligado com retorno 0.
Inclui a reprodução de três falhas de disponibilidade do classificador, não
aprovação dessas falhas. A suíte Python existente passou **286 testes** nesta
etapa; não há novos testes Python de parser C e não se somam testes de outras
rodadas. Verificação offline confere hashes, causas PAM, contextos e restauração.
Audit reportou perda de eventos (1–7): não declarar inventário AVC completo.

Benefício limitado: retirar a associação estática do override PAM e demonstrar
papéis persistentes separados do estado transacional. Risco demonstrado: falha
global do índice bloqueia contas comuns. Reversão do ensaio remove o módulo e
os dois diretórios e restaura bytes/modo do override PAM. Não promover nem
integrar à candidata antes de qualificar uma classificação independente que
preserve a rota comum sem reclassificar identidades desconhecidas.
