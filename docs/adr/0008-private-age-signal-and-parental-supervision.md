# ADR 0008 — Sinal etário privado e supervisão parental

- Status: **Proposta — revisão técnica e aprovação final pendentes**
- Data: 18/08/2026; conciliação técnica: 21/09/2026
- Issues vigentes: #5 (arquitetura), #6 (base upstream), #7/#8 (integração/UX),
  #10 (parecer), #11 (epic), #102 (aplicação de políticas).
- O parecer foi aprovado pelo mantenedor em 26/08, conforme #10/#5. Isso não
  aprova automaticamente esta ADR nem preenche decisões técnicas ou contratuais.
- Os números antigos abaixo pertencem ao rastreador anterior e são históricos.

## Contexto

O Lyra precisa acomodar obrigações relacionadas a sistema operacional, loja e
aplicativos sem criar uma base de identidade/vigilância nem concentrar
privilégios no Vega. O contrato definitivo deve aplicar as conclusões do parecer já aprovado e
registrar as decisões técnicas pendentes, sem inferir requisitos jurídicos
a partir dos ensaios de software.

A auditoria #112 rejeitou importar o BigLinux: sua API expõe faixa e atividade,
falha para `18+` em ausência/corrupção e usa helper privilegiado amplo. A qualificação inicial escolheu malcontent como candidato upstream. A
reavaliação Leap 16.1 confirmou pacotes oficiais, mas reproduziu limitações de
aplicação e evasão em #102. Consultar a
[qualificação atual](../parental-controls-upstream-qualification.md). A UX #108 exige informação, contestação, autonomia
progressiva e limitações claras.

Apple Declared Age Range e Microsoft Family Safety são referências, não prova
de conformidade. São aproveitáveis os conceitos de faixa em vez de nascimento,
origem da declaração, permissão por aplicativo, papéis separados e pedidos. O
Lyra não adotará conta cloud ou coleta comportamental por padrão.

## Decisões independentes do método etário

### Separação de componentes

```text
Vega (UI sem root)
  │ API versionada + autenticação
  v
serviço de políticas (root, persistente, mínimo)
  ├── adaptador AccountsService
  ├── adaptador malcontent/OARS
  ├── adaptador Vega/zypper/Flatpak
  ├── adaptador systemd/logind/PAM
  └── provedor de sinal etário (a definir)
```

Vega configura, explica e coleta confirmações. O serviço valida, persiste e
coordena. Adaptadores aplicam mecanismos upstream. A política permanece ativa
sem o Vega e sobrevive a crash, reboot, atualização e rollback.

### Papéis e autorização

- **Administrador técnico:** mantém o sistema; não recebe automaticamente
  acesso a faixa ou atividade.
- **Responsável autorizado:** configura contas vinculadas e responde pedidos.
- **Usuário supervisionado:** consulta regras próprias, pede mudanças e
  contesta/retifica.
- **Consumidor de sinal:** aplicativo autenticado, com capacidade e finalidade.

Um usuário pode acumular papéis, mas autorização é por capacidade, não apenas
por associação a `wheel`.

### Dados mínimos

O serviço pode persistir identificador local opaco da conta, vínculos de papel,
política versionada, referência/classe/validade do sinal quando aprovadas,
autorizações por consumidor/finalidade, pedidos/decisões mínimos e estado de
migração. Não persiste documento, biometria, nascimento exato, histórico web ou
lista de processos por padrão. Logs técnicos não contêm faixa ou justificativa.

### API mínima

Namespace provisório, sujeito a revisão upstream: `org.lyraos.ParentalPolicy1`.

- `GetOwnSupervisionState()`;
- `GetManagedAccountState(account)` para responsável vinculado;
- `RequestThreshold(capability, threshold, purpose)`, nunca consulta geral por UID;
- `SetPolicy(account, expected_revision, policy)`;
- `SubmitRequest(type, payload)` e `ResolveRequest(id, decision)`;
- `GetHealth()` sem dados pessoais;
- `Recover(revision/action)`.

Respostas incluem versão, revisão, confiança e código estruturado. Campos
desconhecidos falham fechado. Não existe método de comando, path ou JSON opaco.

### Defaults de falha

- ausente, expirado, revogado, corrompido ou indisponível → `Unknown`, nunca
  `Adult`;
