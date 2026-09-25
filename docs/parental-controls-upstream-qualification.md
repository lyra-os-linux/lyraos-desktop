# Qualificação upstream de controles parentais

## Reavaliação Leap 16.1 — 21/09/2026

**A disponibilidade dos pacotes foi confirmada; a integração parental continua
reprovada.** O Flatpak oficial não aplica o filtro no ensaio abaixo.
Esta avaliação substitui as conclusões de indisponibilidade e de exclusão da
interface GNOME feitas para Leap 16.0. A decisão de produto de 16/09 permanece:
avaliar serviço e interface upstream antes de duplicá-los no Vega.

### Origem e compatibilidade dos pacotes

Consulta direta ao repositório oficial Leap 16.1 confirmou `malcontent`,
`malcontent-control`, `libmalcontent-0-0`, `libmalcontent-ui-1-1` e
`malcontent-lang` **0.12.0-160100.2.1**. Checksums conferem com o primary
referenciado pelo repomd; os cinco RPMs têm assinatura válida SUSE `09d9ea69`.
A origem de compilação é `SUSE:SLFO:1.3`, não um projeto pessoal.
A consulta `/source/openSUSE:Leap:16.1/malcontent` retornou 404, mas não demonstra
ausência de binários: o repositório da distribuição os contém.

As dependências foram resolvidas pelo zypper com apenas o repositório oficial,
numa VM descartável. Foram instalados AccountsService 23.13.9 e Flatpak
1.16.6-160100.2.3. Nenhuma conta ou pacote da estação foi modificado.
A receita Lyra referencia `malcontent-lang`; isso não comprova seleção explícita
da interface, ativação de políticas ou aplicação de restrições.

### Ensaios executados

Conta fictícia `parentaltest`, sem grupos administrativos, em VM marcada
`lyra.virtualization-test=1`. O administrador do ensaio gravou uma blocklist via
`malcontent-client`, incluindo um caminho e uma referência Flatpak completa.

| Cenário | Resultado observado |
| --- | --- |
| Administrador grava política | Passou |
| Usuário consulta a própria política | Passou |
| Usuário tenta remover a política, sem interação Polkit | Negado, código 2; política permaneceu |
| Consulta do caminho bloqueado | Negada, código 3 |
| Reinício do AccountsService | Política preservada, mesmo hash |
| Execução direta de `/usr/bin/true` bloqueado | Executou, código 0; sem enforcement de execve |
| Flatpak mínimo permitido | Executou, código 0 |
| Mesmo Flatpak após blocklist explícita | **Executou, código 0; restrição não aplicada** |

O teste Flatpak usa runtime/aplicativo mínimos locais, instalados pelo
administrador somente na VM. A conta consulta o mesmo ref
`app/org.lyra.TestApp/x86_64/stable` e recebe negação, enquanto
`flatpak run org.lyra.TestApp` inicia normalmente. Não é uma inferência baseada
apenas na aparência do menu. O teste esperado de bloqueio falhou; o resultado
não foi convertido em aprovação para obter um gate verde.

O SRPM oficial assinado `flatpak-1.16.6-160100.2.3.src.rpm` explica o resultado:
`flatpak.spec:228` configura **`-Dmalcontent=disabled`**. O histórico da receita
atribui a desativação, em 23/04/2024, a problemas com xdg-desktop-portal.
Não remover essa opção e promover o pacote sem investigar essa regressão e
qualificar os portais. Habilitar o suporte Flatpak tampouco resolveria execução
direta de RPMs ou filtragem de conteúdo no navegador.

### Decisão e trabalho restante

1. Manter a interface GNOME como candidata, sem criar UI/daemon Lyra duplicados.
2. Investigar a integração Flatpak/malcontent com o mantenedor da base e testar
   uma correção isolada em staging, incluindo portais, autorização e rollback.
3. Testar UI original com administrador/conta supervisionada, cancelamento,
   instalação Flatpak por usuário/sistema, ausência do serviço e três idiomas.
4. Completar a matriz RPM/navegadores/execução direta e separar os requisitos
   não atendidos. Não apresentar o upstream como bloqueio universal.
5. Validar reboot, atualização e rollback; depois adaptar ADR/UX e o acesso pelo
   Vega somente ao comportamento comprovado.

A issue #6 permanece aberta; #2/#7 não devem anunciar proteção efetiva antes
dessa qualificação. Não há conclusão jurídica nem aprovação de conformidade
neste ensaio. A auditoria final e a candidata Alpha 8 continuam pendentes.

