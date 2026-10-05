# Persistência da retirada de admissão e do registro de operação

Resultado final PASS: 744 testes, 140 controles na VM (6 pré-corte + 8 pós-boot
por caso), 40 leitores de restauração e dez leitores adicionais. Todas as dez
VMs terminaram OFF, com limpezas e poweroffs/encerramentos finais 0.

Esta prova acrescenta cortes reais da VM às interrupções de processo já
qualificadas em parental-registry-barrier, parental-operation-journal e
parental-withdrawal-boot. Não repete aqueles ensaios após fsync nem modifica
seus modelos. Verificador:
`python3 docs/evidence/parental-owner-cut/verify-evidence.py`.

## Contrato e benefício

A primeira publicação de `.deny-1002` persiste a intenção completa antes de
qualquer retirada da prova positiva. O registro separado `.operation-1002.json`
conserva a mesma identidade/operação/inventário. Ambos usam o gravador
RegistryStore._atomic existente. A remoção de `1002` usa unlink seguido de
fsync do diretório, depois de marcador e journal duráveis.

O benefício é distinguir retirada ainda não confirmada de bloqueio persistido.
Antes da durabilidade do primeiro marcador, uma interrupção pode conservar a
admissão original: a autorização inicial não equivale a uma operação concluída.
Depois da persistência do marcador, a conta precisa continuar negada mesmo
com registro de operação incompleto ou prova positiva ainda presente. A
remoção da prova positiva não é o primeiro ponto de negação.

## Método

Dez overlays novos e independentes: quatro pontos para o primeiro marcador,
quatro para o primeiro registro separado e dois para unlink da prova.
Os pontos de publicação são escrita parcial, fsync do temporário, rename e
fsync do diretório. Para remoção, pausa imediatamente após unlink ou após
fsync do diretório. Wrappers executam os syscalls reais e pausam o worker com
SIGSTOP; notificam apenas por tmpfs. Nenhum checkpoint/fsync adicional em disco
ocorre depois da pausa. Instalação e checkpoint são duráveis antes do worker.

Executa o Operations.begin real. O worker recebe autorização inicial explícita;
isso é callback confiável da fixture, não Polkit. Durante a pausa, o serviço
PAM da unidade conserva MainPID e auxiliar vivos, sem job de parada. Não testa
revogação desses processos: o método trata de futuras admissões e grava estado
negativo, sem quiescência ou mutação Unix.

O host valida root, ambos os marcadores, serial, boot e worker parado. Confere
QEMU/disco, abre pidfd, envia SIGKILL somente à VM e observa retorno -9. O mesmo
overlay é relançado; UUID real diferente e fontes PAM/unidades intactas são
conferidos antes de verificar os dados e tentar admissões nativas.

## Critérios

Antes de rename, o canônico publicado pela escrita interrompida deve estar
ausente. Após rename, antes de fsync do diretório, pode estar ausente ou inteiro.
Após fsync do diretório, precisa estar inteiro. Temporários não são promovidos.
Durante a publicação do registro separado, o primeiro marcador já é durável.
Durante unlink, marcador legado blocked, journal blocked e owner legacy-blocked
precisam permanecer íntegros. Antes do fsync do unlink, a prova positiva pode
voltar ou permanecer ausente; depois dele precisa permanecer ausente. O
marcador nega em ambos os casos.

A inspeção é somente leitura. Outra operação é recusada antes de autorização.
Retomada com autorização negada conserva todos os arquivos; se o primeiro
marcador não persistiu, resume retorna RecoveryRequired sem pedir autorização.
Não há reconstrução de autoridade a partir de temporário nem retirada implícita.

Com marcador presente, user@1002 falha 224/PAM com causa exata de retirada.
Sem o primeiro marcador persistido, o manager entra pela prova original íntegra,
no contexto unconfined esperado, sem alegar confirmação da retirada. A conta
vizinha é admitida e conserva sua prova. Tentativas PAM não alteram os arquivos
ou recriam a prova retirada.

## Resultados observados

O primeiro marcador ficou ausente nos três primeiros pontos e persistiu após
fsync do diretório. Sua ausência conservou a admissão original, sem confirmar
retirada. Nos quatro cortes do registro separado, o marcador já persistido
continuou negando. O canônico separado ficou ausente nos três primeiros pontos
e inteiro no quarto. Após unlink sem fsync a prova voltou; após fsync ficou
ausente. Ambas as condições conservaram a negação durável.

## Restauração, risco e limites

O risco é corromper um overlay ou deixar configuração experimental nele. A
reversão é a limpeza limitada ou descarte após conferir o backing raw. Leitores
independentes verificam restauração da fixture; isso não é rollback integral
do filesystem. O driver local é arquivado em host-run.py; caminhos/runtime
pertencem ao laboratório. A estação e pacotes de produção não são alterados.

O host e seu cache continuam vivos durante SIGKILL do QEMU: não é falta de
energia física ou teste de erros reais de armazenamento. Não qualifica todas
as substituições posteriores do journal/owner, falhas de fsync com erro ou
antirollback por root. A retomada autorizada após estes cortes não é exercitada
aqui; o teste verifica consulta e negação de retomada.

Não prova quiescência, daemon de produção, PAM geral/D-state, lifecycle Unix,
cobertura global de produtores, UI/Polkit ou ISO. Controle parental integral
permanece NO-GO; #6 e #102 continuam abertas. Próximo: recuperação explicitamente
autorizada após corte, preservando a negação e sem afirmar quiescência.
