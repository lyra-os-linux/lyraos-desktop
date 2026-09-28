# Identidade e admissão supervisionada — 28/09/2026

O módulo anterior tinha GID1004 e grupo compilados no código. Este ensaio usa
vínculos explícitos `nome:UID:GID:grupo_privado` em configuração PAM de root e
exercita duas contas com IDs diferentes. Continua exclusivamente experimental:
nada instalado em logins reais, host, receita ou pacotes OBS.

## Contrato ensaiado

`bindings.py` gera um fragmento único com seletor e argumentos do módulo. Se
**qualquer** nome, UID ou GID coincidir com um vínculo, o módulo exige que todos
os componentes coincidam com exatamente um vínculo, incluindo o grupo privado.
Renomear a conta/grupo ou alterar só UID/GID não a transforma em conta comum.
IDs reservados, sintaxe inválida e vínculos duplicados são recusados.

O seletor usa o módulo oficial
[`pam_succeed_if`](https://man7.org/linux/man-pages/man8/pam_succeed_if.8.html):
todas as condições de conta comum precisam ter sucesso para pular o módulo
experimental. Erro no seletor segue para o módulo obrigatório. Assim, quando
o módulo experimental está ausente, as duas contas supervisionadas são
recusadas e a comum continua executando. Isso depende da integridade do
fragmento completo e do PAM oficial; não cobre remoção da configuração inteira.

O guard exige SELinux globalmente enforcing, domínio não permissivo e contexto
de execução pendente exato. O contexto ainda é fixo da política experimental;
somente os identificadores Unix deixaram de estar compilados no módulo.
O fragmento deve ser substituído inteiro, com propriedade de root e sem escrita
pela conta. O gerador puro não instala configuração nem cadastra supervisão.

## Resultado

[47 cenários nativos](result.json) passaram, usando libpam e libselinux reais,
compilação `-Wall -Wextra -Werror` e a política já existente na VM:

| Grupo de cenários | Evidência |
| --- | --- |
| Duas contas, UID1003/GID1004 e UID21000/GID23000 | Probe aprovado executa no contexto restrito; Python recebe EACCES |
| Módulo ausente | Ambas recusadas; conta comum executa Python |
| SELinux global/domínio permissivo ou mapeamento ausente | Supervisionada recusada; comum preservada |
| Nome, UID, GID ou nome do grupo alterado de verdade | Supervisionada recusada; comum preservada |
| GID de uma conta coincide com outro vínculo | Conta ambígua recusada; outra supervisionada e comum preservadas |
| 16 configurações inválidas | PAM_SERVICE_ERR, sem executar payload |
| Recuperação | Duas contas voltam ao probe aprovado; Python continua negado; comum executa |

O harness `pam-probe.py` é chamado por root e abre apenas uma **sessão PAM**:
não autentica senha, não simula login gráfico e não prova cobertura de todas as
entradas da conta. A lista de nomes/programas do harness é intencionalmente
limitada às fixtures. Os testes Python de geração rejeitam injeção de novas
linhas/opções, IDs inválidos e cadastros ambíguos antes de produzir texto PAM.

`exercise.py` só executa no disco `lyra-admission-test` com marcador
`lyra.parental-identity-test=1`. Compila um módulo separado e usa somente
`/etc/pam.d/lyra-identity-probe`. Cria uma conta temporária com IDs livres e
desfaz alterações em `finally`. O resultado confirma retirada de conta,
mapeamento, grupo, módulo e arquivo PAM, preservação dos IDs das contas
originais e retorno ao estado permissivo inicial da VM. Não afirma restauração
byte a byte de toda a base de contas após ferramentas como `useradd`/`userdel`.

A VM é cópia descartável da fixture anterior, com boot direto de kernel,
não uma ISO candidata. O hash do disco de origem antes/depois da cópia foi
`8699b33a0672f497d0fd949b62a7163bd6fb5569feff5a74bae007a4c839ce26`.
As versões e hashes dos fontes usados estão em [provenance.json](provenance.json).

## Limites e próxima etapa

- O contrato cobre contas locais com identidade parcialmente divergente.
  NSS remoto, aliases, indisponibilidade de passwd e identidade inteiramente
  substituída não foram qualificados. Uma conta que deixe de coincidir em
  **todos** os identificadores pode cair no caminho comum.
- Remoção/recriação com os mesmos identificadores pode herdar um vínculo
  antigo. Cadastro, renomeação, migração e remoção precisam de uma transação
  autorizada que cuide também de sessões existentes e processos persistentes.
- Mudanças de política não revogam processos já abertos. Este ensaio não
  integra GDM, systemd-user, D-Bus, TTY, SSH, cron ou lingering; não substitui
  as fixtures antigas dessas entradas nem qualifica recuperação administrativa.
- O seletor e o guard consultam a identidade separadamente. Atualizações
  concorrentes da base precisam de controle no ciclo de cadastro; atomicidade
  do arquivo PAM sozinho não resolve essa corrida.

Próximo: definir o ciclo autorizado de identidade e integrá-lo às entradas reais,
ensaiando falhas e recuperação com conta comum preservada. Depois concluir
evasão, identidade dos aplicativos e integração conforme a
[fronteira aprovada](../../parental-protection-boundary.md). #6/#102 seguem
abertas. Este avanço não autoriza promoção de produção ou conclusão da Alpha8.
