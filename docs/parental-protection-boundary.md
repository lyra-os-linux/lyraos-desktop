# Conta supervisionada restrita — Alpha 8

Status: decisão de produto aprovada em 21/09/2026; mecanismo de proteção em
qualificação. Não habilitado na receita, no host ou em contas reais.

O mantenedor escolheu “Conta restrita, com aplicativos aprovados e proteção
contra evasão”. O alvo é GNOME/Vega GTK. Contas comuns devem preservar seu
funcionamento. A interface só pode anunciar supervisão ativa quando todas as
camadas obrigatórias estiverem verificadas.

## Fronteira e critérios

| Superfície | Critério para entrega | Estado |
| --- | --- | --- |
| Política | Alteração autorizada, persistência, corrupção sem liberação | Base malcontent parcialmente ensaiada |
| Flatpak | Bloquear mesmo com cliente alternativo, serviço ausente ou ambiente alterado | Falha demonstrada; #102 aberta |
| RPM, AppImage e cópias | Negar execução direta e indireta fora dos aplicativos aprovados | Ainda não qualificado |
| Interpretadores e extensões | Não permitir código arbitrário por shell, Python, macros, plugins ou carregador ELF | Dois desvios reproduzidos no ensaio abaixo |
| Sessão | Cobrir GDM, serviços systemd do usuário, ativação D-Bus e processos persistentes | Ainda não qualificado |
| Entradas alternativas | TTY, SSH, cron e outras entradas não podem iniciar processos sem restrição | Ainda não qualificado |
| Serviços privilegiados | Polkit, instalação, containers e virtualização não podem delegar execução irrestrita | Ainda não qualificado |
| Falhas | Política/serviço/kernel incompatível mantém restrição; não vira conta comum | Ainda não qualificado |
| Recuperação | Responsável autorizado recupera acesso sem apagar política; contas comuns intactas | Ainda não qualificado |
| Atualização | Substituição de binários e rollback não deixam permissões obsoletas ou abertas | Ainda não qualificado |

Aprovar um aplicativo significa revisar também suas capacidades de executar
código e delegar operações. Ocultar terminal ou remover atalhos não atende ao
critério. Conta supervisionada não recebe administração irrestrita. A proteção
não promete resistir a root comprometido ou alteração offline do disco;
credenciais administrativas e inicialização física pertencem a outras camadas.
Filtragem de conteúdo de rede não foi qualificada por este ensaio.

## Ensaio de execução no kernel

Na VM descartável, kernel `6.12.0-160100.4-default`, conta fictícia UID 1003,
Landlock informou ABI 6. Um processo sem privilégios aplicou uma política que
trata **somente EXECUTE**, permitindo `true`, Python e o carregador ELF.

| Tentativa | Resultado |
| --- | --- |
| `true` aprovado | Executou |
| `false` não aprovado | EACCES |
| Cópia de `true` em diretório temporário | EACCES |
| Carregador ELF aprovado abrindo essa cópia | Executou — desvio |
| Python aprovado executando código arbitrário | Executou — desvio |

Evidência: [resultado JSON](evidence/parental-confinement-20260921.json).
Reprodução: [probe Python](evidence/parental-confinement-probe.py), somente na
VM com marcador `lyra.virtualization-test=1` e conta fictícia `parentaltest`.
A restrição foi aplicada exclusivamente a um processo temporário e seus
descendentes. Não houve instalação de política para a conta inteira.

**Conclusão: rejeitada a proposta de usar apenas Landlock EXECUTE como
fronteira da conta.** Os cinco casos caracterizam o mecanismo; os dois desvios
são resultados esperados do experimento, não testes de segurança aprovados.
O ensaio não avaliou todos os recursos do Landlock nem comprovou impossibilidade
de utilizá-lo como uma camada complementar.

## Próxima implementação

### Progresso experimental em 22/09

O [ensaio do domínio e de sessão PAM](evidence/parental-selinux/README.md)
demonstrou negações em enforcing e seleção do domínio por mapeamento de
usuário. A checagem PAM experimental rejeita mapeamento ausente e estado
permissivo. Ainda não pode ser integrada: falha do cadastro também bloqueia
a conta comum, e o `systemd-user` restrito falha na preparação de keyring.
Proteção da conta inteira, sessão GNOME e recuperação seguem pendentes.

