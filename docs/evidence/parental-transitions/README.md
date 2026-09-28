# Bloqueio durante transições de supervisão — 28/09/2026

Trocar configuração PAM não encerra processos existentes. Antes de implementar
criação, migração e remoção de supervisão, este ensaio acrescenta uma barreira
para contas **já vinculadas, com nome/UID/GID/grupo estáveis**. Não é uma API de
administração de contas nem uma integração de produção.

## Comportamento

O guard da [etapa de identidade](../parental-identity/README.md) ganhou um
estado de root consultado em cada abertura de sessão. O estado precisa conter
`active=nome:UID:GID:grupo` exato. Arquivo ausente, inválido, ligado por symlink
ou hardlink, sem propriedade de root ou com escrita por terceiros recusa a conta.
O diretório também precisa ser de root e protegido. O seletor existente continua
preservando a conta comum, que não depende desse estado.

O módulo conserva uma trava compartilhada durante a sessão PAM. Fechar a sessão
ou finalizar o handle libera a referência. O cleanup após fork fecha apenas a
cópia local; não usa `LOCK_UN`, que soltaria a trava compartilhada com o pai.
Os contratos usados são os do
[`pam_set_data`](https://man7.org/linux/man-pages/man3/pam_set_data.3.html) e
[`flock`](https://man7.org/linux/man-pages/man2/flock.2.html).

`transition.py` serializa os controladores com uma segunda trava, grava
`blocked` por substituição atômica com fsync e tenta obter a trava exclusiva
das sessões. Se uma sessão ainda possuir a trava, recusa a operação e mantém
o bloqueio para novas sessões. Depois verifica `/proc`: qualquer processo com
UID real, efetivo, salvo ou de filesystem da conta impede a transição.
Erros de leitura/identidade abortam; processo que já desapareceu é ignorado.
Não há encerramento automático de processos.

No retorno normal, identidade e ausência de processos são verificadas novamente
antes de publicar `active`. Falha antes dessa publicação mantém `blocked`.
Se a gravação final reportar erro, tenta restaurar `blocked` e devolve a falha.
A recuperação é uma nova operação explícita de root, com as mesmas verificações.
Restaurar o cadastro sozinho não remove o bloqueio.

## Evidência nativa

[55 cenários](result.json) passaram na cópia descartável, com libpam/SELinux
reais e compilação `-Wall -Wextra -Werror`. O ensaio preservou o controle positivo
de duas contas supervisionadas, a negação de Python e a execução da conta comum.

| Cenário | Resultado |
| --- | --- |
| Transição em andamento | Conta afetada recusada; outra supervisionada e comum continuam |
| Sessão PAM já aberta | Operação recusada; nova admissão bloqueada até recuperação |
| `pam_end` sem close e cleanup no filho | Recursos liberados corretamente; filho não libera trava do pai |
| Handle PAM iniciado antes do bloqueio | A abertura posterior observa o estado bloqueado |
| SIGKILL no controlador dentro da transição | Travas liberadas pelo kernel; estado continua bloqueado |
| Serviço com UID da conta fora do logind | Continua vivo após `terminate-user`; `/proc` impede a transição |
| Alteração do GID durante a operação | Commit recusado; restauração do GID ainda exige recuperação |
| Erro injetado após publicar estado ativo | Restauração de bloqueio passou; conta comum preservada |
| Estado incorreto, ausente, inseguro ou ligado a outro arquivo | Admissão recusada |
| Falha na checagem SELinux | Admissão recusada sem vazar a trava |

O processo persistente foi criado por root com `systemd-run --uid` numa unidade
de sistema sem `PAMName`; não era uma sessão de login. `loginctl terminate-user`
retornou1 e esse processo continuou em `system.slice`. Isso demonstra por que
ausência de sessão no logind não basta para afirmar ausência de processos;
não é uma falha do loginctl em encerrar uma sessão que ele gerencia.

Quatro testes Python adicionais verificam os quatro UIDs, identidade de processo
inválida/desaparecida e entrada inválida do registro. A suíte completa passou
com **245 testes**. [Proveniência e hashes dos fontes](provenance.json) conferidos
contra os arquivos efetivamente enviados ao guest.

## Reprodução e limites

O harness exige root, disco `lyra-admission-test` e marcador
`lyra.parental-identity-test=1`. Utiliza somente `/etc/pam.d/lyra-transition-probe`,
`pam_lyra_transition_fixture.so` e um diretório de estado exclusivo em
`/etc/security/lyra-parental-transition-fixture`. Precisa da política experimental
anterior e do gerador `../parental-identity/bindings.py`. O controlador não possui
daemon, serviço D-Bus, integração Polkit ou interface no Vega.

A primeira rodada passou os cenários funcionais, mas a limpeza tentou parar
novamente uma unidade transitória já coletada pelo systemd e retornou erro.
A fixture foi removida; o harness foi corrigido e a rodada final completa passou,
incluindo a limpeza. Conta/grupo/mapa temporários, módulo, PAM e estado foram
removidos. A VM voltou a permissive e foi desligada. O disco parental original,
host, receita e pacotes OBS permaneceram intocados.

**Não usar este resultado para permitir alterações de supervisão em produção:**

- Só a pilha PAM de teste participa das travas. GDM, systemd-user, D-Bus, TTY,
  SSH, cron, lingering e serviços com `User=` precisam de contrato e integração.
  Um produtor fora dessa fronteira pode criar processos depois da varredura.
- O harness de root abre sessões, sem autenticação de senha. A autorização
  administrativa e a confirmação de encerramento de sessões ainda não existem.
- Não implementa cadastro, migração de identidade, tombstones contra reutilização
  ou retirada da supervisão. Troca simultânea de todos os identificadores ainda
  pode escapar do seletor antigo; isso permanece uma operação não suportada.
- O teste injeta erro depois da publicação e confirma a restauração quando o
  armazenamento aceita novas escritas. Falha simultânea da publicação e da
  restauração, perda de energia, disco corrompido e rollback não foram qualificados.
  SIGKILL não equivale a ensaio de queda de energia.
- O estado ativo só permite chegar às checagens de identidade/SELinux do guard;
  não atesta proteção integral ou autoriza a interface a anunciar supervisão ativa.

Próxima etapa: integrar e qualificar entradas reais antes de usar essa barreira
para mudar o cadastro ou a supervisão, incluindo processos persistentes e
recuperação. O ciclo completo de identidade e as demais superfícies da
[fronteira aprovada](../../parental-protection-boundary.md) continuam pendentes.
#6/#102 permanecem abertas; nenhuma promoção de produção ou ISO foi feita.
