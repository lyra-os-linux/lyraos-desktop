# Ativação do autostart XDG restrito — 22/09/2026

Continuação dos [geradores nativos](../parental-user-units/README.md).
A política SELinux da etapa anterior permanece inalterada. Nenhuma mudança
na receita, nos pacotes ou no host.

## O que foi exercitado

Os targets oficiais graphical-session.target e xdg-desktop-autostart.target
recusam início manual. O ensaio cria um target fictício com as dependências
apropriadas, como faria um componente de sessão, e o inicia pelo systemctl
executado no domínio restrito. Não remove RefuseManualStart das unidades.

Cinco arquivos .desktop fictícios são instalados por root em /etc/xdg/autostart
antes de iniciar o gerenciador. O gerador produz exatamente as quatro unidades
esperadas: executável aprovado, aprovado OnlyShowIn=GNOME, aprovado
OnlyShowIn=KDE e helper aprovado tentando executar Python. A quinta entrada,
Python diretamente, não produz unidade. O ambiente do gerenciador recebe
XDG_CURRENT_DESKTOP=GNOME para exercitar as condições.

`exercise.py` / `result.json` confirma:

- O programa aprovado inicia pela dependência do target, UID1003 e contexto
  lyra_parental_u:lyra_parental_r:lyra_parental_probe_t:s0 no journal do filho.
- A condição GNOME permite o aprovado; a condição KDE impede sua execução.
  O journal registra explicitamente Skipped due to exec-condition para este.
- O helper aprovado é iniciado, mas sua tentativa de executar Python recebe
  EACCES; a unidade termina126. Portanto, ativar por dependência não remove
  a restrição do processo filho.
- O gerenciador encerra ainda em enforcing. Arquivos de teste são removidos e
  permissive é restaurado somente na limpeza da fixture.

O helper aprovado é um instrumento de ensaio, não um aplicativo do produto.
Os .desktop são criados por root; overrides/autostart persistente criados pela
criança, links, múltiplas sessões e aplicativos reais continuam pendentes.
O teste confere o conjunto exato de unidades geradas e identifica o contexto
do processo em cada caso positivo; atingir o target sozinho não é aprovação.

## Limite da evidência e próximo passo

**Não é uma sessão GNOME completa.** `readiness.json` confirma que esta VM não
tem gdm, gnome-shell ou gnome-session instalados. Tem zypper e aproximadamente
3,3GB livres no disco de6GB. XDG_CURRENT_DESKTOP é apenas o ambiente da fixture;
não representa execução de GNOME Shell, GDM, compositor ou interação visual.

Próximo: preparar uma VM com componentes GNOME oficiais, conferir resolução de
dependências/espaço/recursos gráficos e qualificar GDM, sessão e portais com a
política restrita. O script gerador Flatpak ainda precisa de integração
específica, sem permitir shell genérico à conta. Permanecem entradas
TTY/SSH/cron/lingering, identidade de produção e recuperação. #6/#102 abertas.
Não há material pronto para publicar no OBS nem ISO qualificada nesta etapa.

Reproduzir somente na VM marcada lyra.parental-selinux-test=1, com os geradores
e helpers da etapa anterior. O script preserva os targets oficiais e não deve
ser executado em contas reais. Resultado positivo final sem alteração adicional
de política; regressões de execução anteriores permanecem na etapa anterior.

VM desligada após sync. Checkpoint persistente mais recente:
`analysis/2026-09-22/parental-graphical/system-checkpoint.raw` (não versionado).
Launcher/control: `analysis/2026-09-21/parental-selinux/`.
