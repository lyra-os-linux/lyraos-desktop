# Administração: D-Bus/Polkit e efeito Unix na mesma fixture

Em 05/10/2026, 15 cenários passaram numa VM descartável, usando o barramento
**system** real, remetente único resolvido pelo próprio D-Bus, `pkcheck` real,
catálogo/inventário/ledger em arquivos root e o guard/envelope selado previamente
qualificados. Os nove modelos anteriores foram reutilizados sem alteração.
Nenhuma mudança foi instalada no host ou no UsersService do vegad.

Executar a verificação de recibos, sem ligar VM:

```sh
python3 docs/evidence/parental-administrative-auth/verify-evidence.py
```

| Cenário | Resultado observado |
| --- | --- |
| Perfil | `usermod -c … -G users -- ordinaryuser`; `$(literal)` permaneceu texto |
| Concessão + repetição do token | `usermod -aG wheel`; mesmo token recusado sem nova decisão/efeito |
| Concessão já aplicada | Nova autorização, no-op, arquivos de contas intactos |
| Retirada | `gpasswd -d ordinaryuser wheel`; grupo users preservado |
| Retirada já aplicada | Nova autorização, no-op, arquivos intactos |
| Alteração do payload durante autorização | Efeito wheel original selado mantido |
| Negação | Polkit rc1; nenhum comando ou escrita nas contas |
| Cancelamento | Agente real retornou Cancelled, pkcheck rc3; nenhum efeito |
| Capacidade revogada após Polkit | Denied, apesar de pkcheck rc0 |
| Revisão do catálogo alterada após Polkit | Conflict, nenhum comando |
| Barreira publicada após Polkit | Blocked, nenhum comando |
| Outro remetente com mesmo UID | Token recusado antes do Polkit |
| UID sem capacidade | Plano recusado antes do Polkit |
| Parâmetro bool incorreto | InvalidParameters antes do Polkit |
| Consulta própria | OrdinaryEligible; sem Polkit ou escrita |

Foram 11 decisões Polkit, quatro comandos Unix com rc0 e dois no-ops.
As três leases ficaram livres durante `pkcheck` e impediram probes EX durante
cada efeito/no-op. Os parâmetros fornecidos ao Plan ficaram privados no servidor;
Execute recebeu apenas identificador, nunca parâmetros substitutos. A fixture
usa JSON limitado a 4096 bytes e rejeita chaves duplicadas; isso não define a ABI
de produto. Não há método Resume administrativo nem retirada de admissão aqui.

A identidade primária UID/nome/GID/grupo e perfil/grupos da conta vizinha foram
conferidos a cada caso. Linhas passwd de outros usuários e shadow não mudaram.
Arquivos passwd/group/shadow/gshadow e backups foram salvos exclusivamente no
guest, em diretório root 0700/arquivos 0600, restaurados e fsyncados; os hashes
originais bateram. Políticas/regras/configuração D-Bus temporárias, agente,
servidores, fixtures e backup foram removidos, com reload e confirmação de
remoção das ações Polkit. PAM/configuração existente preservados. QEMU encerrou
com rc0, VM OFF e disco raw base com hash/inode/tamanho/mtime iguais.

## Limites

A permissão positiva veio de regra Polkit exclusiva de `installeduser` e da ação
fictícia. Não houve autenticação positiva por senha, diálogo GNOME, vínculo de
responsável persistido, PAM/login supervisionado, aplicação malcontent ou
qualificação MAC (SELinux Permissive antes/depois). O catálogo/proof sintético e
adaptador Python são de laboratório, não serviços ou pacotes de produto.

A restauração de arquivos inteiros é procedimento exclusivo do laboratório sem
concorrência externa; não é recuperação segura de produto. Quedas/I/O/reboot
entre comando e registro, alterações NSS concorrentes e escritores externos
não foram qualificados neste ensaio. Create/Remove/senha/foto continuam fora da
fixture. Os gates #2/#5 e #6/#102 permanecem abertos.

`host-run.py`, `host.py` e `vm.py` arquivam o driver realmente executado. O driver
cria overlay novo, confere cadeia do disco e identificação do guest antes dos
efeitos e exige caminho temporário ainda ausente. Recibos/fontes estão vinculados
por `manifest.json`; isso fornece integridade local, não assinatura de release.

## Continuação

Transferir o contrato qualificado para a implementação Go existente do vegad,
começando por classificação e catálogo durável, bootstrap/recuperação e
cobertura dos caminhos de mutação. Não instalar a fixture como produto.
A instalação local após concluir o controle parental foi autorizada pelo
mantenedor, que criará nova conta local de criança/adolescente para testar.
