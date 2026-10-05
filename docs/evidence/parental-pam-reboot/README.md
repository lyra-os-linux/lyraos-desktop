# Operação pendente após reboot real da VM

Resultado: PASS local. Suíte com 744 testes; 14 controles antes do reboot,
7 depois e quatro leitores independentes de restauração. Execute
`python3 docs/evidence/parental-pam-reboot/verify-evidence.py` para conferir
os arquivos arquivados, hashes das dependências e resultados.

Este ensaio acrescenta evidência de segurança à recuperação experimental:
um reboot real não transforma um pedido antigo em autorização para agir no
novo boot. Não modifica os módulos de produção nem habilita recuperação
entre boots. Os adaptadores permanecem restritos à fixture descartável.

## Execução

A VM marcada, com disco qcow2 próprio e backing raw previamente conferido,
recebeu o auxiliar PAM fechado já qualificado (hold de 30 segundos). O worker
registrou a origem, enviou um único StopUnit e persistiu `accepted` antes de
encerrar abruptamente com código 91, sem executar finally. Um consumidor novo
no mesmo boot observou Busy, sem reenviar o pedido. O checkpoint preservou
hash, inode, permissões e proprietário dos arquivos de prova, ledger, origem,
efeito e locks, além da máscara possuída.

`systemctl reboot` encerrou o primeiro QEMU com código 0 devido a `-no-reboot`.
O mesmo disco foi aberto novamente. O UUID real passou de
`ef6d2bf1-1883-47aa-becd-2148c56a7f8e` para
`54aaba94-0a4a-4eec-9a63-f2b52e441c47`. Não houve substituição de boot_id por mock.

No novo boot os artefatos negativos ficaram idênticos. Dois consumidores novos,
com intenções de autorização distintas, retornaram RecoveryRequired antes de
chamar autorização; nenhum herdou pidfd, reutilizou o job ou enviou StopUnit.
Mesmo com cgroup vazio e sem job, o registro antigo permaneceu pendente.

A máscara persistente negou partida do produtor. Para verificar causalmente o
PAM, a manutenção da fixture guardou e recolocou a mesma máscara, conservando
o inode: o produtor sem máscara falhou com 224/PAM. `user@1002` também falhou
com 224. A prova da conta vizinha permaneceu igual e uma admissão nova dela
funcionou; não tratamos seu PID anterior como autoridade ou como sobrevivente.

## Restauração e limites

A limpeza removeu os produtores, política e arquivos reservados e repôs a
configuração original. Quatro leitores conferiram restauração; um quinto
conferiu ausência de perfil PAM, marker e effects, e SELinux Permissive original.
A VM terminou OFF com segundo QEMU código 0. O backing não foi modificado.
Isso é restauração da fixture; não é rollback integral do filesystem.

O benefício é demonstrar recusa segura de autoridade obsoleta. O risco do teste
é deixar configuração experimental no overlay se houver interrupção; a reversão
é a limpeza limitada e, se necessário, o descarte do overlay após conferir seu
backing. Nada foi instalado ou promovido na estação.

Este reboot foi gracioso: o systemd pode drenar o auxiliar durante o shutdown.
Não demonstra perda de energia, interrupção de escrita/rename/fsync, proteção
contra rollback por root ou recuperação autorizada entre boots. Também não
qualifica daemon de produção, PAM geral, D-state ou cobertura global de contas.
As issues #6 e #102 continuam abertas; controle parental integral permanece
NO-GO. Próxima prova separada: desligamento abrupto da VM com efeito pendente.
