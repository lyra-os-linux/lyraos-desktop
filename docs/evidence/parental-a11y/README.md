# Acessibilidade nativa e descoberta AT-SPI no X11 — 25/09/2026

**Ensaio de componentes em VM; não habilita controle parental de produção.**
Continua a [etapa dconf](../parental-dconf/README.md). Integra o serviço oficial
`gsd-a11y-settings` no domínio restrito e substitui experimentalmente o hook
X11 de descoberta AT-SPI por um executável nativo. Não altera receita, host
ou pacotes publicados; #6/#102 continuam abertas.

## Problemas e proposta

O serviço A11ySettings não executava por ter o rótulo genérico `bin_t`.
Recebe um tipo específico na [política temporária](exercise.py), permanecendo
em `lyra_parental_probe_t`, sem ganhar memória executável ou transição para
um domínio irrestrito. A permissão permite também execução direta pela conta;
não distingue o systemd de outros chamadores no mesmo domínio.

O hook oficial `/usr/etc/xdg/Xwayland-session.d/00-at-spi` é um script que usa
shell, busctl, sed e xprop para copiar o endereço do barramento de acessibilidade
para a propriedade X11 `AT_SPI_BUS`. Sua execução continuava negada. O
[patch experimental](native-x11-hook.patch) troca a instalação desse script
por um pequeno [programa C](at-spi-x11.c), usando GDBus e Xlib diretamente.
Não há subprocesso, interpretação de comandos ou busca pelo PATH.

O programa consulta `org.a11y.Bus.GetAddress`, exige uma resposta string não
vazia de até 4096 bytes e publica XA_STRING/8 no root window. Retorna falha
se não consegue consultar o barramento ou abrir/publicar no display. Diferente
do script original, não trata falha de conexão como sucesso silencioso; rejeita
argumentos adicionais. Não é mediador de segurança de acesso ao barramento.

## Validação funcional

[O fonte oficial](source.json) AT-SPI 2.58.7-160100.2.1 teve assinatura verificada
e coincide em NVR/DISTURL com a VM. O [Meson oficial compilou o novo alvo](build.json).
A aplicação do patch foi [reproduzida em 502 arquivos idênticos](source-reproduction.json).
Isso não representa build ou qualificação de um RPM completo.

O [probe de preferências](a11y-settings-probe.c) alterna teclado de tela
ligado → desligado → ligado e observa o serviço atualizar
`toolkit-accessibility` nos três estados. Exercita notificações dconf entre
processos já abertos; não qualifica o uso visual do teclado de tela.

O [aplicativo de teste](accessible-app.c) abre uma janela GTK3 real com um botão.
O [cliente nativo libatspi](accessible-client.c), em processo separado, procura
esse botão na árvore de acessibilidade e confere nome e papel. Usa o display
X11 público, sem `WAYLAND_DISPLAY`/`AT_SPI_BUS_ADDRESS` e com endereço inválido
do barramento de sessão. Assim, depende da descoberta pela propriedade X11.

Os resultados da [sessão](session.json) e dos [controles](a11y-controls.json)
registram as etapas positivas e negativas, incluindo argumento inválido e
barramento ausente no novo hook. A propriedade é removida durante o teste:
um novo cliente falha sem os dois caminhos de descoberta; após o hook nativo
republicar o endereço, outro cliente volta a encontrar o botão.

As primeiras rodadas capturavam stdout/stderr do aplicativo em arquivos de
root e tiveram [escrita negada nesses logs](capture-denials.json). O coletor
final usa pipes, verifica a mensagem de prontidão e registra a saída do
processo. Não foi acrescentada permissão de escrita em diretórios de root.

A sessão também repete as provas dconf,
execução restrita, descritores, janela X11, registro GDM e autorizações Polkit
das etapas anteriores. Os 221 testes Python do repositório passaram.

A [rodada final](summary.json) confirmou A11ySettings `active/running` e
`NRestarts=0`, com 16 unidades restantes em falha. Passaram também os nove
chamados dconf, 15 controles de execução/conta comum, dez falhas de configuração
e quatro provas de descritores. A [auditoria](audit.json) teve delta zero de
perdas e nenhum corte. Os treze pacotes verificados foram restaurados; o hook
original voltou ao script e os probes foram removidos.

## Limites

O teste demonstra descoberta e leitura de uma árvore GTK/ATK real em enforcing.
Não qualifica Orca, síntese de voz, navegação por teclado, dispositivos assistivos,
acessibilidade de todos os aplicativos, cliente Wayland nativo ou mediação de
ações AT-SPI entre aplicativos. O hook de recursos `00-xrdb` continua bloqueado.
O aplicativo GTK avisou que não consegue gravar caches Fontconfig; a leitura
da árvore passou, mas cache de fontes e renderização visual ainda exigem
qualificação. Esses avisos permanecem na evidência, sem liberação genérica
de escrita nos diretórios da conta.
Os demais SettingsDaemon, portais, proteção de todas as entradas da conta,
evasão, Vega e recuperação continuam pendentes.

O novo tipo de executável é temporário. A substituição RPM, os contextos
persistentes e o comportamento em atualização/rollback ainda precisam ser
integrados e qualificados. Os probes são instrumentação da VM, não executáveis
de produto. O sucesso dos componentes não aprova a sessão completa.

## Reprodução e recuperação

Extrair o SRPM verificado e executar `prepare-source.py --sources DIRETORIO
--output DIRETORIO_NOVO`. Na VM marcada `lyra.parental-selinux-test=1`, colocar
a árvore resultante em `/root/at-spi2-core-2.58.7` e executar `build.py`.
O alvo esperado é `/root/atspi-hook-build/bus/00-at-spi`. A receita diagnóstica
usa prefix `/usr`, sysconfdir `/usr/etc`, X11 habilitado, introspecção/docs e
adaptador GTK2 desabilitados; somente o alvo do hook é compilado.

Reusar os pré-requisitos/builds diagnósticos, recuperação, launcher e probes
de XWayland, serviços GNOME e dconf. Copiar os três novos probes C desta etapa
para `/root`; `exercise.py` como `/root/xwayland-exercise.py`; `session.py`
como `/root/restricted-xwayland-session.py`. São necessárias as dependências
de desenvolvimento de gio-2.0, x11, gtk+-3.0, atspi-2 e libselinux.

Executar a unidade transitória com `RuntimeMaxSec=300`, `TimeoutStopSec=180`
e `ExecStopPost=/usr/bin/python3 /root/fixture_recovery.py`, conforme o comando
da etapa XWayland. Não executar ensaios simultâneos. O snapshot persistente
inclui o hook original e o daemon A11ySettings e remove os probes ao terminar.
Conferir resultados, auditoria e [restauração](restored.json) antes de novo ensaio;
[verify-final.py](verify-final.py) verifica também que o hook voltou ao script
oficial. Dependências e builds permanecem na VM; SELinux volta ao modo
permissivo original fora do ensaio.
