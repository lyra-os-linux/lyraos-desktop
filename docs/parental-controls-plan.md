# Plano de desenvolvimento do controle parental básico

Estado: plano aprovado pelo mantenedor em 25/10/2026; trabalho começa em 26/10/2026. Substitui, como
direção de trabalho, o desenho congelado em 07/10/2026 (comentário no épico
#11). Os documentos anteriores (`parental-protection-boundary.md`,
`vega-parental-controls-ux.md`, ADR 0008) ficam como referência e serão
revisados na frente 7.

## Objetivo

Controle parental **básico** para uma criança numa conta comum, usando o que o
GNOME e o openSUSE Leap 16.1 já entregam e mantêm.

Fora do escopo, e escrito assim na interface e na documentação:

- resistência a quem tem senha de administrador, live USB ou acesso ao disco;
- filtro de conteúdo web e histórico de navegação;
- bloqueio de aplicativos RPM (o malcontent só lista aplicativos Flatpak).

## Responsabilidades

| Parte | Responsável |
| --- | --- |
| Regras (aplicativos, classificação etária, instalação de software) | malcontent, configurado pelo app "Controle Parental" (`malcontent-control`) |
| Marcação da conta supervisionada | grupo de sistema `lyra-supervised` |
| Bloqueio de login por TTY e SSH | pacote `lyra-parental-controls`, ativado pelo grupo |
| Criar e marcar a conta; abrir o Controle Parental | Vega (sem regras próprias) |

## Frentes de trabalho

### 1. Qualificação em VM (2 dias)

Prova sem código numa VM Leap 16.1 descartável, com administrador e criança:

- `malcontent-control`: gravação, persistência e se a criança consegue remover
  a política;
- integração do painel Usuários do GNOME Settings 48 com o malcontent;
- se o GNOME Software 48 do openSUSE respeita a restrição de instalação;
- comportamento com RPM, navegador e terminal.

Saída: `docs/parental-controls-upstream-qualification.md` reescrito para a
16.1, com a matriz requisito → atendido pelo upstream / integração / lacuna.
Essa matriz ajusta o tamanho das frentes 3, 4 e 5.

### 2. Imagem (`lyraos-desktop`, 1 dia, 1 PR)

- `kiwi/config.xml`: `malcontent-control` e `typelib-1_0-MalcontentUi-1` (hoje
  só `malcontent-lang`).
- `check-gnome-image.py`: exigir os dois pacotes.
- Notas da release com a exceção ao congelamento.

### 3. Pacote `lyra-parental-controls` (`lyraos-desktop/packaging/`, 1–2 dias, 1 PR)

- Cria o grupo de sistema `lyra-supervised`.
- SSH: `/etc/ssh/sshd_config.d/50-lyra-supervised.conf` com
  `DenyGroups lyra-supervised`.
- TTY: `pam_access` só no serviço `login`, com `accessfile` próprio, sem tocar
  no GDM nem na pilha comum. O mecanismo sai da frente 1; sem forma limpa no
  Leap 16.1, fica só o SSH e a lacuna é registrada.
- `%check`: `sshd -t` com o drop-in e validação da regra.
- Entrada no `obs/projects.toml` e promoção pelo fluxo normal.

### 4. Vega (`vegad` e `vega`, 2–3 dias, 2 PRs)

O contrato `org.lyraos.Vega1` não muda: `CreateUser`/`UpdateUser` já recebem
`groups`, e `ListUsers` já devolve os grupos.

- `vegad`: recusar administrador + `lyra-supervised` na mesma conta e impedir
  que a última conta administradora vire supervisionada; testes de unidade.
- `vega` (Tauri), página Usuários: interruptor "Conta supervisionada", selo na
  lista, botão "Abrir Controle Parental" (`malcontent-control`, autorizado
  pelo polkit do próprio malcontent) e um quadro com o que a supervisão cobre
  e o que não cobre. Textos em pt, en e es.

### 5. Flatpak com malcontent (#102, 3–5 dias)

O `flatpak` oficial do Leap 16.1 vem com `-Dmalcontent=disabled`: as regras de
aplicativos Flatpak ficam gravadas, mas não são aplicadas.

Um `flatpak` do Lyra com o mesmo nome perde para o oficial depois da
instalação, porque o instalador põe os repositórios do Lyra na prioridade 90.
Proposta:

- bug na SUSE pedindo `-Dmalcontent=enabled`, com a evidência do #102;
- até a correção chegar, `flatpak` do Lyra com exceção explícita e temporária
  no `repository-policy` (como a do Packman), preservada pelo instalador.

Testes: execução e instalação negadas (por usuário e por sistema), portais
FileChooser, Documents e ScreenCast, AccountsService indisponível (o upstream
libera a execução; vira limitação documentada), atualização e rollback com
Snapper.

Plano B, se a exceção for recusada: não bloquear Flatpak e dizer isso no Vega
e na documentação.

### 6. Sinal de idade (só se o parecer jurídico exigir, 2–5 dias)

Faixa etária por conta, gravada pelo administrador e legível só pela própria
conta e pelo administrador. Sem documento, biometria ou histórico. Fica no
`vegad`, com método novo no contrato (nova tag do `lyra-vega-dbus` e
atualização dos consumidores).

### 7. Gate, documentação e issues (2–3 dias)

