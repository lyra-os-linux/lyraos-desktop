# Controle parental: revisão de integração após qualificação de admissão

Data: 05/10/2026. Status: **proposta revisável; não é aprovação da ADR nem entrega de produto**.
Complementa o [contrato autorizado](parental-lifecycle-recovery-contract.md), a
[ADR 0008](adr/0008-private-age-signal-and-parental-supervision.md) e os
[marcos da primeira entrega](parental-first-release-scope.md).

## Resultado e limite

Os ensaios qualificaram componentes experimentais de negação persistente,
retirada de admissão e retomada de operações identificadas. Não qualificaram
controle parental completo, quiescência global nem criação/migração real de
contas. #6 e #102 continuam abertos. A próxima etapa deve resolver a fronteira
do serviço e os gates abaixo, em vez de prolongar automaticamente a série de
cortes de VM. A estação permanece sem instalação parental; publicação segue NO-GO.

| Componente | Evidência concluída e reutilizável | Limite para integração |
|---|---|---|
| Barreira e leases | [Writer e barreiras por geração](evidence/parental-registry-barrier/README.md) | Classificação de produto, descoberta e cobertura de produtores incompletas |
| Retirada de admissão | [Operação e ownership](evidence/parental-operation-journal/README.md) | Concluir retirada não encerra atividade existente nem permite alterar Unix |
| StopUnit com PAM | [Recuperação por nova instância](evidence/parental-pam-daemon-recovery/README.md) e [timeout nativo](evidence/parental-pam-native-timeout/README.md) | Perfil PAM fechado; não é daemon implementado, PAM geral ou prova de toda a conta drenada |
| Durabilidade antes/depois de StopUnit | [Origem/intent](evidence/parental-pam-early-cut/README.md), [accepted](evidence/parental-pam-atomic-cut/README.md) e [corte durável](evidence/parental-pam-powercut/README.md) | QEMU morto; host/cache vivos. Não cobre falta física de energia ou todos os erros I/O |
| Ownership e prova positiva após corte | [Publicação/unlink](evidence/parental-owner-cut/README.md) e [retomada autorizada](evidence/parental-owner-recovery/README.md) | Callback confiável, sem Polkit/transport de produto; retomada concluída e retry, sem novos cortes durante recuperação |
| Aplicação de políticas | [Qualificação upstream](parental-controls-upstream-qualification.md) e [fronteira de proteção](parental-protection-boundary.md) | Evasão #102 permanece impeditiva; admissão negada não comprova restrições de aplicativos |

No ensaio final, sete estados com marcador durável concluíram
`AdmissionWithdrawnNoQuiescence` com autorização nova fora dos locks. Repetir a
mesma operação exigiu autorização nova e preservou bytes/inodes/metadados.
Três estados sem primeiro marcador retornaram `RecoveryRequired` antes de
consultar autorização e sem escrita. A conta vizinha foi preservada.
Os 744 testes e 180 controles de VM são resultados desse ensaio, não percentual
de conclusão do produto. Os respectivos verificadores estão em cada diretório
acima; fontes e escopo precisam continuar compatíveis para reutilizar os resultados.

## Fronteira concreta do serviço

Inspeção local do checkout `vegad`, HEAD
`1c671bac5ce6a813d0732bbcb847dce314ae9417`: `README.md`,
`packaging/vegad.service` e `internal/dbusserver/users.go`.
O serviço existente é Go/D-Bus `org.lyraos.Vega1`, ativado sob demanda, com saída
por timeout de ociosidade. `UsersService.CreateUser` recebe `dbus.Sender` e
exige a ação `org.lyraos.vega.users.manage` antes da mutação administrativa.
A busca nos fontes Go inspecionados não encontrou implementação parental ou
malcontent. Esse método de criação não implementa o protocolo parental.

Recomendação: manter uma única autoridade de política conforme a ADR, reutilizar
o transporte/autorização existente quando adequado e os adaptadores upstream.
Não copiar os helpers Python/PAM de laboratório para o RPM. Não adicionar um
daemon paralelo por conveniência. A decisão de residência/ativação ainda deve
ser registrada em #2/#5: a persistência e a negação não podem depender de um
processo vivo ou de uma janela Vega aberta.

A integração deve declarar quem mantém trabalhos em andamento e como o
shutdown/timeout do serviço os trata. Durante operação pendente, impedir saída
por ociosidade ou persistir um ponto seguro e entregar retomada explícita;
reconciliação no boot consulta estado confiável e conserva bloqueio. Ela não
reabre conta, não inscreve geração e não chama automaticamente uma recuperação
com efeitos. Nenhuma alteração do timeout atual é autorizada por esta proposta.

