# Composição do serviço parental com armazenamento real

Resultado: **11 testes de integração PASS numa VM descartável**, com catálogo,
inventário, ledger e locks reais, arquivos root-owned e writer histórico.
Limpeza confirmada, contas/PAM/SELinux preservados, backing raw inalterado por
SHA256/metadados e VM OFF com retorno QEMU 0.

O [guest.py](guest.py) exercita a [ligação de planejamento à retirada](../parental-service-withdrawal/README.md)
e o [classificador](../parental-service-classifier/README.md) sem modificar seus
fontes. Usa Inventory/Operations/Withdrawal e RegistryStore._atomic existentes,
com hash conferido no guest. Não modifica vegad nem instala hook PAM, serviço,
pacote, unidade ou regra. Escritas ficam no diretório exclusivo da fixture.

## O que foi demonstrado

- Planejamento não altera arquivos. Retirada conclui com prova positiva removida,
  marcador negativo e owner retired; catálogo/inventário e conta vizinha mantêm
  bytes, inode, proprietário, modo e tamanho. Diagnóstico continua negando o alvo.
- Autorização nova acontece fora dos três locks: callback adquire EX real em
  catalog.lock, .inventory-1002.lock e .gate-1002.lock. Na primeira publicação
  negativa, a tentativa EX nos três é recusada, confirmando a retenção.
- Contenção em cada lock impede execução antes do callback, sem escrita.
  Negação antes da retirada deixa o snapshot completo idêntico.
- Mudança de catálogo/inventário/prova durante o diálogo é recusada antes do
  marcador. Catálogo e inventário são alterados sob seus locks, pelo mesmo
  writer atômico; nenhuma conclusão permissiva compensa o conflito.
- Processo separado termina com os._exit(91) imediatamente após o primeiro
  intent publicado e fsynced pelo writer real. Prova ainda existe, owner separado
  ainda não existe e diagnóstico nega. Outro processo com autorização nova
  retoma o journal e conclui a retirada, mantendo negação.
- Processo separado repete operação já concluída com autorização nova; TODOS
  os arquivos da fixture conservam hashes/inodes/proprietário/modo/tamanho.
- Ausência de marcador, operação alheia, owner corrompido e geração divergente
  recusam retomada sem autorização ou efeitos adicionais.

Usa identidades locais fictícias já presentes na VM, conferidas por passwd/group
locais e NSS; não cria/remove/modifica contas. O catálogo é preparado pelo
controlador root antes do ensaio. Os produtores no inventário são registros de
fixture, não prova de descoberta ou cobertura do sistema.
A prova positiva é JSON sintético com tupla Unix exata, **não o formato do
leitor PAM histórico**. inspect_admission é diagnóstico, sem login/PAM real.

## Evidência e reprodução

[execution.json](execution.json) contém saída dos 11 testes e retorno 0;
[result.json](result.json) contém snapshots e hashes dos arquivos de contas/PAM
antes/depois, estado SELinux e flags de escopo. [source-hashes.json](source-hashes.json)
registra os oito módulos enviados ao guest. [cleanup-check.json](cleanup-check.json),
[poweroff.json](poweroff.json) e [vm-off.json](vm-off.json) registram limpeza,
retorno de desligamento e backing inalterado. [disk.json](disk.json) identifica
o overlay e backing. [manifest.json](manifest.json) sela os artefatos e fontes.

Na raiz do worktree:

```sh
python3 docs/evidence/parental-service-storage/verify-evidence.py
```

[host-run.py](host-run.py), [vm.py](vm.py) e [host.py](host.py) são cópias do driver
usado em analysis/2026-10-05/parental-service-storage, com caminhos de laboratório.
Não são instaladores ou receita de produção. Nova execução exige overlay e
paths exclusivos, disco confirmado e marcador/serial da VM. O driver confere
a cadeia qcow2/raw e o processo QEMU antes de enviar comandos root. A remoção
final é limitada ao subdiretório fixtures dentro da pasta exclusiva no guest.
Backing: /tmp/lyra-parental-identity-20260928/system.raw; overlay:
/tmp/lyra-parental-service-storage-20261005/system.qcow2.

## Limites e próximo passo

Este ensaio qualifica a composição no filesystem real e uma interrupção de
processo após intent durável, **sem corte/reboot de VM**, falha física de energia
ou injeção de erro write/fsync. Não repete nem extrapola a série de cortes
históricos. Fontes existentes passaram na suíte 780 na etapa anterior e estão
inalteradas; a suíte não foi repetida por adicionar este ensaio independente.

Autorização/remetente/capacidades continuam callbacks confiáveis; UID0 tem
capacidade técnica explícita no laboratório, sem herdar papel de responsável.
Não é Polkit/D-Bus real, proteção contra root, autoridade antirollback,
classificação de boot, quiescência ou enforcement. O guest iniciou/terminou
Permissive; não qualifica política MAC Enforcing ou GNOME completo.

Próximo: adaptar transporte e autorização reais numa fixture isolada, verificando
remetente, negação/cancelamento e vínculo/revisão ao redor do diálogo. A integração
de produto ainda exige decisões #2/#5, guards dos métodos administrativos,
classificação/recuperação/rollback e gates #6/#102/UX/ISO. Produto NO-GO;
nenhuma promoção OBS ou instalação na estação nesta etapa.