[Dados, versões, assinaturas e resultados](evidence/parental-base-20260921.json).
Scripts/logs completos: `analysis/2026-09-21/parental-base/` no workspace.
A documentação [GNOME](https://help.gnome.org/gnome-help/parental-controls.html)
limita a lista de aplicativos a Flatpak. O README entregue no RPM malcontent
explica que os consumidores devem consultar a política e que não é um sistema
de controle obrigatório como AppArmor/SELinux.

## Comparação com malcontent habilitado — 21/09

O mesmo código Flatpak 1.16.6 do SRPM oficial foi compilado na VM com
`-Dmalcontent=enabled`, mantendo o patch SUSE de autorização. O binário oficial
foi preservado e executado como controle na mesma conta/fixture. Este build
é diagnóstico: documentação e módulo SELinux não foram construídos; não é
um RPM equivalente ao release. Helpers oficiais de sistema/sessão permanecem.

| Cenário | Oficial | Build com malcontent |
| --- | --- | --- |
| Aplicativo permitido | Executa (0) | Executa (0) |
| Ref explicitamente negado | Executa (0) | Bloqueia (1), mensagem de política |
| Ref negado, barramento de sistema inacessível | Não repetido | **Executa (0)** |
| Ref negado, AccountsService indisponível | Não repetido | **Executa (0)** |
| Portal de documentos: exportar, ler e consultar permissão | Passou | Passou |

O cenário de barramento usa endereço inexistente na variável de ambiente da
própria conta sem privilégios. A indisponibilidade do AccountsService é uma
injeção administrativa de falha: o serviço foi temporariamente mascarado em
runtime e restaurado em `finally`. Não significa que a conta supervisionada
conseguiu interromper o serviço.

A causa está explícita em `common/flatpak-run.c:2835–2878`: a rotina retorna
permissão quando a conexão ao barramento falha, os controles estão desativados
ou o serviço obrigatório está ausente. Assim, habilitar a opção resolve o
fluxo comum, mas não satisfaz o critério de falha/evasão da integração Lyra.
Também não impede usar outros executáveis ou resolve bloqueio universal de RPMs.

O portal de documentos real e o PermissionStore foram ativados por D-Bus;
o conteúdo exportado conferiu byte a byte e a permissão de leitura foi
consultada. Quatro testes upstream (`testcommon`, `test-context`,
`test-exports`, `test-portal`) passaram, somando 49 subtestes. O teste upstream
de portal usa um Flatpak simulado: não substitui o ensaio real do documento,
nem qualifica FileChooser, ScreenCast ou a sessão GNOME/Wayland completa.
O changelog oficial menciona problemas com portais em 2024 sem detalhar o caso;
a pesquisa não identificou uma reprodução exata desse incidente. Não declarar
a regressão histórica resolvida.

A preparação do ambiente encontrou uma configuração SELinux incompleta trazida
por dependências opcionais. Ela também quebrou o controle positivo com o binário
oficial. Os resíduos foram preservados, a preparação foi reparada e o controle
positivo passou antes de aceitar a comparação. O enforcement do kernel não foi
alterado; este ambiente mínimo não qualifica SELinux da candidata.

**Decisão: não promover esse build nem encerrar #102/#6.** Antes de ampliar a
integração, definir a fronteira efetiva de proteção da conta supervisionada e
como recusar falhas sem quebrar contas comuns, initial-setup e portais. Avaliar
os mecanismos da base para essa fronteira; um botão no Vega ou uma alteração
isolada no cliente não impede a execução de um cliente alternativo pelo usuário.
Em seguida repetir instalação por usuário/sistema, autorização interativa,
portais completos e atualização/rollback com o pacote candidato.

[Comparação e limites](evidence/parental-flatpak-20260921.json).
Artefatos reproduzíveis em `analysis/2026-09-21/parental-flatpak/` no workspace.
Nenhum pacote enviado ao OBS, configuração do host alterada ou ISO gerada.

## Registro histórico — Leap 16.0, superado pela avaliação acima


Status: resultado técnico da #6  
Data da consulta: 18/08/2026  
Alvo original: Lyra OS Desktop 1.0, openSUSE Leap 16.0, x86_64

> Esta qualificação registra a decisão tomada sobre a base 16.0. A migração
> para Leap 16.1 exige repetir a consulta de disponibilidade e os testes antes
> de promover qualquer componente de controle parental para a imagem.

## Resultado

`malcontent` é o candidato upstream preferencial para política de aplicativos
e integração com AccountsService/OARS. Ele **não está qualificado para entrar
na imagem da versão 1.0 neste momento**, porque não há pacote oficial para
openSUSE Leap 16.0. O portal oficial lista somente pacote comunitário 0.12.0
para Leap; Tumbleweed possui 0.13.1 oficial.

Consequentemente:

- não adicionar repositório comunitário à ISO;
- não copiar `libmalcontent` nem os helpers do BigLinux;
- não criar fork privado permanente;
- solicitar/manter o pacote pela cadeia GNOME/openSUSE e submetê-lo ao staging;
- bloquear #2 até existir pacote qualificado ou exceção formal documentada.

Referências:

- [estado do pacote no openSUSE Software](https://software.opensuse.org/package/malcontent);
- [fonte em GNOME:Factory](https://build.opensuse.org/package/show/GNOME%3AFactory/malcontent);
- [repositórios oficiais do Leap 16.0](https://build.opensuse.org/repositories/openSUSE%3ALeap%3A16.0).

## Componentes avaliados

| Componente | Uso possível | Situação no Leap 16 | Decisão |
|---|---|---|---|
| AccountsService | Identidade e tipo da conta local | Base existente do desktop | Usar como adaptador de conta, nunca como aferidor |
| malcontent core | Filtro por caminho, instalação e OARS | Sem pacote oficial | Candidato condicionado à promoção oficial |
| malcontent-control/UI | Interface upstream | Sem pacote oficial; UX será Vega | Não instalar; evitar duas interfaces concorrentes |
| GNOME Software plugin | Consumidor de filtro | Vega é o fluxo Lyra | Estudar interoperabilidade, não tornar dependência da UX |
| PAM `time.conf` | Agenda de login | Mecanismo maduro, mas escopo limitado | Avaliar apenas como camada de agenda |
| systemd/logind | Sessão e enforcement persistente | Base madura | Preferir APIs tipadas; testar encerramento/recuperação |
| polkit | Autorização administrativa | Base madura | Usar ações pequenas por capacidade |
| nftables | Camada de rede | Base madura | Complementar; não equivale a filtro web completo |
| ACL POSIX | Bloqueio por inode/caminho | Base madura | Complementar; não equivale a controle da instalação |

## Compatibilidade funcional do malcontent

Pontos adequados ao Lyra:

- integração com AccountsService e D-Bus;
- API para filtro de aplicações e metadados OARS;
- política consultada pelo consumidor em vez de depender da GUI;
- suporte existente no ecossistema GNOME/Flatpak;
- biblioteca e formato já mantidos fora do Lyra.

Limites que permanecem:

- consumidores precisam consultar e respeitar o filtro; ele não bloqueia todo
  executável ou canal automaticamente;
- OARS depende da qualidade e disponibilidade de metadados;
- filtro de aplicação não fornece aferição de idade nem sinal interoperável;
- agenda de sessão não substitui quota consolidada ou política multi-sessão;
- a versão futura 0.14 adiciona tempo de tela, mas não deve entrar na base LTS
  sem maturidade, pacote oficial e análise específica de segurança.

## Caminho recomendado para empacotamento

1. Abrir solicitação no projeto mantenedor GNOME do OBS para construir a versão
   estável suportada contra `openSUSE_Leap_16.0`.
2. Confirmar que o pacote usa somente dependências oficiais do Leap e preserva
   ABI/API durante o ciclo LTS.
3. Executar build no staging do Lyra sem adicionar repositório de usuário à
   imagem final.
4. Validar filtros com RPM, Flatpak, Vega e GNOME Software, inclusive ausência
   de metadados e falha do serviço.
5. Revisar política D-Bus/polkit, migração, downgrade e rollback.
6. Promover apenas após revisão de segurança e evidência reproduzível.

Se a promoção upstream não ocorrer antes do gate, a alternativa segura é
adiar a funcionalidade parental, não internalizar silenciosamente o pacote.

## Contrato de adaptadores para a ADR

A futura arquitetura deve separar:

- `AccountAdapter`: UID, papel local e ciclo de vida da conta via
  AccountsService;
- `ApplicationPolicyAdapter`: política upstream via malcontent;
- `StoreAdapter`: autorização efetiva nos fluxos Vega/zypper/Flatpak;
- `SessionAdapter`: agenda/quota com systemd/logind/PAM quando aprovado;
- `AgeSignalProvider`: interface mínima ainda indefinida pela #10/#111.

Falha em qualquer adaptador obrigatório deve produzir estado explícito
`Unavailable` ou `Blocked`, nunca liberação automática.

## Gate da #6

A pesquisa e a decisão de qualificação estão concluídas. A integração ainda
fica bloqueada pela ausência do pacote oficial. A #5 pode usar este resultado
para desenhar a arquitetura, mas a #2 só inicia quando o pacote estiver
qualificado ou houver exceção formal com proprietário, manutenção, testes e
plano de remoção.