### Auditoria da base oficial em 21/09

Foram baixados e extraídos, sem instalação, cinco RPMs oficiais do Leap 16.1:
SELinux policy/targeted `20260826+git0.492b478c7-160100.1.1`, PAM
`1.7.2+git12-160100.2.1`, GDM `48.0-160100.2.1` e o pattern SELinux
`20241218-160100.3.1`. Checksums SHA-512 foram comparados aos metadados do
repositório e as assinaturas RPM verificadas.

- A política distribui `user_u` e `xguest_u`, com contextos para login local,
  SSH, GDM (`xdm_t`), cron e init. Isso oferece pontos de integração; não prova
  que cada entrada esteja confinada na candidata.
- O mapeamento padrão é `unconfined_u`. Instalar SELinux não converte
  automaticamente uma conta em supervisionada.
- As regras CIL de `user_t` e `xguest_t`, por seus atributos de usuário,
  permitem `execute_no_trans` para `bin_t` e `shell_exec_t`. Portanto, usar
  esses perfis sem alteração não atende à lista de aplicativos aprovada.
- O script de instalação de `selinux-policy` cria configuração enforcing
  quando ausente e executa `pam-config -a --selinux`. Não basta inspecionar o
  arquivo PAM estático do GDM: a pilha gerada também precisa ser verificada.
- A receita Lyra usa `patternType="onlyRequired"` e não declara SELinux
  explicitamente. Os Requires diretos examinados dos patterns base,
  enhanced_base, minimal_base e gnome_basic não garantem sua inclusão. Isso
  **não é uma resolução completa de dependências**; o conjunto resolvido e o
  estado do kernel da candidata permanecem pendentes.

[Evidência dos RPMs e regras](evidence/parental-mac-20260921.json) e
[auditor reproduzível](evidence/parental-mac-audit.py). O auditor é estático:
não executa scriptlets, não carrega política e não qualifica a sessão GNOME.
Os RPMs extraídos e metadados estão no workspace em
`analysis/2026-09-21/parental-mac/`. A origem da política openSUSE e sua relação
com Fedora estão documentadas no [repositório oficial](https://github.com/openSUSE/selinux-policy).

### Decisão técnica e sequência

SELinux é o próximo candidato de integração a testar, aproveitando os pacotes
oficiais. **Não aprovar `user_u`/`xguest_u` como solução pronta nem acrescentar
regras `allow` esperando revogar as permissões amplas já existentes.** A prova
seguinte precisa de um domínio dedicado com permissões mínimas, sem herdar
as permissões genéricas incompatíveis com a lista de aplicativos.

1. Preparar uma VM separada com política oficial, rotulagem e enforcement
   verificados; preservar a VM dos ensaios anteriores como comparação.
2. Criar o domínio experimental e demonstrar negação de shell/interpretador,
   cópia e carregamento indireto, mantendo o controle positivo aprovado.
3. Integrar mapeamento PAM e verificar contextos reais de GDM, systemd-user,
   D-Bus, TTY/SSH e cron. Qualificar GNOME, portais e recuperação.
4. Somente após isso fixar dependências e ativação na receita e conectar o
   estado verificado ao Vega GTK. Não promover pacotes antes dessas evidências.

Primeiro identificar a política de controle obrigatório de acesso efetivamente
suportada e ativada na candidata openSUSE e qualificar um domínio de usuário
restrito, incluindo leitura/carregamento de código e serviços fora da árvore
da sessão. Preferir integração com a base a um lançador exclusivo do Lyra.
Não escolher SELinux/AppArmor só pela presença de headers ou pacotes no host.

Antes de integrar ao Vega: reproduzir e bloquear os desvios acima; testar
cliente Flatpak alternativo, ambiente adulterado, indisponibilidade de política,
sessão GNOME/portais e recuperação; registrar também o controle positivo de
uma conta comum. A ausência de um mecanismo qualificado mantém o recurso
indisponível, sem reduzir silenciosamente o requisito aprovado.

Depois vêm auditoria, correções e qualificação da candidata pelo checksum
exato. Este documento não encerra #6/#102 nem autoriza declarar uma ISO aprovada.
