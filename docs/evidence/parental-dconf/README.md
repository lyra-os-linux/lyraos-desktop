# Preferências dconf na sessão restrita — 25/09/2026

**Ensaio de componente em VM; controle parental de produção continua desativado.**
Continua a [etapa de serviços GNOME](../parental-gnome-services/README.md).
O serviço oficial de preferências agora inicia dentro do domínio restrito,
grava e relê uma preferência comum e preserva o valor após reiniciar. O perfil
fixo continua impondo as configurações protegidas diante de valores conflitantes
no banco do usuário. Não altera receita, RPMs publicados ou host; #6/#102 abertas.

## Integração experimental

O executável `/usr/libexec/dconf-service` tinha execução negada por estar em
`bin_t`. A [política temporária](exercise.py) atribui um tipo específico a esse
binário oficial verificado e permite sua execução sem transição: serviço,
cliente e gerenciador permanecem em `lyra_parental_probe_t`. Não há domínio
irrestrito intermediário nem concessão de memória executável ao serviço.
Essa permissão também permite a execução direta pela conta; não é exclusiva
do chamador systemd.

Um tipo de dados próprio protege o diretório `~/.config/dconf` da conta fictícia
e os arquivos criados nele. Recebe escrita, substituição e monitoramento,
sem execução. O Shell pode ler/monitorar esse diretório. O ensaio exige
inicialmente a ausência desse diretório e o prepara com UID/GID 1003/1004 e
modo 0700. Não qualifica migração de bancos existentes nem persistência dos
rótulos em atualização/restorecon: a rotulagem desta fixture é temporária.

O [fonte oficial](source.json) dconf 0.40.0-160100.2.1 foi baixado, teve
assinatura verificada e coincide em NVR/DISTURL com a VM. A inspeção do engine
mostrou que as travas dos bancos do sistema afetam a leitura e escrita feitas
com aquele perfil. O writer continua armazenando o banco do usuário. Não houve
patch ou rebuild do dconf; foram usados serviço e bibliotecas oficiais.

## Resultados

O [probe nativo](settings-probe.c) usa GSettings e libdconf, operações fixas,
UID/contexto previstos e enforcing obrigatório. É instrumentação temporária;
não é uma aplicação aprovada para produção. Os [nove chamados](settings-controls.json)
passaram na [rodada final](summary.json):

| Verificação | Resultado |
| --- | --- |
| Gravar `clock-format=12h` e ler em outro processo | Valor persistido |
| Alterar três chaves protegidas com o perfil fixo | `writable=0`, alteração recusada |
| Gravar valores opostos com perfil alternativo contendo somente `user-db:user` | Escrita aceita no banco do usuário |
| Ler novamente com o perfil fixo | Valores protegidos continuam efetivos |
| Abrir perfil e banco do sistema para escrita | EACCES, sem modificar os arquivos |
| Criar cópia ELF no diretório de dados e tentar exec/mmap executável | Ambas negadas; auditoria registra SELinux |
| Reiniciar dconf e reler preferência/chaves protegidas | Persistência e travas preservadas |

As chaves são `allow-extension-installation=false`, `development-tools=false`
e `disable-user-extensions=true`, em `org.gnome.shell`. A escrita pelo perfil
alternativo **não foi bloqueada no banco do usuário**. O resultado válido é que
um consumidor com o perfil fixo continua ignorando esses valores conflitantes.
Isso depende do [launcher com ambiente fixo](../parental-xwayland/trusted-shell.c)
e dos arquivos de root; locks dconf sozinhos não são uma fronteira de segurança
para qualquer programa da conta. O teste consulta as chaves por um cliente
nativo com o mesmo perfil; não automatiza cliques na interface do Shell.

O serviço ficou `active/running`, sem reinícios automáticos. O reinício
intencional mudou o PID de 85696 para 86143, ainda no domínio restrito.
A [sessão](session.json) mostra banco com tipo `lyra_parental_settings_t`,
registro efetivo do GDM, janela X11 com moldura e Shell/XSettings com mesmos
PIDs durante a observação de 45 segundos herdada da etapa anterior.

Também passaram os [15 controles de execução/conta comum e quatro provas de
descritores](native-controls.json), as [dez falhas de configuração](config-faults.json)
e 221 testes Python do repositório. A [auditoria](audit.json) teve delta zero
de perdas e nenhum corte. Não converter um retorno zero do coletor em
aprovação de toda a sessão: os resultados funcionais estão separados.

## Pendências e recuperação

A sessão passou de 18 para **17 unidades com falha**, conforme a lista coletada:
15 SettingsDaemon, xdg-desktop-portal e xdg-permission-store. Hooks X11 de
recursos/acessibilidade e GeoClue também continuam pendentes. Notificações de
mudança para aplicações já abertas, recuperação de banco corrompido, múltiplos
logins, atualização/rollback e estabilidade prolongada não foram qualificados.
Continuam necessários admissão integral da conta, evasão, Vega e recuperação
do responsável antes de habilitar o produto.

O snapshot persistente inclui o executável dconf, o perfil alternativo e os
arquivos de teste. [A verificação final](restored.json) confirmou 13 pacotes
com `rpm -V` limpo, rótulos originais, diretório/banco de teste removidos e
ausência de recuperação pendente. GDM, user@1003 e auditd ficaram inativos,
backlog voltou a 64 e SELinux ao modo permissivo original da VM fora do ensaio.
Dependências de build permanecem instaladas.

## Reprodução

Usar somente a VM marcada `lyra.parental-selinux-test=1`, com os pré-requisitos,
builds diagnósticos e recuperação da [etapa XWayland](../parental-xwayland/README.md).
Reutilizar também `system-bus-probe.c` da etapa de serviços GNOME. A compilação
do novo probe requer `pkg-config gio-2.0 dconf` e libselinux.

Copiar `settings-probe.c` para `/root`; `exercise.py` como
`/root/xwayland-exercise.py`; `session.py` como
`/root/restricted-xwayland-session.py`. Executar a unidade transitória com
`RuntimeMaxSec=300`, `TimeoutStopSec=180` e
`ExecStopPost=/usr/bin/python3 /root/fixture_recovery.py`, usando o comando
documentado na etapa XWayland com esse limite atualizado. Não executar ensaios
simultâneos. Após terminar, conferir os resultados e executar
[verify-final.py](verify-final.py) antes de outro ensaio.
