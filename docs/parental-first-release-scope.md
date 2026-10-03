# Primeira entrega de controle parental — proposta de organização

Status: proposta para revisão do mantenedor em 03/10/2026. Não altera o
[contrato autorizado](parental-lifecycle-recovery-contract.md), não aprova a
ADR0008 e não autoriza publicar ou habilitar a proteção. #6/#102 e os gates
originais continuam abertos. Elaborada após o mantenedor observar que a demanda
ficou maior do que esperava.

## Resultado mínimo a perseguir

Uma conta local supervisionada consegue entrar na sessão GNOME suportada e
executar os aplicativos aprovados sob a política aplicada. O sistema apresenta
corretamente os estados de bloqueio e indisponibilidade. Um erro ou uma operação
incompleta conserva a negação, permite diagnóstico e recuperação autorizada,
e preserva o uso da conta comum. O limite de autoridade continua o do contrato:
root e manutenção administrativa irrestrita são confiáveis.

A entrega exige qualificação da conta/sessão real e da ISO. Resultados de
fixtures e catálogos escolhidos por root servem como evidência de componentes;
a integração de produto deve demonstrar descoberta/cobertura, autorização,
persistência e aplicação efetiva da política.

## Trabalho obrigatório para esse resultado

| Bloco | Aceite mínimo | Situação |
|---|---|---|
| Núcleo e produtores | Inventário confiável, atividade pendente incluída, inibição antes de revogação, nenhuma conclusão permissiva com produtor desconhecido | Barreiras, ownership e reboots passaram em escopos fechados; descoberta de produto incompleta |
| Persistência e contas | Identidade/geração e revisão confiáveis; estado antigo ou inválido não reabre; provisionamento protegido e divergência NSS recusada | Fixtures de admissão/journals existentes; autoridade monotônica e ciclo real pendentes |
| Sessão GNOME e política | Login completo, autenticação pendente e login automático cobertos; política MAC/OARS/aplicativos comprovada nos caminhos suportados | Ensaios parciais; worker/sessão completos e enforcement de produto pendentes |
| Serviço e experiência | Chamador identificado pelo transporte, papéis e Polkit corretos; API não aceita autoridade da GUI; interface informa controles ativos/limites/erros; privacidade aprovada | Contratos e fixtures; serviço/integração de produto pendentes |
| Entrega e manutenção | RPM/fontes, boot de produto, instalação, atualização, rollback e recuperação na ISO de checksum exato | Integração parental permanece NO-GO |

Rotas alternativas podem ficar indisponíveis para a conta supervisionada
quando essa indisponibilidade for imposta e qualificada. Esconder uma opção na
interface ou retirar uma entrada de catálogo não satisfaz esse aceite.
Produtores obrigatórios permanecem no inventário; uma inibição comprovada pode
ser o comportamento suportado do canal. A conta comum mantém seus canais.

## Como limitar a primeira entrega sem enfraquecer os aceites

Manter o contrato limitado a contas locais, sessão GNOME da base qualificada e
operações explicitamente suportadas. Evitar adicionar novas políticas, métodos
de aferição etária ou integrações externas durante a estabilização. Retirada
de supervisão e exclusão permanecem indisponíveis, como já determina o contrato.

A extensão de uma GUI para migrações e recuperação abrangentes pode ser
separada numa entrega posterior **se o mantenedor aprovar essa alteração de
escopo**. Os comandos não suportados precisam ser recusados explicitamente;
os requisitos de identidade, negação durável e tratamento de divergência
continuam necessários. Esta proposta não remove criação/migração do contrato
atual nem implementa essa redução por conta própria.

## Marcos de execução

1. Fechar descoberta de produtores pendentes e inventário, além da autoridade
   de persistência, e registrar os testes obrigatórios restantes do núcleo.
2. Qualificar a integração de uma conta local fictícia na sessão GNOME completa,
   com política real, caminhos alternativos definidos e conta comum preservada.
3. Integrar serviço, papéis, Polkit e interface com o fluxo suportado; concluir
   os requisitos de privacidade e provisionamento/recuperação.
4. Empacotar e validar instalação, login, atualização, rollback e recuperação
   na candidata de ISO identificada por checksum, antes de habilitar a função.

Os marcos agrupam sete áreas de trabalho já identificadas; não são estimativas
de duração. Não há percentual ou prazo confiável de conclusão enquanto a
cobertura de produto e suas decisões pendentes não tiverem aceites fechados.
A próxima revisão deve avaliar estes marcos e seus resultados concretos para
controlar expansão de escopo e priorizar correções que desbloqueiem a entrega.
