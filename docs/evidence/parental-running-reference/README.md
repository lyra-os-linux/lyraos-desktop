# Vínculo com o processo principal — ensaio isolado

O benefício é impedir que uma configuração de unidade seja tomada como identidade do processo atual. `running.py` integra a Reference anterior com uma observação de execução mantida sob pidfd e diretório /proc abertos. É um leitor e verificador, sem método de parada, autoridade de cobertura ou retirada de barreira.

## Resultado e fontes

620 testes Python passaram, incluindo 18 novos testes do núcleo. Nove controles reais passaram na segunda execução nativa. Na primeira, a unidade inativa foi coletada da memória entre consultas e GetUnit falhou antes do primeiro controle; cleanup passou. A segunda usa LoadUnit somente para carregar definições, mantendo a recusa de MainPID=0. Fonte/result/stderr completos da primeira tentativa estão arquivados. O núcleo e os testes permaneceram iguais; mudou somente a consulta do harness. A pequena correção no backend Linux para comparar stamp sem atime ocorreu depois da suíte e antes de sua primeira execução na VM; esse backend é validado pela matriz nativa, não pelos testes com memória.

A fábrica root revalida a referência de configuração antes e depois de ler o processo. MainPID e ControlGroup têm assinaturas D-Bus u/s; o cgroup precisa ser o /system.slice exato da unidade canônica. O backend fixa pidfd e diretório /proc, confere o PID do descritor por fdinfo e verifica saída por select. A observação compara quatro UIDs e quatro GIDs, grupo suplementar único igual ao primário, CapPrm/CapEff/CapAmb zero, argumentos, instante de criação e dispositivo/inode/SHA256 do executável aberto através do link especial exe do kernel. Não lê executable a partir de caminho informado por GUI.

Há revalidação depois da primeira observação e em cada `Pinned.check()`. Divergência de credenciais, cgroup, executável ou argumentos recusa a referência; saída, mudança do processo ou fontes também recusam. O context manager fecha pidfd e diretório em sucesso/falha e invalida o handle depois da saída do contexto. Callbacks, backend e objetos internos são da fábrica root confiável, não um protocolo de capabilities público.

## Matriz real

Serviço reservado lyra-parental-running-probe.service, User=ordinaryuser UID1002/GID1003, Type=exec e payload C root-owned sob /usr/libexec. Contas, grupos, senhas, PAM e MAC mapping não mudam.

1. Unidade sem processo: referência de execução recusada.
2. Processo real identificado com credenciais/cgroup/executável/argv corretos.
3. Comentário realmente gravado no arquivo da unidade: referência antiga recusada por NeedDaemonReload.
4. Root restaura bytes e executa daemon-reload: stamps mudaram e a referência antiga continua recusada por Conflict.
5. Nova referência de configuração identifica o mesmo processo original.
6. SIGUSR1 selecionado pelo controlador root faz o payload executar /usr/bin/sleep. Mesmo PID830, ticks36581 e pidfd vivo; inode/hash/argv mudam e a referência é recusada.
7. Parada upstream exclusiva da fixture torna o pidfd antigo legível e invalida a referência.
8. Novo início cria processo PID1348, exigindo novo pin/observação.
9. Contas, PAM e broker PID454 permanecem preservados.

SIGUSR1 e systemctl start/stop são controles explícitos da fixture reservada. Não são um adaptador de revogação autorizado do produto, nem teste de interrupção de serviço compartilhado. O payload bloqueia SIGUSR1 durante a instalação do handler e usa sigsuspend para evitar perder o sinal no ensaio.

## Preservação e limites

Cleanup removeu exclusivamente unidade/executável reservados e recarregou systemd. Leitura independente confirmou ausência desses caminhos e lock não usado, unidade not-found/inactive/MainPID0/ControlGroup vazio, nenhum processo reservado, arquivos de todas as nove referências anteriores preservados, declarações D-Bus originais e contas/PAM intactos, broker preservado. A VM foi desligada e QEMU sessão68081 terminou exit0. Helpers/logs/binário compilado ficam em /root/running-reference-test; não se afirma rollback integral do disco ou do cache do manager. Sem instalação de RPM ou mudança no host, PAM de produto, receitas, OBS ou ISO.

A relação testada é do processo PRINCIPAL de uma única unidade reservada, não população completa/cgroup drenado, threads com credenciais próprias, namespaces alternativos, descendentes, trabalho de serviços root por outros UIDs, D-Bus ownership, ambiente/sandbox/MAC, todas capacidades ou ativação concorrente. Prm/Eff/Amb zero não prova impossibilidade de adquirir privilégio depois. Grupos implícitos extras e UID/GID diferentes são recusados conservadoramente; daemons legítimos que mudam argv/credenciais ficam fora deste subconjunto. Os três casos recusados na etapa anterior continuam recusados; não foram contornados nem certificados aqui.

Pidfd fixa a identidade da tarefa e permite observar saída, conforme [pidfd_open(2)](https://man7.org/linux/man-pages/man2/pidfd_open.2.html); este ensaio demonstra separadamente que não fixa seu executável. Leituras separadas de /proc/D-Bus não são snapshot atômico, não impedem ABA nem congelam exec/credenciais após o check. Não foi autorizado sinal a partir deste handle. Antes de integrar efeitos, é necessário provar inibição da ativação, revalidar fontes/população e usar a operação upstream apropriada, preservando serviços compartilhados. Reutilizar o gate isoladamente como certificado seria incorreto.

Risco de integração futura: divergência pode bloquear a conta; o fallback deve conservar a barreira e informar falha, nunca tratar Unsupported como conta comum. Hoje a mudança se limita a evidências/testes e pode ser revertida removendo o commit local. Controle parental integral continua NO-GO; #6/#102 abertas. full_account_protection/global_coverage/real_activation_or_revocation_adapter/shared_privileged_services permanecem false.

Próximo: conectar este vínculo ao backend do adaptador existente de unidades sob autorização e inibição já conferidas, com teste de mudança/reinício entre autorização e StopUnit; não duplicar um controlador novo. Depois cobrir descendentes/ativação pendente e os serviços privilegiados que não seguem a identidade simples.

## Conferência offline

`python3 docs/evidence/parental-running-reference/verify-evidence.py` confere hashes, fontes efetivamente executadas, ambas tentativas, retornos, controles e preservação. A suíte foi executada na worktree, não em export limpo. Provenance é consistência local sem assinatura independente.
