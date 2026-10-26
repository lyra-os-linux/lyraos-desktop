# ADR 0019: controle parental básico com malcontent e conta supervisionada

- Estado: aceita
- Data: 2026-10-26
- Substitui: [ADR 0008](0008-private-age-signal-and-parental-supervision.md)

## Contexto

A [ADR 0008](0008-private-age-signal-and-parental-supervision.md) propunha
sinal etário privado, conta supervisionada com proteção contra evasão e
camadas próprias de aplicação de políticas. Os ensaios de setembro mostraram
que esse desenho não se sustenta na base: o confinamento por lista de
programas aprovados é contornado por qualquer interpretador permitido
(`parental-confinement-20260921.json`), e o Flatpak do Leap não aplica o
malcontent (#102). Em 07/10 o mantenedor congelou o desenho completo e, em
25/10, aprovou um [plano](../parental-controls-plan.md) para um controle
parental **básico**.

A [qualificação de 26/10](../parental-controls-upstream-qualification.md)
(matriz R1–R23) mediu o que o upstream entrega no Lyra 16.1 e o que falta
integrar.

## Decisão

O Lyra OS 16.1 entrega controle parental básico, para uma criança comum, com
componentes do GNOME e do openSUSE:

1. **Regras:** malcontent e o aplicativo upstream "Controle parental"
   (`malcontent-control`): navegadores, aplicativos, instalação e
   classificação etária, gravados no AccountsService.
2. **Conta supervisionada:** grupo `lyra-supervised`, do pacote
   `lyra-parental-controls`, que também:
   - nega SSH (`DenyGroups`) e login por TTY (`pam_access` só no serviço
     `login`, numa cópia de `/etc/pam.d/login` conferida contra a do
     fornecedor no build);
   - trava o Alt+F2 num perfil dconf próprio da conta;
   - traz a regra polkit de leitura do malcontent, para o GNOME Settings
     mostrar o estado real.
3. **Vega:** só marca a conta e abre o "Controle parental". O vegad recusa
   conta supervisionada que seja administradora, protege o último
   administrador e, ao supervisionar, esconde Console, `gnome-terminal`, fish
   e Vega pelo filtro do malcontent. Sem mudança no contrato D-Bus.
4. **Sheliak:** menus, busca e fixados usam o `ParentalControlsManager` do
   GNOME Shell.
5. **Flatpak opcional:** o `flatpak` não vem instalado. O administrador o
   habilita no Vega, depois de um aviso para contas supervisionadas. O
   LinuxToys também deixa a imagem, porque instalaria o `flatpak` sozinho.
6. **Sem sinal etário** nesta versão, salvo exigência do parecer jurídico
   (frente 6 do plano).

## Consequências

- O controle não resiste a uma criança com conhecimento técnico: atalhos
  `.desktop`, scripts e macros próprios, e programas baixados na pasta pessoal
  ainda executam. Esse limite aparece no Vega e na documentação.
- Com o Flatpak habilitado, a criança pode instalar e abrir apps Flatpak até o
  openSUSE compilar o `flatpak` com malcontent.
- `/etc/pam.d/login` sombreia o arquivo do fornecedor; o `%check` do pacote
  falha quando o `util-linux` muda o original.
- A correção de segurança do `sudo` (#191, #192), encontrada na qualificação,
  é pré-requisito: sem ela qualquer conta virava administradora.
- O gate #9 ([parental-controls-gate.md](../parental-controls-gate.md)) entra
  na candidata a partir da RC 3.
- [vega-parental-controls-ux.md](../vega-parental-controls-ux.md) e
  [parental-protection-boundary.md](../parental-protection-boundary.md) ficam
  como histórico do desenho anterior.
