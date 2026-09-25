# Registro GDM e XSettings na sessão restrita — 25/09/2026

**Etapa experimental em VM; proteção parental de produção continua desativada.**
Continua o [ensaio XWayland](../parental-xwayland/README.md). A política
temporária permite ao Shell conversar com GDM, AccountsService e Polkit e
permite executar o XSettings oficial no domínio restrito da conta. Não muda
pacotes publicados, receita ou host. #6/#102 continuam abertas.

## Mudança e fronteira

A [política do ensaio](exercise.py) acrescenta transporte D-Bus bidirecional
entre o domínio Shell e `xdm_t`, `accountsd_t` e `policykit_t`. Essas regras
não filtram métodos; a autorização interna de cada serviço continua necessária.
O helper `/usr/libexec/gsd-xsettings`, de propriedade de root e verificado
contra o pacote oficial, recebe um tipo de executável específico. Continua
em `lyra_parental_probe_t`, sem ganhar a memória executável do Shell. A conta
pode executar esse helper diretamente; a regra não distingue o systemd de
outros chamadores no mesmo domínio.

O [probe nativo](system-bus-probe.c) faz operações fixas: consulta a versão do
GDM e a identidade da própria conta, depois consulta duas autorizações Polkit
sem interação. Não altera contas ou unidades. O programa é uma entrada
instrumentada temporária no domínio Shell, removida ao terminar; não é um
launcher de produto. As checagens de UID/contexto não substituem o launcher
com ambiente sanitizado da etapa anterior.

## Resultados e limites

Os [registros da sessão](session.json) contêm a confirmação do GDM
`session registered: yes` para um display não nulo. Consultar apenas a versão
ou receber sucesso em `RegisterSession` não seria suficiente: o código oficial
do GDM também completa esse método quando não encontra um display.

Na [rodada final](rounds.json), o Shell (PID 84839) e o XSettings (PID 85230)
preservaram seus PIDs durante 45 segundos; `RESOURCE_MANAGER` continuou
acessível ao fim. O XSettings ficou `active/running`, com `NRestarts=0`. Os alvos de prontidão
do GNOME ficaram ativos. O primeiro pedido do XSettings teve falha de
dependência antes da ativação do XWayland sob demanda; o serviço iniciou
quando o cliente X11 acionou essa ativação. Isso não aprova a inicialização
completa da sessão.

As consultas de identidade e transporte passaram. As ações
`org.freedesktop.accounts.user-administration` e
`org.freedesktop.systemd1.manage-units` responderam `allowed=0, challenge=1`:
sem autorização automática, com autenticação administrativa disponível.
Não foi exercida uma alteração privilegiada nem qualificado todo o Polkit.

A janela X11 recebeu moldura (`0,0,37,0`), a consulta pública e a leitura/escrita
da propriedade interna passaram. Os controles de execução da etapa anterior
continuaram negando shell, Python, carregador, cópia ELF, memória anônima e
execução direta dos componentes reservados ao compositor. A conta comum
continuou executando Python. As falhas de configuração e provas de descritores
também foram repetidas: 15 controles de execução/conta comum, dez falhas
de configuração e quatro provas de descritores; consultar
[controles nativos](native-controls.json) e [falhas](config-faults.json).
Os 221 testes Python do repositório passaram.

A [auditoria](audit.json) registrou delta zero de perdas e nenhum corte. Ainda contém
negações esperadas e falhas reais. Sucesso do processo de coleta significa
apenas conclusão do ensaio/restauração, não aprovação da sessão inteira.

## Pendências identificadas

- [Os hooks oficiais](hooks.json) `00-xrdb` e `00-at-spi` continuam bloqueados. O primeiro lê recursos X11 do
  sistema e do usuário; o segundo copia o endereço do barramento de
  acessibilidade para a propriedade X11 `AT_SPI_BUS`, usando shell, busctl,
  sed e xprop. Acessibilidade X11 não está qualificada. Não liberar execução
  genérica de shell para resolver esses hooks.
- Persistem bloqueios de monitoramento de fontes/módulos GTK, leitura de
  diretórios e acesso a `udmabuf`. Verificar o efeito de cada um antes de
  conceder permissões; não converter a auditoria inteira em regras allow.
- GeoClue, outros SettingsDaemon, dconf, permission-store/portais, aplicações
  reais e acessibilidade ainda exigem integração e testes. A lista de unidades
  com falha da rodada final (18 unidades) fica na evidência da sessão.
- Continuam pendentes admissão de todas as entradas da conta, evasão,
  recuperação do responsável, integração Vega e candidata ISO exata.

O [SRPM oficial](source.json) de gnome-settings-daemon coincide em NVR e
DISTURL com o instalado e teve assinatura verificada. Foi inspecionado para
entender os hooks; não houve rebuild ou patch do GSD nesta etapa. O ensaio
continua dependendo dos builds diagnósticos GDM/Mutter/XWayland anteriores.

## Reprodução e recuperação

Usar exclusivamente a VM marcada `lyra.parental-selinux-test=1`, com os
pré-requisitos e os builds descritos na etapa XWayland. Reutilizar dali
`fixture_recovery.py`, `audit_capture.py`, `trusted-shell.c`,
`config-faults.py`, `fd-probe.c` e `xwindow-test.c`, com os nomes de instalação
indicados naquele relatório. Copiar desta etapa `system-bus-probe.c` para
`/root`; `exercise.py` como `/root/xwayland-exercise.py`; `session.py` como
`/root/restricted-xwayland-session.py`.

Executar a unidade transitória com `RuntimeMaxSec=240`, `TimeoutStopSec=180`
e `ExecStopPost=/usr/bin/python3 /root/fixture_recovery.py`, conforme o comando
da etapa anterior. A sessão acrescenta 45 segundos de observação dos PIDs
Shell/XSettings e repete a leitura de `RESOURCE_MANAGER` ao final. Esse
intervalo não demonstra estabilidade prolongada.

O snapshot persistente inclui agora o XSettings e remove o probe de barramento.
Esperar a unidade terminar antes de coletar ou iniciar outro teste. Executar
[verify-final.py](verify-final.py) e conferir [restored.json](restored.json):
onze pacotes verificados, rótulo original do XSettings, fixtures removidas,
serviços de teste parados e backlog de auditoria restaurado. Dependências de
build continuam na VM e SELinux volta ao modo permissivo original fora do teste.
