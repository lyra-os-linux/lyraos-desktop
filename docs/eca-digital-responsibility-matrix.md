# Matriz de responsabilidades — ECA Digital

**Escopo:** Lyra OS Desktop 1.1 / Alpha 8, GNOME, Leap 16.1
**Status:** matriz técnica preliminar; requer validação contra o parecer já
aprovado pelo mantenedor e revisão profissional antes de servir como posição
jurídica do projeto.
**Atualizado:** 06/10/2026
**Issue:** [Desktop #10](https://github.com/lyra-os-linux/lyraos-desktop/issues/10)

O parecer profissional foi recebido e aprovado pelo mantenedor, conforme o
registro da issue #10. Seu conteúdo integral permanece sob guarda do mantenedor;
este documento não o reproduz, resume nem amplia suas conclusões. A aprovação
jurídica não qualifica tecnicamente os controles descritos abaixo.

### Classificação das afirmações

- **Técnica:** comportamento ou limite de software; deve estar associado à
  versão e à evidência indicada na linha.
- **Produto:** escopo, escolha de componentes ou guarda provisória do Lyra; não
  afirma obrigação legal.
- **Revisão pendente:** atribuição ou redação que precisa ser comparada pelo
  mantenedor e pelo profissional responsável com o parecer aprovado. Esta
  matriz não antecipa essa conclusão.

Aplicando essa classificação às tabelas abaixo: as fronteiras de GNOME,
Flatpak, RPM e Vega são afirmações técnicas/produto, sujeitas à evidência e às
limitações descritas em cada linha; as atribuições jurídicas entre projeto,
upstream, lojas, fornecedores, administradores e responsáveis seguem em revisão
pendente. As regras de minimização de dados são guardas provisórias de
produto/privacidade, não conclusões sobre obrigação legal. A redação desta
matriz ainda não substitui a conferência profissional requerida pela issue #10.

## Fronteiras operacionais

| Agente/componente | O que controla no produto | O que não se deve presumir | Evidência e responsável | Estado/risco aberto |
|---|---|---|---|---|
| Projeto/mantenedor Lyra | Seleção da base, integração, marca, imagem, configuração padrão, testes e decisão de release | Que ser comunitário ou usar software livre transfira todas as responsabilidades à base | Escopo de produto, receita KIWI, revisão de release; mantenedor + engenharia | Escopo GNOME/Leap 16.1 registrado; revisar contra parecer antes de release |
| openSUSE Leap | Pacotes, mecanismos e políticas que mantém, como GNOME, AccountsService, malcontent e Flatpak | Que a presença de um pacote habilite ou garanta enforcement no Lyra | RPMs oficiais, SRPMs, políticas e documentação da versão; engenharia de integração | Malcontent não está habilitado no Flatpak oficial; #102 aberta |
| Vega GTK / vegad | Interface Lyra e operações administrativas que o produto expõe para software/configuração | Que Vega seja a loja adotada ou possa impor sozinho política de execução | Inventário de fluxos e chamadas; equipe Vega | GNOME Software é a loja adotada; UX parental e papel administrativo seguem pendentes |
| GNOME Software | Catálogo e fluxos de descoberta/instalação que o upstream oferece | Que sua interface prove classificação etária ou cubra todos os canais de execução | Testes de fluxo e integração com autorizações; engenharia GNOME | A qualificação #6 precisa cobrir os caminhos efetivamente entregues |
| Flatpak / Flathub | Cliente, runtimes, remotos e distribuição de aplicativos Flatpak | Que a blocklist de malcontent seja aplicada por qualquer cliente ou impeça outros formatos | Testes #6/#102 com RPM exato, instalação por usuário/sistema e portais; engenharia upstream/Lyra | Caso reproduzido no pacote oficial; build diagnóstica habilitada ainda falha aberta em condições testadas |
| Zypper, RPM e repositórios | Instalação/atualização de pacotes e origem/cadeia de RPMs | Que malcontent cubra execução de RPMs, AppImage, cópias ou código interpretado | Matriz de canais e autorização, com limites explícitos; engenharia de sistema | Cobertura parental não qualificada; não anunciar como canal protegido |
| OBS | Build e publicação de RPMs do Lyra | Que hospedar artefatos implique curadoria do conteúdo de terceiros | Configuração de projeto/repositório e proveniência do artefato; mantenedor/release | Infraestrutura de build; responsabilidades de publicação devem seguir o parecer aprovado |
| Flathub e fornecedores de apps | Metadados e conteúdo dos aplicativos publicados em seus canais | Que o Lyra verifique independentemente cada app ou controle seu comportamento interno | Origem, metadados, termos e limites informados; responsáveis upstream e release | Classificação e cobertura por app/canal ainda precisam de definição técnica |
| Administrador técnico | Manutenção do sistema e operações privilegiadas autorizadas | Que possuir `wheel` confira automaticamente papel de responsável ou acesso a dados pessoais | Capacidades de polkit/contas e trilha mínima; engenharia de segurança | Papéis e autorizações da ADR #5 precisam ser reconciliados |
| Responsável autorizado | Configuração e decisões explicitamente disponíveis para uma conta vinculada | Que uma declaração/configuração seja aferição etária confiável | Fluxo de vínculo, autorização, contestação e recuperação; produto/privacidade | Modelo final depende da ADR #5 e da UX #8 |
| Usuário supervisionado | Uso da conta, consulta das regras próprias e pedidos de revisão permitidos | Que uma restrição seja eficaz se depender de ocultar UI ou atalhos | Testes de evasão, recuperação e acessibilidade; segurança/QA | A fronteira de enforcement segue sem qualificação |

## Dados e decisões de privacidade

| Dado/finalidade | Estado permitido nesta fase | Retenção/acesso | Evidência e condição para mudar |
|---|---|---|---|
| Documento, biometria ou data de nascimento exata para inferir idade | Não coletar nem armazenar pelo Lyra | Nenhuma | Qualquer proposta nova exige decisão formal, revisão jurídica e de privacidade |
| Histórico de navegação, lista de processos ou telemetria de atividade | Não coletar para supervisão | Nenhuma | Não usar como substituto de enforcement; nova finalidade exige revisão explícita |
| Identificador local opaco, papéis e política parental | Somente protótipo/teste com contas fictícias até ADR #5 aprovada e gate #9 habilitado | Ainda sem prazo de retenção aprovado | Inventário campo a campo, controles de acesso, exclusão/recuperação e teste de corrupção |
| Sinal etário ou limiar fornecido a consumidor | Não implementar/publicar API nesta etapa | Sem persistência ou compartilhamento definidos | ADR #5 deve fixar origem, finalidade, validade, autorização, contestação e revogação |
| Logs de saúde e falha do adaptador | Apenas dados técnicos não identificáveis necessários ao diagnóstico | Prazo mínimo ainda a definir no gate #9 | Inspecionar conteúdo para evitar faixa etária, justificativas ou atividade pessoal |

## Decisões de engenharia refletidas no escopo

- GNOME é o único alvo Desktop da 1.1; GNOME Software é a loja adotada e Vega
  GTK oferece configurações e operações administrativas.
- A conta só pode ser apresentada como supervisionada quando os mecanismos
  obrigatórios estiverem verificados. Estado ausente, desconhecido ou degradado
  não deve aparecer como proteção ativa.
- A qualificação atual demonstra uma lacuna no Flatpak oficial. Ativar
  `-Dmalcontent=enabled` isoladamente não satisfaz o requisito nem qualifica
  portais, contas comuns, login inicial ou rollback.
- O upstream do Flatpak documenta que falha no barramento não é fronteira de
  segurança e aceitou ignorá-la no [PR #6663](https://github.com/flatpak/flatpak/pull/6663),
  posteriormente integrado ao `main`. Isso trata a falha de acesso ao barramento;
  não demonstra correção do caso distinto da issue Lyra #102 (política nega o app,
  mas a execução ainda ocorre). Essa reprodução precisa ser repetida ou refutada
  no RPM oficial exato atualmente usado no Leap 16.1;
  também caracteriza malcontent como não sendo uma fronteira contra execução
  arbitrária ([issue #5076](https://github.com/flatpak/flatpak/issues/5076)).
  Para o requisito Lyra de proteção contra evasão, é necessária uma fronteira
  imposta pelo sistema que cubra todos os caminhos suportados.
- Malcontent não bloqueia por si só RPM, AppImage, cópias, interpretadores,
  containers, execução por cliente alternativo, VPN ou DoH. Cada canal precisa
  ser qualificado ou explicitamente excluído da alegação de proteção.
- O Lyra não escolhe método de aferição etária nem declara conformidade legal
  com base nesta matriz. Orientações regulatórias e parecer devem ser revistos
  pelo responsável do projeto antes do congelamento de release.

## Evidências e responsáveis por fechamento

| Entrega | Dono proposto | Critério de conclusão |
|---|---|---|
| Vincular o parecer aprovado à decisão sem publicar o documento confidencial | Mantenedor | Registrar referência/data e confirmar que a redação pública não expõe conteúdo protegido |
| Revisar esta matriz à luz do parecer e corrigir papéis/condições | Mantenedor + responsável jurídico | Cada conclusão identificada como jurídica, técnica ou pendente; aprovação registrada na #10 |
| Qualificar canais, permissões e falhas em Leap 16.1 | Engenharia de sistema + QA | Evidência ligada a RPM/SRPM e hashes; #6/#102 resolvidas ou limitação formal que retire o canal do escopo |
| Definir papéis, dados mínimos e recuperação | Produto + segurança + privacidade | ADR #5 aceita e UX #8 revisada; nenhuma coleta não aprovada |
| Automatizar gates e manter evidência da candidata | QA/release | Testes negativos e positivos da candidata exata, limites residuais e aprovações associados à #9/#11 |

Esta matriz organiza o trabalho do produto e não substitui o parecer, não
declara conformidade e não autoriza ativar supervisão parental na imagem.