- Gate #9: script em `kiwi/test/guest/` que cria a criança, aplica as regras e
  tenta contornar (aplicativo RPM, Flatpak negado, `flatpak run`,
  `flatpak install`, GNOME Software, TTY, SSH, `su`/`pkexec` sem senha),
  depois reinicia, atualiza e faz rollback. Resultado na evidência JSON.
- ADR nova substituindo a 0008 pelo desenho simples; revisão do
  `vega-parental-controls-ux.md`.
- Site: página "Controle parental" para responsáveis (pt, en, es, it), com os
  limites.
- Issues: reescrever #2, #5, #7 e #8 para o escopo novo, fechar #4 como
  referência, atualizar #11 e #102.

## Ordem e dependências

```
1 Qualificação ──┬─> 2 Imagem
                 ├─> 3 lyra-parental-controls ─┐
                 ├─> 4 vegad ─> 4 vega ────────┼─> 7 Gate + docs ─> RC com controle parental
                 └─> 5 Flatpak ────────────────┘
   6 Sinal de idade em paralelo, se o parecer exigir
```

Depois da frente 1, as frentes 2 a 5 andam em paralelo.

Esforço: 12 a 16 dias de trabalho; 14 a 21 com o sinal de idade.

## Cronograma por dia (início em 26/10/2026)

Dias úteis, com os feriados nacionais de 02/11 e 20/11. As frentes 2 a 5 são
independentes entre si, mas são feitas em sequência, uma de cada vez.

### Semana 1: qualificação e pacote

| Dia | Frente | Trabalho |
| --- | --- | --- |
| Seg 26/10 | 1 | VM Leap 16.1 com snapshot, conta administradora e conta da criança. `malcontent-control`: gravação, persistência e se a criança consegue remover a política. |
| Ter 27/10 | 1 | Painel Usuários do Settings 48, restrição no GNOME Software, RPM, navegador e terminal. Confirmar o #102 no `flatpak` oficial e definir o mecanismo do `pam_access` no TTY. |
| Qua 28/10 | 1 | Matriz em `parental-controls-upstream-qualification.md` (PR), bug na SUSE sobre o `flatpak` e reestimativa das frentes 3 a 5. Decisões 2 e 4 do mantenedor. |
| Qui 29/10 | 2, 3 | PR da imagem (`config.xml` e `check-gnome-image.py`). Início do spec do `lyra-parental-controls`: grupo e drop-in do sshd. |
| Sex 30/10 | 3 | `pam_access`, `%check` e `obs/projects.toml`; PR e staging. |

### Semana 2: Vega e Flatpak

| Dia | Frente | Trabalho |
| --- | --- | --- |
| Seg 02/11 | — | Feriado (Finados). |
| Ter 03/11 | 4 | `vegad`: recusar administrador + supervisionada e proteger a última conta administradora. Testes, PR e release. |
| Qua 04/11 | 4 | `vega`, página Usuários: interruptor, selo e botão "Abrir Controle Parental". |
| Qui 05/11 | 4 | `vega`: quadro com o que a supervisão cobre e o que não cobre, textos em pt, en e es; PR e release. |
| Sex 06/11 | 5 | `flatpak` com `-Dmalcontent=enabled` no staging e exceção no `repository-policy`. |

### Semana 3: Flatpak, gate e RC 3

| Dia | Frente | Trabalho |
| --- | --- | --- |
| Seg 09/11 | 5 | Instalador preservando a exceção. Execução e instalação negadas, por usuário e por sistema. |
| Ter 10/11 | 5 | Portais, AccountsService indisponível, atualização e rollback com Snapper. Promoção dos pacotes. |
| Qua 11/11 | 7 | Script do gate #9 em `kiwi/test/guest/`. |
| Qui 12/11 | 7 | ADR substituindo a 0008, revisão do `vega-parental-controls-ux.md`, site (pt, en, es, it) e issues #2, #4, #5, #7, #8, #11 e #102. |
| Sex 13/11 | — | Build da RC 3 e gate completo da ISO. |

### Semanas 4 e 5: margem e lançamento

| Dia | Trabalho |
| --- | --- |
| 16–19/11 | Margem para Flatpak, portais, correções do gate e novo build, se necessário. |
| Sex 20/11 | Feriado (Consciência Negra). |
| 23–25/11 | Release check, notas da release e chave de assinatura. |
| **Qui 26/11** | **Lançamento da 16.1 com controle parental (data realista)** |

São 13 dias de trabalho, dentro da estimativa de 12 a 16.

- Otimista: 19/11, se a Flatpak não trouxer surpresas.
- Com sinal de idade (frente 6): consome a margem; lançamento em 03/12.
- Com o plano B da Flatpak: a semana 3 fica 2 a 3 dias mais curta.

## Impacto na 16.1

- Exceção ao congelamento: imagem, Vega, um pacote novo e o `flatpak`.
- O build #6 da RC 2 segue como validação do vegad 5.1.41; a candidata final
  passa a ser uma RC 3 com o controle parental e o gate completo.
- A chave de assinatura da release continua pendente, qualquer que seja a
  data.

## Decisões do mantenedor

1. Lançar a 16.1 em 05/11 sem controle parental ou adiar para a data acima.
2. Exceção de prioridade para o `flatpak` do Lyra (frente 5) ou plano B.
3. Se o parecer jurídico exige o sinal de idade (frente 6).
4. Nomes `lyra-supervised` e `lyra-parental-controls`.
