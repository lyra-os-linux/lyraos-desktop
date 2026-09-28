# Login GDM com senha e bloqueio durante autenticação — 28/09/2026

**18 cenários nativos passaram** na VM descartável. Esta etapa estende a
[admissão dos gerenciadores](../parental-managers/README.md) à conversa
`gdm-password`, mantendo autenticação PAM real e verificando o contexto da
sessão resultante. Não ativa controle parental na receita ou em pacotes.

## Como a senha é verificada

O GDM real inicia seu greeter. Um [cliente de teste](client.py), executado com
UID/GID de `gdm`, conecta ao servidor privado do greeter e usa os métodos
`BeginVerificationForUser`, `AnswerQuery` e `StartSessionWhenReady` das
interfaces `UserVerifier` e `Greeter`. Esse protocolo foi conferido em
`daemon/gdm-session.xml` e `gdm-session.c` do fonte oficial preparado na
[etapa anterior de GDM](../parental-gdm/README.md).

O cliente somente responde à solicitação `SecretInfoQuery` de `gdm-password`.
O worker nativo executa a pilha PAM vendor, incluindo `pam_unix`, e depois
a barreira experimental de sessão. A senha não é substituída por `pam_permit`
nem por uma chamada direta a `pam_open_session` de um programa de root.
Os controles de senha errada e recuperação com a correta demonstram o caminho
de autenticação. Nos negativos de admissão, o journal do mesmo worker precisa
comprovar `AUTHENTICATED` e `AUTHORIZED` antes da recusa na sessão.

Senhas aleatórias são criadas apenas no guest para as duas contas fictícias,
entregues por stdin ao `chpasswd` e ao cliente, e nunca enviadas ao host ou
incluídas nos argumentos dos processos. O harness verifica que elas não
aparecem nos registros exportados. Ao final, restaura os bytes originais de
`/etc/shadow`. Isso exige uma VM dedicada, sem alterações concorrentes de contas;
não é um procedimento para a estação real.

## O que os testes demonstram

| Cenário | Resultado |
| --- | --- |
| Senha correta da conta supervisionada | Autenticada; sessão ELF mínima no contexto restrito |
| Sessão ativa e tentativa de transição | Worker GDM e `(sd-pam)` retêm travas; operação recusada, sessão continua viva |
| Encerramento e nova tentativa sob bloqueio persistente | Travas liberadas, mas senha correta ainda não abre sessão |
| Recuperação explícita | Nova sessão aceita no contexto correto |
| Estado ausente, módulo PAM ausente ou SELinux permissive | Senha correta autentica; abertura de sessão supervisionada recusada |
| Conta comum nos mesmos estados de falha | Senha correta abre sessão unconfined |
| Bloqueio enquanto GDM aguarda a senha | Resposta correta posterior autentica, mas não abre sessão |
| Senha incorreta | Falha em `pam_unix` e conversa encerrada, sem sessão |
| Senha correta após a tentativa incorreta | Sessão aceita; não se confundiu indisponibilidade com proteção |

No cenário pendente, a pilha com guard já está instalada. O cliente recebe o
prompt e aguarda; o controlador grava `blocked` numa transição interrompida
intencionalmente; somente depois envia a senha correta. O handle PAM iniciado
antes da mudança consulta o novo estado ao abrir a sessão. Após encerrá-lo,
uma recuperação explícita permite nova autenticação.

Isso **não** qualifica migração de uma conta que ainda não tinha o guard,
troca/reutilização de identidade ou retirada de supervisão. O worker de root
que aguarda a senha ainda não possui a trava de sessão; o resultado depende
da consulta obrigatória do estado em `pam_open_session`. O cenário não autoriza
usar apenas ausência de UID em `/proc` para mudar o cadastro.

[Resultado nativo](result.json) e [proveniência dos fontes/RPMs](provenance.json).
A suíte Python passou com **262 testes**, incluindo sete regressões do
[verificador de evidência](evidence.py): conversa de senha separada de
autologin, módulo opcional, conversa incompleta, worker/manager/conta alheios,
ordem incorreta e sessão iniciada posteriormente.

## Critérios e limites

Os negativos exigem causa específica, abertura tentada, retorno do mesmo
worker a `NONE`, falha de início registrada pelo manager e saída do worker.
O harness observa mais dois segundos sem encerrar o GDM, exige ausência do
executável e rejeita qualquer início posterior registrado. A senha errada
exige falha de autenticação `pam_unix`, `VerificationFailed` e
`ConversationStopped`, sem abertura de sessão.

O cursor do journal é obtido **depois** de o greeter estar registrado e antes
da conversa de senha. A primeira rodada já abriu a sessão supervisionada e
recusou a bloqueada, mas o verificador contou o início do próprio greeter como
sucesso do usuário. Esse erro de observação foi corrigido e a matriz inteira
repetida. Também foi separado `AUTHENTICATED` do sinal `VerificationComplete`:
o GDM pode reportar `VerificationFailed` por falha na abertura da sessão mesmo
quando a senha foi aceita. A rodada vinculada passou incluindo a limpeza.

Esta é automação do protocolo nativo, não um teste de digitação, acessibilidade,
layout de teclado ou UX da tela de login. O cliente de teste parte do controlador
privilegiado e reduz UID/GID para gdm; não demonstra resistência a comprometimento
do greeter. O worker, PAM e processo final da conta são os componentes avaliados.

O worker ainda é o **build de diagnóstico com o patch anterior dos hooks de
root**, não um RPM de produção reconstruído. A sessão do usuário é o
`session.c` mínimo da etapa anterior, sem compositor/aplicativos. A política
temporária do launcher é a mesma, sem permissões novas. O greeter real funciona
na VM, mas isso não qualifica uma sessão GNOME supervisionada completa.

## Reprodução e restauração

Requer a mesma VM/política anterior, disco `lyra-admission-test` e marcador
`lyra.parental-identity-test=1`. O harness verifica esses pré-requisitos antes
de alterar arquivos. Preparar os fontes anteriores sob `/root` como descrito
na etapa dos gerenciadores, além de:

| Fonte | Destino no guest |
| --- | --- |
| `client.py` | `/root/password-client.py` |
| `evidence.py` | `/root/manager-gdm-evidence.py` |
| `launcher.cil` | `/root/lyra-password-launcher.cil` |

Executar [exercise.py](exercise.py) como root exclusivamente nessa VM.
O resultado é `/root/password-gdm-result.json`. Ao final, foram restaurados
shadow, PAM, arquivos de sessão, configuração GDM, AccountsService, rótulo
do launcher e worker oficial (SHA256 registrado). Módulo PAM, estado, ELF
de teste e módulo CIL foram removidos; GDM e gerenciadores foram parados;
SELinux voltou a permissive. Os arquivos vendor permaneceram intactos.

Próximo: fechar entradas persistentes/alternativas (lingering, D-Bus, cron e
serviços `User=`), revogação de processos/conexões existentes e o ciclo
autorizado de contas. Desbloqueio e reautenticação ainda não foram qualificados.
#6/#102 continuam abertas; nenhuma publicação OBS, mudança no host ou ISO.