Métodos administrativos existentes que alteram a identidade precisam consultar
a classificação parental no serviço antes de mutar uma associação protegida.
O protocolo tipado deve recusar caminho sem suporte, divergência NSS ou revisão
obsoleta. Isso não pretende impedir um administrador root irrestrito confiável.

## Decisões a registrar antes de implementar o serviço

| Decisão | Recomendação concreta | Aceite de revisão |
|---|---|---|
| Autoridade e transporte | Coordenador integrado; identidade obtida do remetente D-Bus, plano produzido no servidor | Localização do componente, lifecycle, contrato versionado e limites de privilégio registrados em #2/#5 |
| Capacidades | Separar reparo técnico, política vinculada e mutação Unix; wheel sozinho não é responsável | Ações Polkit e vínculos definidos; autorização vinculada à operação/revisão/efeito, revalidada após o diálogo |
| Persistência e rollback | Registro root-only e classificação negativa independentes da GUI/processo | Definir fonte de revisão confiável, schema, migração e comportamento de rollback/downgrade sem reabrir |
| Cobertura | Conta local e GNOME suportados; inibir canais alternativos com mecanismos verificados | Inventário obrigatório e política por produtor; desconhecido retorna UnsupportedProducer, sem conclusão permissiva |
| Recuperação | Distinguir retirada de admissão, reconciliação de StopUnit e reparo/publicação de geração | Tipos/resultados separados; nenhum deles é confundido com quiescência ou enrollment |
| Dados e UX | Estado próprio e saúde mínimos; Blocked/Unavailable enquanto incompleto | Aplicação das conclusões já aprovadas em #10, vínculo/retenção/sinal definidos na ADR e limites claros em #8 |

A revisão numérica das fixtures é **local ao registro**, não uma autoridade
monotônica global nem proteção contra restauração de snapshot. Permissões,
hashes e fsync não resolvem antirollback. Root irrestrito permanece confiável,
mas downgrade ou recuperação operacional não devem aceitar estado obsoleto
como permissão. A solução e os limites precisam estar explícitos antes de
prometer o requisito de revisão monotônica da ADR.

`StopJobs.reconcile` qualificado opera no mesmo boot e não reenvia StopUnit;
referências de outro boot são recusadas antes da autorização. A retomada de
retirada de admissão pode atravessar reboot, conservando marcador e bindings e
exigindo autorização nova. Ela retira apenas prova positiva verificada. Reparo
que publica uma geração ativa é outra operação, ainda não qualificada.

## Sequência finita de implementação e aceite

1. **Fechar #2/#5 para o próximo componente.** Registrar as decisões da tabela,
   contratos de produtores, fonte de classificação e revisão confiável. Manter
   o status de proposta da ADR até os seus gates finais; a direção técnica já
   autorizada não precisa ser aprovada novamente.
2. **Integrar o núcleo isoladamente em VM com contas fictícias.** Implementar
   leitura/estado/planejamento e retirada tipada com remetente real, Polkit e
   journal. Testar negação/cancelamento, cliente desconectado, revisão obsoleta,
   replay de outra operação, retomada e preservação da conta comum. Não habilitar
   criação/migração antes de qualificar classificação e cobertura.
3. **Fechar durabilidade do núcleo integrado.** Derivar da implementação final
   os testes de interrupção durante recuperação, publicações posteriores e
   erros write/rename/fsync, concorrência e atualização com journal pendente.
   Registrar cada ponto, estado permitido e resultado. Não executar novas
   séries de VM só para aumentar contagens; reutilizar provas compatíveis e
   acrescentar ensaio quando contrato ou código introduzir lacuna concreta.
4. **Qualificar conta/sessão/política reais em VM.** Inventário e inibição de
   produtores, quiescência demonstrada, NSS e gerações, criação/migração parcial,
   GNOME/GDM completos e matriz de evasão #102. Perfil PAM geral, D-state,
   notify/reload, capabilities/threads/subgrupos e recursos compartilhados
   exigem tratamento explícito de suporte ou recusa, não extrapolação da fixture.
5. **Concluir experiência e entrega.** Vega/UX, privacidade e sinal aprovado;
   RPM em staging somente Leap 16.1, instalação/update/downgrade/recuperação e
   ISO por checksum exato. Só publicar/habilitar após os gates correspondentes.

Reversão da etapa isolada: parar o componente da fixture e restaurar/descarte
do overlay verificado, conferindo ausência de alterações na estação. Reversão
do pacote de produto precisa conservar registro e barreira; desinstalar não
pode converter a conta em comum. Uma falha pode bloquear login: diagnóstico e
reparo que conservem política são obrigatórios antes de qualquer instalação real.

Esta consolidação encerra a organização das provas existentes. O próximo
resultado revisável é o contrato de integração #2/#5 e sua classificação
persistente; não o fechamento de #6/#102 nem a promoção de um pacote parental.
