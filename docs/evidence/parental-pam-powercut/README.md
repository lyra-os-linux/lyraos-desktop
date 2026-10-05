# Corte abrupto da VM com parada pendente

Resultado final: PASS local. 744 testes, 15 controles antes do corte e oito
depois, quatro leitores independentes de restauração e um leitor adicional de
perfil/marker/effects/SELinux. Verificação dos arquivos e resultados:
`python3 docs/evidence/parental-pam-powercut/verify-evidence.py`.

O benefício desta prova é verificar recusa segura da autoridade anterior quando
o sistema convidado perde sua execução sem shutdown. Não modifica os módulos
de produção nem habilita recuperação entre boots.

## Falha encontrada e correção da fixture

O primeiro corte preservou os registros negativos e recusou o efeito antigo,
mas a admissão da conta vizinha falhou. O journal registrou `file too short`
ao carregar o módulo PAM recém-compilado. A instalação feita durante o teste
não estava durável antes de simular a interrupção. O conjunto desse ensaio
permanece FAILED, arquivado em `failed-unflushed-setup/`, com suas fontes,
respostas e quatro leitores de restauração PASS. Seus resultados 224/PAM
não são usados como evidência causal de bloqueio por retirada de admissão.

A fixture agora estabelece uma fronteira explícita de instalação:
`os.sync()` depois de instalar/configurar os módulos, perfis, programas e
unidades, e ANTES de iniciar a retirada ou criar o efeito. Não há sync extra
entre a operação pendente e o corte. No novo boot, verifica hash, inode,
proprietário, permissões e links desses arquivos antes de testar o PAM. Isso
simula uma instalação concluída; não qualifica resistência do instalador/RPM
à interrupção nem elimina a necessidade de testar as fronteiras das escritas.

## Corte e novo boot

O worker usa o auxiliar fechado já qualificado, com hold de 30 segundos.
Persiste origem e `accepted` após UM StopUnit, depois sai com código 91 sem
finally. Um consumidor novo no mesmo boot retorna Busy sem reenviar parada.

O controlador valida root, marcadores e serial do convidado, boot original,
job pendente, MainPID 0, auxiliar ainda no cgroup e marker presente. No host,
abre pidfd e valida a linha de comando do QEMU e o caminho exato do overlay
antes de enviar SIGKILL. Não solicita reboot, poweroff, ACPI ou flush do guest.
O encerramento é código 137. Relança o MESMO qcow2 e verifica UUID real distinto.

Na segunda execução, fontes instaladas e todos os artefatos negativos mantêm
seus hashes/inodes/permissões/proprietários. Dois consumidores distintos
retornam RecoveryRequired antes de autorização; nenhum herda pidfd, reutiliza
job ou envia StopUnit. O cgroup vazio não autoriza completar o efeito antigo.
A máscara persistente recusa partida. Na manutenção causal, a MESMA máscara
é guardada e recolocada; o produtor sem máscara falha com 224/PAM, e user@1002
também. A prova vizinha fica intacta e sua nova admissão funciona.

## Restauração, risco e limites

Os dois ensaios usam o mesmo overlay descartável e backing raw previamente
conferido. A limpeza retorna 0 em ambos. As verificações finais conferem a
remoção da fixture e SELinux Permissive original. O último poweroff retorna
0 e QEMU encerra 0; VM OFF. Nada foi instalado ou promovido na estação.

O risco é corromper o overlay ou deixar configuração experimental nele. A
reversão é a limpeza limitada e, se necessário, descarte após conferir o
backing. Não há rollback integral de filesystem nem alteração do backing.

SIGKILL encerra o QEMU e perde a memória do convidado, mas o host e seu cache de
armazenamento continuam vivos. Não é falta de energia física, teste de cache
volátil do dispositivo ou interrupção controlada de write/rename/fsync.
A prova final corresponde ao efeito accepted durável; não cobre todas as
fronteiras de persistência ou proteção contra rollback por root.

Recuperação autorizada entre boots, daemon de produção, PAM geral/D-state,
cobertura global e integração final permanecem NÃO qualificados. Issues #6
e #102 seguem abertas; controle parental integral NO-GO. Próximo: testar
interrupções nas fronteiras de escrita/rename/fsync dos registros.
