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
- resistência a uma criança com conhecimento técnico: atalhos `.desktop`, scripts
  e macros próprios ainda executam comandos (qualificação R23);
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

> Substituída em 26/10/2026: o `flatpak` deixou de vir instalado e é habilitado
> pelo Vega com aviso (ver "Decisões do mantenedor"). O texto abaixo fica como
> registro da proposta original.

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

## Cronograma (atualizado em 26/10/2026)

O trabalho andou mais rápido que o previsto: em 26/10 ficaram prontas e
publicadas todas as frentes, exceto a 6, que depende do parecer jurídico. O
cronograma diário anterior (frentes até 13/11 e RC 3 em 16/11) fica superado.
Como nenhuma ISO da RC 2 do Desktop tinha sido publicada, a candidata com o
controle parental passa a ser a **RC 2**, não uma RC 3 (decisão de 26/10).

### Feito em 26/10

| Frente | Entrega |
| --- | --- |
| 1 | Qualificação em VM, matriz R1–R23 e decisões (#193) |
| Segurança | `sudo` restrito ao `wheel` (#191, #192), publicado |
| 2 | Imagem com o Controle Parental (#195) |
| Sheliak | 2.0.6 respeita o filtro do malcontent (sheliak#40), publicado |
| 3 | `lyra-parental-controls`: grupo, SSH, TTY, Alt+F2, regra de leitura e dependências (#196, #197, #199), publicado |
| 5 | Flatpak e LinuxToys fora da instalação padrão; Flatpak habilitado pelo Vega com aviso (#198, #200, vegad#91) |
| 4 | Vega 5.3.0 e vegad 5.1.42: conta supervisionada e "Habilitar Flatpak" (vega#160, vegad#92), publicados |
| 7 | Gate #9 (#201), ADR 0019 (#202), página do site (site#7) e issues |

### Feito em 27/10

O gate da RC 2 achou quatro defeitos, todos anteriores ao controle parental,
e cada um gerou um novo build: Bluetooth sem adaptador e serviço pulado por
condição (vegad 5.1.44, vega-gtk 5.3.2), "Atualizar tudo" deixando pacotes
para trás (vegad 5.1.45, relatado pelo mantenedor), nomes de rede com acento
(vegad 5.1.46) e a tela da live que travava sem como destravar (#209). A
candidata é o build #10.

### Cronograma (atualizado em 27/10/2026)

Lançamento da 16.1 em **05/11**; 26/11 continua como data-limite.

| Data | Trabalho | Responsável |
| --- | --- | --- |
| 27/10 (ter) | Terminar o gate do build #10 (BIOS e UEFI sem NVRAM); se passar, ele é a RC 2 | Claude, com o mantenedor nas instalações pela interface |
| 28/10 (qua) | Flatpak no Vega: reproduzir, corrigir e publicar (staging, VM, SR); chega à RC 2 por atualização, sem novo build da ISO | Claude |
| 28/10 (qua) | Importar a chave da release e assinar o build #10 (`--artifacts-only`) | Mantenedor |
| 29/10 (qui) | Publicar a RC 2: SourceForge, PR do site e anúncio | Claude prepara, mantenedor aprova |
| 29/10 (qui) | Server RC 3 (Delos) com o vegad 5.1.46, em paralelo | Claude |
| 29/10–02/11 | Teste público da RC 2; só entram correções de defeito bloqueante | Todos |
| 02/11 (seg) | Congelamento: identidade final `16.1` e notas da versão | Claude |
| 03/11 (ter) | Build final e gate completo (UEFI com Secure Boot, BIOS, sem NVRAM, rollback) | Claude, com o mantenedor nas instalações |
| 04/11 (qua) | Assinatura, upload e site | Mantenedor e Claude |
| 05/11 (qui) | Lançamento do Lyra OS 16.1 "Odisseia" | Mantenedor |

Riscos e alternativas:

- Com sinal de idade (frente 6): 2 a 5 dias a mais, só se o parecer exigir;
  o lançamento passa para 12/11.
- Defeito bloqueante na RC 2: RC 3 em 05/11 e lançamento em 12/11 ou 19/11.
- A chave da release é o único passo exclusivo do mantenedor; sem ela, nada
  é publicado.

Depois do lançamento: LinuxToys 7.7.3, promoção do lyra-upgrade 0.2.9,
conferência do RTD3 da NVIDIA (vegad#78), decisão sobre o Sulafat em contas
supervisionadas e a fase 2 (#125, #102, #22).
- O bug no openSUSE para o `flatpak` com malcontent é opcional e fica com o
  mantenedor; não bloqueia a 16.1.

## Impacto na 16.1

- Exceção ao congelamento: imagem, Vega, um pacote novo e o `flatpak`.
- Os builds #4 a #6 da RC 2 não foram publicados; a RC 2 publicada será o
  build com o controle parental e o gate completo.
- A chave de assinatura da release continua pendente, qualquer que seja a
  data.

## Decisões do mantenedor

1. Lançar a 16.1 em 05/11 sem controle parental ou adiar para a data acima.
2. Exceção de prioridade para o `flatpak` do Lyra (frente 5) ou plano B.
   **Decidido em 26/10: exceção + bug na SUSE.**
3. Se o parecer jurídico exige o sinal de idade (frente 6).
4. Nomes `lyra-supervised` e `lyra-parental-controls`. **Aprovados em 26/10.**

A qualificação da frente 1 acrescentou a correção do Sheliak (1–1,5 dia) e
mais duas decisões de 26/10: bloquear o TTY e não incluir o `yelp`.

**Exceção ao congelamento decidida em 26/10 (substitui a decisão 2):** o
`flatpak` deixa de vir instalado. O administrador o habilita na página Software
do Vega, que instala o pacote depois de um aviso (o parágrafo sobre contas
supervisionadas aparece se houver alguma); o Flathub vem de
`/etc/flatpak/remotes.d`. Saem o `flatpak` próprio do Lyra e a exceção de
prioridade no `repository-policy`; o bug na SUSE continua. Quem já instalou uma
RC mantém o Flatpak e vê o aviso na tela de conta supervisionada (frente 4). O
LinuxToys também deixa de vir instalado, porque instalaria o `flatpak` por
conta própria. Frente 5 passa de 3–5 para 2–3 dias. Detalhes e
reestimativa em [parental-controls-upstream-qualification.md](parental-controls-upstream-qualification.md).