- consumidor não autorizado → `Denied`, sem confirmar existência/faixa;
- adaptador obrigatório indisponível → `Degraded/Blocked`;
- escrita/migração parcial → manter última revisão válida;
- divergência entre cache e enforcement → não declarar política ativa;
- rollback incompatível → preservar bloqueio e orientar recuperação.

### Persistência

- arquivos root-only `0600`, `O_NOFOLLOW|O_CLOEXEC`;
- schema e revisão monotônica;
- temporário `create_new`, fsync de arquivo/diretório e rename;
- backup da última revisão válida e migração reversível;
- lock global e leitura consistente;
- corrupção gera recuperação, nunca configuração vazia.

### Enforcement em camadas

- Vega/vegad controlam instalação suportada e o serviço root revalida;
- malcontent/OARS é candidato para política de aplicativos;
- ACL e nftables são apenas reforços;
- systemd/logind/PAM podem aplicar agenda/quota após qualificação;
- cada adaptador publica saúde e limitações para a interface.

## Decisões que ainda precisam ser explicitadas a partir do parecer

Permanecem indefinidos: método/provedor/base legal de aferição, valor de
declaração parental, retenção, limiares/faixas, regras regionais,
consentimento/revogação, evidências exigidas e enquadramento preciso do Vega
como loja. A aprovação anterior do parecer não permite inventar o conteúdo dessas decisões.
Protótipos técnicos usam contas fictícias, sem aferição nem dados de menores.

## Alternativas rejeitadas

- **Importar BigLinux:** fail-open, leitura ampla, helper monolítico e Arch-specific.
- **Usar só malcontent:** não fornece aferição, sinal, papéis nem cobertura total.
- **Conta cloud obrigatória:** coleta/dependência sem lacuna demonstrada.
- **Faixa geral por UID:** facilita enumeração e correlação; preferir limiar/finalidade.
- **Declaração como “verificada”:** proibida sem conclusão jurídica.
- **Entregar proteção parcial como completa:** adiar é o fallback seguro.

## Modelo de ameaça mínimo

- aplicativo enumerando menores/faixas;
- administrador técnico sem papel de responsável e responsável coercitivo;
- evasão por CLI, cópia, interpretador, AppImage, container, VPN ou DoH;
- substituição de binário/política durante update;
- symlink, corrupção, rollback/downgrade e schema antigo;
- frontend comprometido solicitando operação excessiva;
- correlação entre consumidores e dispositivo compartilhado;
- indisponibilidade do aferidor e recuperação de responsável.

## Migração e rollback

O serviço nasce `Unconfigured`, não adulto. Migração só publica revisão após
validação completa e mantém a anterior até confirmação. O pacote lê ao menos
uma versão anterior, mas escreve apenas a atual. Downgrade incompatível preserva
estado e bloqueia alteração. Remover o pacote não apaga política ou recuperação.

## Consequências

O desenho minimiza dados, mantém enforcement fora da GUI e permite trocar
adaptadores. Em contrapartida, exige serviço, autorização fina, qualificação de
malcontent e testes extensos. A funcionalidade pode ser adiada da 1.1 se as
dependências jurídicas/upstream não fecharem antes do congelamento.

## Gate de aprovação

A ADR muda para `Aceita` após registrar a aplicação das conclusões do parecer
já aprovado, completar as decisões técnicas, qualificar a base (#6/#102),
revisar a UX (#8) e demonstrar testes, migração e reversão. A aprovação do
parecer não deve ser solicitada novamente como se ainda não existisse.
Até a aprovação técnica, esta ADR orienta protótipos isolados com contas fictícias;
não é evidência de uma proteção pronta para a distribuição.


## Fronteira técnica de proteção — proposta de 21/09

A [matriz de proteção](../parental-protection-boundary.md) distingue política
armazenada, clientes cooperativos e controle da execução da conta. Em 21/09,
o mantenedor escolheu **conta restrita, com aplicativos aprovados e proteção
contra evasão**. Essa decisão não qualifica automaticamente um mecanismo de
confinamento nem reduz os critérios de evasão porque a biblioteca upstream é cooperativa.
Não expor “Supervisão ativa” antes da qualificação das camadas obrigatórias.
