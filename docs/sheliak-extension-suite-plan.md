# Plano de implementação — conjunto de extensões Lyra

Data: 12/09/2026. Estado: implementação das etapas 1–6 preparada; qualificação
integrada e entrega em andamento. Publicação e ISO ainda não concluídas.

As seis extensões, o fork LDI, os nomes PT/EN/ES e os controles individuais no
Vega estão implementados. O migrador mantém snapshots por usuário e recuperação
de interrupções; receita KIWI, defaults e verificador exigem as versões
coordenadas Sheliak 2.0.0, Vega GTK 5.1.35 e Welcome 0.4.1.

Os testes nativos já cobrem integração entre extensões, Vega real, favoritos,
tamanhos dos cards, busca, barra superior, teclado e acessibilidade. O ensaio de
atualização/reversão e os gates de RPM/OBS/ISO continuam obrigatórios. Evidências
locais: `analysis/2026-09-12/sheliak-extension-suite/` no workspace do mantenedor.
Não confundir testes de desenvolvimento com qualificação da próxima ISO.

## Objetivo e decisões aprovadas

Organizar o código para manutenção e expansão, preservando o comportamento já
aprovado. O mantenedor confirmou que a motivação não é lentidão.

- Manter o repositório `lyraos-desktop-sheliak`, com várias extensões GNOME.
- Manter um único pacote RPM/OBS `sheliak`, que instala todas as extensões.
- Sheliak será o nome do pacote/conjunto, não de uma extensão na estrutura final.
- Integrar Lyra Desktop Icons (LDI), baseado no DING, no mesmo repositório e RPM.
- Usar os nomes Lyra por contexto. Core e Aparência serão bibliotecas internas.
- Windows 10 passa a **Lyra Clássico**; Windows 11 a **Lyra Central**;
  MacOS X/macOS a **Lyra Flutuante**. Não usar Lyra SO 10/11/X.
- Manter os nomes dos demais perfis nesta alteração. Ubuntu não foi abrangido
  pela decisão de renomeação nem pela avaliação jurídica realizada.
- Foco exclusivo no GNOME e componentes comuns necessários. Distribuição RPM;
  OBS para fontes dos RPMs, ISO construída localmente com KIWI.

A decisão explícita do mantenedor define o escopo arquitetural. A execução deve
respeitar a fase vigente do release e os critérios de estabilidade do projeto.

## Estrutura proposta

```text
lyraos-desktop-sheliak/
  extensions/
    dock/             # Lyra Dock
    panel/            # Lyra Painel
    menus/            # Lyra Menus
    search/           # Lyra Busca
    animations/       # Lyra Animações
    desktop-icons/    # Lyra Desktop Icons, fork do DING
  shared/
    core/             # sinais, ciclo de vida, compatibilidade e contratos
    appearance/       # paleta e geração de estilos com escopo definido
    layouts/          # contratos de apresentação dos perfis
  schemas/
  po/
  tests/
  packaging/
  docs/
```

UUIDs propostos: `dock@lyraos.com.br`, `panel@lyraos.com.br`,
`menus@lyraos.com.br`, `search@lyraos.com.br`, `animations@lyraos.com.br` e
`desktop-icons@lyraos.com.br`. Conferir colisões antes de fixar o contrato.
Cada extensão terá metadata, enable/disable, recursos e testes próprios.
Bibliotecas serão incluídas pelo build; não importar arquivos de outra extensão
por caminhos privados. A integração em execução será explícita e versionada.

## Etapas e critérios de conclusão

### 1. Inventário, contratos e linha de base

- Partir dos commits integrados de Sheliak, Vega, Welcome e Desktop, em branches
  isoladas; preservar as alterações locais de tradução do DING já preparadas.
- Mapear configurações, atores, sinais, atalhos, estilos e referências cruzadas.
  Cada elemento terá um único responsável por criá-lo, modificá-lo e restaurá-lo.
- Painel controla geometria/indicadores e oferece o ponto de integração; Dock
  controla seus itens; Menus controla menu L/Iniciar e seu atalho quando ativo;
  Busca oferece pesquisa reutilizável com cancelamento e resultados limitados.
- Definir degradação: Dock sem Painel funciona independente; Menus sem Dock usa
  um lançador próprio; sem Busca os menus ainda abrem aplicativos. Ao perder uma
  integração, desfazer conexões e restaurar o estado sem atores órfãos.
