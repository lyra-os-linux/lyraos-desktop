# Atalhos globais — 27/09/2026

**Integração experimental qualificada na VM descartável.** Continua
a [etapa dos auxiliares GNOME](../parental-helpers/README.md). Não habilita
controle parental em produção nem encerra #6/#102.

## Integração

A sessão anterior negava a execução de
`gnome-control-center-global-shortcuts-provider`, impedindo a interface de
consentimento do portal. O ensaio aprova somente esse executável nativo por
tipo SELinux dedicado. Ele permanece no domínio restrito da conta, sem conceder
execução genérica de `bin_t`, shell ou `execmem`.

Uma entrada D-Bus nativa fixa usa o renderizador Cairo e o perfil dconf do ensaio
para UID 1003. Rejeita argumentos adicionais e exige enforcing/contexto esperado
para essa conta. Não altera o comportamento de outros usuários. Executável,
serviço D-Bus e dados modificados são preservados pela recuperação durável.

Foi conferida a fonte SUSE exata `gnome-control-center-48.7-160100.2.1`, com
assinaturas e DISTURL correspondentes à versão instalada. Os arquivos upstream
do portal 1.20.4 e backend GNOME 48.0 servem como referências complementares,
sem afirmar que contêm todo o patchset SUSE. [Proveniência](shortcuts-sources.json).

## Correção upstream necessária na VM

O pacote SUSE `xdg-desktop-portal-gnome-48.0-160100.2.1` retornou erro ao autorizar
o atalho, embora o diálogo aparecesse. A fonte exata do SRPM confirmou que
`shell_grab_accelerators_done()` deixava o resultado de sucesso sem inicialização;
a atribuição ficava em outro callback. O arquivo coincide com o upstream 48.0.

