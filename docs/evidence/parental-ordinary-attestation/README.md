# Declaração independente para contas comuns — ensaio isolado

Continua o [índice de papéis](../parental-role-index/README.md), que bloqueava
ambas as contas quando o índice parental inteiro falhava. A nova variante só
altera código de evidência: não instalar na estação, PAM real, pacote ou ISO.

O contexto pendente unconfined não prova uma classificação explícita: o
[libselinux upstream](https://github.com/SELinuxProject/selinux/blob/main/libselinux/src/seusers.c)
resolve também grupos e `__default__` e não distingue essa origem na resposta
de getseuserbyname. Portanto, usar apenas esse contexto como liberação tornaria
uma identidade desconhecida candidata a Ordinary. Não se altera o mapeamento
SELinux upstream neste ensaio.

## Variante e fronteira

Uma declaração positiva por UID em `/var/lib/lyra-ordinary-attestation-test/`
contém exatamente uma linha Ordinary com nome/UID/GID/grupo/geração. Reutiliza
somente o formato experimental LYRA-ROLE-INDEX-V1. Diretório root0700 e arquivo
root0600, regular sem symlink/hardlink, tamanho limitado e parsing estrito. O
leitor não cria arquivos. O writer V2 histórico publica por temporário exclusivo,
fsync/rename/fsync e aplica restorecon. O arquivo parental continua independente.

A rota comum exige essa declaração íntegra, tupla NSS completa, Enforcing e
contexto pendente `unconfined_u:unconfined_r:unconfined_t:`. Não consultar o índice
parental para conceder essa rota é uma decisão deste protótipo, condicionada à
correção da declaração independente. Uma linha ordinary no índice parental,
a ausência do índice ou o contexto sozinho nunca concedem acesso. Sem prova
comum válida, a rota supervisionada conserva os requisitos anteriores de
identidade/generation/barreira/lease/MAC; Unknown continua negado.

**Não é uma fonte infalível nem uma transação de cadastro.** Perder/corromper a
própria declaração comum ainda bloqueia essa conta; não há disponibilidade se
todas as fontes de identidade falharem. O benefício proposto é isolar a conta
comum de falhas exclusivamente no estado parental. Enforcing é pré-condição;
não qualifica conta comum em Permissive, SELinux desligado ou outra política.

Ordinary descreve somente uma rota técnica de conta; não é prova de idade nem
autorização para retirar supervisão.

A declaração independente é uma autoridade positiva, não um cache regenerável
por ausência do índice. Para iniciar supervisão, o coordenador precisará remover
e confirmar duravelmente essa autoridade ANTES de publicar supervisão ou alterar
a rota MAC, inibir/revogar atividades antigas e registrar a transação. Nunca
escrever essa declaração no reparo de supervisão, boot ou fallback. Essa ordem,
crash entre fontes, concorrência, restauração de backup e política de criação de
contas ainda NÃO estão implementados/qualificados aqui. Uma declaração antiga
mais contexto unconfined antigo admite por projeto, mesmo se existir estado
parental conflitante: não integrar antes de qualificar o corte dessa autoridade.
O cadastro produtivo não pode tratar esses arquivos como cópia dispensável.

Nome e IDs não são identidade durável: remover/recriar a mesma tupla pode
reutilizar uma declaração obsoleta. O lifecycle deve retirar a declaração antes
de liberar IDs e atribuir geração nova. Não declarar prevenção dessa reutilização
com base neste ensaio sem mutações NSS reais. Root/admin irrestrito é autoridade
confiável conforme contrato autorizado; sem promessa de resistência a root.

## Matriz nativa

A fixture usa dois managers systemd-user reais com PAM vendor, sem argumentos
estáticos de conta ou skip Unix. As admissões verificam PID/contexto e as
negações exigem status224/MainPID0 e causa exata do módulo após cursor de journal.
Managers, runtimes e logind são drenados entre casos.

| Injeção root na VM | Supervisionada | Comum |
|---|---|---|
| Baseline íntegra | Admitida | Admitida com declaração independente |
| Estado transacional ausente/corrompido | Negada | Admitida |
| Entrada supervisionada ausente | Negada/Unknown | Admitida |
| Índice parental ausente/corrompido/modo0644 | Negada | Admitida |
| Declaração comum ausente/corrompida/modo0644/GID divergente | Admitida | Negada, sem fallback ordinary |
| Declaração ordinary forjada para supervisionada, MAC ainda supervisionado | Negada | Admitida |
| Restauração final | Admitida | Admitida |

Os quatro controles da declaração inválida reproduzem a perda da autoridade
comum e recusam fallback: não significam que toda falha do classificador mantém
acesso. O controle ausente conserva contexto MAC comum e linha ordinary no
índice; nenhum dos dois basta para admissão. A declaração forjada é injeção root
apenas para testar o requisito MAC, não ataque executado por usuário.

## Reprodução e reversão

VM descartável com AMBOS marcadores de kernel e serial lyra-admission-test.
Helpers `/root/ordinary-attestation/`, C `/root/attestation-pam-guard.c`, writer
histórico `/root/barrier-writer.py`. Rodar nativo desacoplado com stdout/stderr e
exit-status registrados: o agente de comandos tem limite120s, não deixar uma
rodada maior depender dele. O native.py restaura arquivos com escrita atômica
0600 entre injeções e remove os dois índices e declarações no finally, seguido
por cleanup.py. restore-check.py inspeciona independentemente estado anterior,
bytes/modo PAM, vendor, arquivos de contas, managers/sessões/processos e SELinux.

Reversão remove módulos/índices/declarações exclusivos do ensaio e restaura
PAM original e Permissive da VM. Nenhum pacote ou mapping SELinux criado aqui.
A restauração de root/evidência não constitui procedimento de recuperação do
produto. Sem GDM/GNOME completo, login/password/auth, SSH/cron/D-Bus, produtores,
boot, update/rollback ou checksum ISO; audit não é inventário completo.
Proteção parental completa continua NO-GO. Próximo gate: retirar duravelmente
esta autoridade em transições, sem reconstrução automática, e qualificar
falha/crash/concorrência antes do lifecycle real de contas.

## Resultado de 02/10/2026

26 controles nativos concluídos, processo rc0/stderr vazio; seis pares de
falhas exclusivamente parentais preservaram a comum e negaram a supervisionada.
Quatro pares de falha da declaração própria negaram a comum e preservaram a
supervisionada. Declaração ordinary forjada para a supervisionada recusada pelo
MAC; final ambas readmitidas após restauração. Suíte Python existente: 286 testes
PASS, sem testes Python novos; stdout/rc nativos e log da suíte preservados.
Verificador offline confere hashes, identidades, causas PAM, contextos,
restauração e limites false de qualificação global/cutover. Inspeção independente
PASS, PAM/mode/vendor/passwd/group preservados; VM desligada, QEMU rc0.
Audit perdeu eventos (contadores até11): não inferir cobertura AVC completa.
Nenhum host/receita/OBS/ISO parental modificado, sem publicação/promoção.