- Descrever comportamento quando alguma extensão é desligada manualmente.
  Nenhuma extensão deve reativar outra à força ou ignorar bloqueio global GNOME.
- Preservar como referência os perfis, favoritos separados, tamanhos dos cards,
  alinhamentos, cores, transparência, ampliação e comportamento da tecla Super.

Saída: contratos revisáveis e matriz de regressão. Risco principal: duas
extensões disputarem o mesmo ator ou atalho; mitigar antes da extração.

### 2. Nomes dos perfis

- Trocar nomes exibidos no Vega GTK, Welcome, preferências, mensagens e docs.
- Atualizar PT/EN/ES e prévias próprias; conferir recursos visuais e licenças.
- Manter inicialmente os IDs persistidos `windows10`, `windows11`, `macos` como
  compatibilidade interna. Não converter nomes visíveis em chaves de armazenamento.
- Preservar snapshots, favoritos e comandos existentes; documentar aliases antigos
  se posteriormente forem introduzidos IDs novos.

Saída: três nomes próprios nas interfaces, com comportamento e dados preservados.
Esta etapa pode ser revisada independentemente da mudança arquitetural.

### 3. Estrutura interna e extração das extensões

- Primeiro reorganizar os módulos sem alterar comportamento. Depois criar os
  pontos de entrada separados, em PRs pequenas e verificáveis.
- Extrair Animações e Busca; em seguida Menus; separar Dock/Painel juntos na etapa
  de integração, pois os layouts Clássico/Central hoje incorporam o dock ao painel.
- Compartilhar paleta/código, mas atribuir a uma única extensão os estilos globais
  de calendário/ajustes rápidos. Estilos locais devem ter escopo próprio.
- Os layouts serão dados/contratos compartilhados, não uma extensão adicional.
  O Vega aplica o perfil; cada extensão executa apenas sua responsabilidade.
- Testar ativação em ordens diferentes, desativação, reativação, falha parcial,
  integração indisponível e restauração dos recursos nativos do GNOME.
- A entrada antiga pode existir somente durante o desenvolvimento transitório;
  o RPM final não instala uma extensão chamada Sheliak.

Saída: extensões separadas funcionando juntas e com degradação definida. Não
prometer isolamento de processos: extensões continuam dentro do GNOME Shell.

### 4. Lyra Desktop Icons

- Importar a base DING 49.0.5, commit
  `c32667693d0831c29e3ab3f7bfeb675ea1531a00`, com origem/histórico rastreáveis,
  licença GPL e créditos mantidos. Documentar como incorporar correções upstream.
- Manter aplicativo auxiliar e arquitetura upstream; adaptar nome, UUID, domínio
  gettext, schemas, IDs D-Bus e empacotamento sem alterar serviços do Nautilus.
- Aproveitar o catálogo pt_BR revisado de 190 mensagens, conferir o catálogo
  espanhol e as strings inglesas; validar placeholders, plurais e nova marca.
- Definir migração das preferências e posição dos ícones. Não mover, renomear nem
  excluir arquivos do Desktop. Respeitar a preferência anterior de desktop desligado.
- Impedir ativação simultânea de DING e LDI; detectar também instalação DING por
  usuário. Não apagar cópias locais do usuário nem suas configurações.
- Integrar reserva de espaço com Dock/Painel por contrato de área útil, validando
  bordas e múltiplos monitores sem duplicar responsabilidades do compositor.

Saída: LDI incluído no conjunto, traduzido, com migração e operações de arquivos
qualificadas em diretórios de teste descartáveis.

### 5. Vega GTK, Welcome e revisão do vegad

- Substituir a dependência de um UUID Sheliak por um catálogo de capacidades,
  versões e estados das extensões. Distinguir instalada, preferida e ativa na sessão.
- Manter o controle independente de área de trabalho ativa. Instalar todas as
  extensões não significa habilitar todas em todo perfil.
- Criar tabela explícita dos seis perfis e configurações. GNOME Vanilla restaura
  recursos nativos; a escolha independente do desktop permanece preservada.
- Aplicar perfis com pré-validação, snapshot e recuperação em falha parcial;
  não presumir atomicidade entre configurações e ativações diferentes.
- Preservar extensões de terceiros, bloqueios globais, favoritos por perfil,
  ordem/tamanho dos cards e preferências personalizadas já salvas.