O ensaio aplica somente a [correção oficial 54087eb](https://github.com/GNOME/xdg-desktop-portal-gnome/commit/54087ebf0b467b4193f1b40f3177f55d415eaa9c),
sem ampliar permissões SELinux para contornar a falha. `build-portal.py` compila
as fontes exatas e o submódulo incluídos no SRPM SUSE, aplicando
`globalshortcuts-success.patch` sem fuzz. O executável do RPM é preservado antes
da substituição temporária e restaurado ao terminar ou interromper a fixture.
`portal-build.json` registra comandos, versões e hash do build.

Essa compilação é uma variante de teste, não um RPM publicado. O backport ainda
precisa de empacotamento, qualificação para contas comuns e inclusão/verificação
da candidata antes de ser considerado entregue no produto.
Essa entrega é acompanhada na [issue #125](https://github.com/lyra-os-linux/lyraos-desktop/issues/125).

## Resultado funcional

A rodada completa **shortcuts1 passou** no [qualificador](qualify.py), que rejeita
diagnósticos abreviados. [Resumo](summary-shortcuts1.json),
[sessão nativa](session-shortcuts1.json), [auditoria](audit-shortcuts1.json),
[preparação e política](progress-shortcuts1.json) e
[restauração](restoration-shortcuts1.json).

O [diálogo de autorização](shortcuts-bind-shortcuts1.png) e o
[cancelamento](shortcuts-cancel-shortcuts1.png) foram exercitados por teclado QMP.
Cancelamento não deixou atalhos registrados; autorização devolveu sucesso,
com uma ativação e uma desativação. Outra conexão com o mesmo app ID teve
List/Bind recusados. Fechar a sessão interrompeu os sinais mesmo com nova
injeção da combinação e tornou a sessão indisponível para consulta.

As regressões de teclado, atalhos de comando, dconf, AT-SPI, XWayland, portais,
busca, áudio, notificações, gravação/decodificação e bloqueio passaram. As 31
consultas de limites da política passaram; zero unidades persistentes em falha
na amostra e zero perda/limitação da auditoria. As recusas remanescentes nos logs
continuam sendo limites da qualificação, não permissões a liberar automaticamente.

A [reprodução com o RPM original](unpatched-control.json) conserva a falha de
resposta e a [imagem do diálogo](unpatched-consent.png). Ela não conta como PASS.

```sh
python3 run.py shortcuts1 /caminho/LyraOS
python3 qualify.py shortcuts1
```

## Recuperação

`faultKillS1` e `faultTimeoutS1` passaram no
[qualificador de recuperação](qualify-recovery.py), com falhas provocadas em
enforcing, resultados `signal`/`timeout` do systemd, 106 arquivos restaurados,
stderr vazio e nenhuma recuperação pendente. [Evidências](recovery-tests.json).
O teste de timeout suspende os processos da unidade e aguarda o limite real de
300 segundos configurado no lançamento, seguido de `ExecStopPost`.

A [verificação final](verified-final.json) confirmou 26 RPMs íntegros, incluindo
GNOME Control Center e o backend original do portal, rótulos restaurados e
remoção de executáveis, `.desktop`, drop-ins e dados temporários. GDM, conta de
teste e auditd ficaram inativos; SELinux voltou ao estado permissive da VM fora
do ensaio. O módulo base do probe permanece, sem a política experimental da sessão.

```sh
python3 run.py faultKillS1 /caminho/LyraOS
python3 run.py faultTimeoutS1 /caminho/LyraOS
python3 qualify-recovery.py faultKillS1 faultTimeoutS1
```

## Contrato do ensaio

O probe C usa a API pública [GlobalShortcuts](https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.GlobalShortcuts.html)
e uma aplicação fictícia descrita por um `.desktop` temporário de root.
Registra sua conexão pela API upstream de aplicações nativas; esse registro
associa um nome à conexão, **não autentica a identidade de um aplicativo nativo**.
Catálogo e identidade de produção continuam pendentes.

O qualificador exige:

- Criar uma sessão inicialmente sem atalhos, abrir o diálogo e cancelá-lo por
  teclado QMP. A resposta deve negar o registro e a lista continuar vazia.
- Criar outra sessão, negar `ListShortcuts` e `BindShortcuts` a uma segunda
  conexão com o mesmo app ID e permitir operações do proprietário.
- Autorizar no diálogo real o atalho `Ctrl+Shift+F8`, listar o ID e sua descrição,
  injetar a combinação por QMP e receber exatamente um sinal `Activated` e um
  `Deactivated` para aquela sessão e ação.
- Fechar a sessão, repetir a combinação e não receber novos sinais; a sessão
  fechada deve recusar novas consultas.
- Preservar as regressões funcionais e de memória da etapa anterior, além das
  consultas de política que negam execução genérica de binários e shell.

Na implementação GNOME 48, Escape fecha o diálogo com `AccessDenied`, que o
backend converte em resposta 2. O teste exige recusa e ausência de registros;
não confunde esse comportamento com a resposta 1 de outros backends.

A captura de stdout passa por pipe; somente o coletor root grava a evidência.
A conta não recebe escrita em `/root`. Os ensaios não usam um cliente D-Bus
genérico aprovado para a conta, nem alteram as teclas do host.

## Limites

Um atalho autorizado entrega um sinal à aplicação; não aprova execução arbitrária
de comandos. A amostra não qualifica todos os conflitos de teclas, mudanças de
layout, persistência após reboot, revogação durante bloqueio de tela ou atalhos
de todos os aplicativos. Também não substitui os testes adversariais pendentes
das APIs Screencast/PipeWire, acessibilidade integral e entradas alternativas.

Requer a VM marcada, controlador em `analysis/2026-09-25/parental-gdm/` e
builds/probes das etapas anteriores. `run.py TAG /caminho/LyraOS` executa a rodada;
tags `diag*`/`fault*` fazem diagnóstico reduzido, recusado pelo qualificador completo.
Usar tags novas para evitar reutilizar unidades e logs de ensaios anteriores.

Antes da primeira rodada, preparar o build do backend na VM marcada. O script
`build-portal.py` requer `/root/shortcuts-portal-source.tar.zst` e
`/root/shortcuts-libgxdp.tar.zst` extraídos do SRPM registrado, o patch em
`/root/globalshortcuts-success.patch` e o RPM de desenvolvimento oficial em
`/root/shortcuts-portal-devel.rpm`. Executá-lo uma vez em diretórios de build
novos. Ele não instala o executável compilado; a fixture faz a substituição
temporária somente após criar o snapshot durável. A dependência de desenvolvimento
permanece instalada na VM e não integra os dados temporários da sessão.