- Welcome continua delegando ao Vega; não duplicar a implementação dos perfis.
- Revisar vegad no repositório próprio. A inspeção inicial não encontrou UUIDs
  Sheliak/DING nos seus controles; alterar somente contratos administrativos
  efetivamente afetados. Ativação e dconf continuam na sessão do usuário.

Saída: perfis consistentes e reversíveis, nomes novos nos três idiomas e ausência
de novas operações privilegiadas para configurar a sessão.

### 6. Migração de instalações e pacote único

- Criar migração versionada e idempotente por usuário, executada na sessão, com
  snapshot protegido e possibilidade de retomada após interrupção.
- Migrar estado do UUID `sheliak@lyraos.com.br` para a combinação do perfil atual,
  respeitando Sheliak desativado e preferências individuais. Coordenar DING → LDI.
- Ler/migrar chaves antigas sem destruí-las; precedência para preferências novas
  explícitas quando a migração for repetida. Testar dados ausentes e inválidos.
- RPM `sheliak` entrega todas as extensões, traduções, schemas e dependências do
  auxiliar LDI. Definir Requires/Obsoletes/Conflicts após ensaio real do resolvedor;
  não remover automaticamente pacotes ou extensões não relacionados.
- Garantir compatibilidade de versões com Vega/Welcome e impedir combinações
  incompatíveis. Durante desenvolvimento, não publicar uma extração incompleta
  como substituta utilizável da versão atual.
- Atualizar inventários OBS/i18n, receita KIWI, defaults GNOME e verificador de
  mínimos da imagem. Não excluir o pacote DING remoto antes de validar a substituição.

Saída: instalação nova e atualização da instalação atual funcionam pelo mesmo
RPM; migração sem acesso root ao dconf e sem perda de arquivos/configurações.

### 7. Qualificação e entrega

- Executar TypeScript/build, contratos, gettext, testes Rust relevantes e testes
  nativos GNOME existentes adaptados aos novos UUIDs. Adicionar testes para os
  contratos novos, migração interrompida, desativação e combinações parciais.
- Cobrir os seis perfis e ida/volta entre eles, temas claro/escuro, PT/EN/ES,
  calendário/ajustes rápidos, teclado/Super, favoritos, cards e desktop desligado.
- Qualificar múltiplos monitores, escala/HiDPI, arquivos/arrastar e soltar, login,
  atualização e reversão em sessão privada/VM. Preservar dados da sessão pessoal.
- Validar primeiro em ambiente isolado; instalação pessoal somente de um candidato
  completo e testado. Não reiniciar o Shell pessoal à força; novo login quando necessário.
- PRs com testes aprovados e versões compatíveis; enviar fontes ao staging OBS.
  Respeitar a preferência de apenas enviar, sem monitoramento contínuo de builds.
- Promoção exige verificação pontual dos resultados, assinaturas e gates de release,
  sem P0/P1. A qualificação não é dispensada pela ausência de monitoramento contínuo.
- A próxima ISO será construída localmente após qualificação dos RPMs; testar live
  e primeiro login instalado. Atualizar memória, docs e evidências de cada entrega.

Saída: conjunto qualificado, pacote entregue e receita local da ISO atualizada.

## Reversão

Guardar RPMs e configurações anteriores antes do ensaio de atualização. Reversão
deve restaurar uma combinação compatível de Sheliak/Vega/Welcome/DING, desativar
UUIDs novos e restaurar apenas configurações pertencentes ao conjunto a partir do
snapshot. Não substituir listas inteiras de extensões ignorando alterações feitas
pelo usuário depois do backup. Nenhuma reversão modifica arquivos do Desktop.
Testar recuperação no login quando a atualização é interrompida e quando o
pacote novo é removido. Não depender de hot reload do GNOME Shell.

## Ordem de execução

1. Inventário e contratos.
2. Nomes próprios dos perfis.
3. Modularização e extração das extensões.
4. Integração LDI.
5. Vega GTK/Welcome e revisão dirigida do vegad.
6. Migração, RPM único e receita KIWI.
7. Qualificação, merges, envio OBS e preparação da ISO local.

Não há estimativa de prazo fechada: o primeiro marco é validar os contratos de
Dock/Painel/Menus; isso determina o tamanho real da migração.
