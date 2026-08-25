# Versionamento e rastreabilidade de releases

O arquivo [`release.toml`](../release.toml) é a única fonte editável da
identidade de uma release do Lyra OS. Não altere versões diretamente no KIWI,
na interface do instalador ou no arquivo gerado
`kiwi/root/usr/lib/lyra-os/release`.

## Convenção

O Lyra usa uma versão de calendário no padrão Ubuntu, `AA.MM`, e acrescenta o estágio enquanto
a imagem ainda é uma pré-release:

| Estágio | `release.toml` | Versão, tag e exemplo de ISO |
|---|---|---|
| Alpha | `stage = "alpha"`, `iteration = N` | `27.02-alphaN`, `v27.02-alphaN`, `lyra-os.x86_64-27.02-alphaN.iso` |
| Beta | `stage = "beta"`, `iteration = N` | `27.02-betaN`, `v27.02-betaN`, `lyra-os.x86_64-27.02-betaN.iso` |
| RC | `stage = "rc"`, `iteration = N` | `27.02-rcN`, `v27.02-rcN`, `lyra-os.x86_64-27.02-rcN.iso` |
| Final | `stage = "release"`, `iteration = 0` | `27.02`, `v27.02`, `lyra-os.x86_64-27.02.iso` |

## Contrato de maturidade

As datas do cronograma são limites de planejamento, não autorização para
promover um produto que ainda não atingiu o estágio seguinte. Se necessário,
o lançamento atrasa. O objetivo não é alegar perfeição, mas entregar uma
distribuição previsível e “chata de tão confiável”: ela deve poder ser usada
diariamente por um período prolongado sem travar, degradar, exigir manutenção
recorrente ou interromper o trabalho do usuário.

| Estágio | Estado esperado | Mudanças permitidas |
|---|---|---|
| Alpha | Produto em construção e qualificação | Funcionalidades planejadas, integração e correções, sempre com estabilidade em primeiro lugar. |
| Beta | Escopo completo e funcionalmente congelado | Correções de bugs, regressões, segurança, desempenho, acessibilidade e traduções existentes. |
| RC | Produto já estável; candidato completo sob verificação final | Nenhuma mudança rotineira. Defeito não trivial interrompe a promoção, devolve o produto à estabilização e exige uma nova RC. |
| Estável | Conteúdo funcional publicado e congelado | Somente correções de segurança. Demais correções e mudanças seguem para o próximo ciclo completo. |

A promoção para RC afirma que os gates de estabilidade já estão verdes; a RC
não é uma Beta com outro nome. A promoção para estável confirma o mesmo
conteúdo após a última verificação de imagem, assinatura, instalação,
atualização, recuperação e uso real. Ausência de P0/P1 é requisito mínimo, não
evidência suficiente por si só.

O build atual é `alpha6`: ciclo de conclusão do Lyra Upgrade, do fluxo de
atualizações e do backend de controle parental, mantendo a classificação Alpha
porque ainda há funcionalidades planejadas em implementação, não apenas
estabilização. A tag já
publicada `v2026.08-beta2-stable-20260809` permanece como registro histórico
e não é reescrita; o próximo ciclo de beta deste produto recomeça em `beta1`.

Uma nova compilação da mesma release mantém a versão. O commit, a data, o
estado limpo ou modificado da árvore e o SHA-256 distinguem builds e ficam no
manifesto `*.iso.manifest.json` criado pelo helper de build.

## Preparação de uma versão

1. Edite apenas os campos em `release.toml`.
2. Renderize os consumidores versionados:

   ```bash
   ./scripts/release.py render
   ```

3. Revise as mudanças e execute as validações:

   ```bash
   ./scripts/release.py check
   python3 -m unittest discover -s tests -v
   ```

4. Faça o build pelo helper. Ele rejeita metadados divergentes, um nome de ISO
   inesperado e um `VERSION_ID` incorreto dentro da imagem:

   ```bash
   ./kiwi/test/build-and-run-vm.sh
   ```

5. Somente um commit limpo e aprovado deve originar uma imagem publicada.
   Crie a tag derivada de `release.toml` no commit exato e use a mesma versão
   no título das notas de release. O campo pode ser consultado sem duplicar a
   regra:

   ```bash
   ./scripts/release.py field tag
   ./scripts/release.py field iso_filename
   ```

As notas devem registrar o nome da ISO, o SHA-256 e os campos `built_at` e
`source.commit` do manifesto. Uma árvore marcada como `source.dirty: true` é
adequada para desenvolvimento local, mas não para publicação.

A decisão final segue a checklist versionada em
[`release-gate.md`](release-gate.md). O manifesto de evidências rejeita árvore
suja, resultado vermelho e qualquer evidência obrigatória ausente.

## Cronograma do ciclo Lyra OS 27.02

O número de iterações por estágio é um teto, não uma meta fixa: a promoção
de estágio é liberada por critério de saída (nenhum item P0/P1 aberto no
[`release-gate.md`](release-gate.md) para o estágio corrente), não apenas
pela data. As datas abaixo assumem o cenário em que todo o teto é usado; se
um estágio fechar mais cedo, a promoção acontece mais cedo.

| Estágio | Cadência | Datas | Política |
|---|---|---|---|
| alpha3 | concluída | 11/ago/2026 | Fechar o instalador suportado e sua publicação. |
| alpha4 | snapshot antecipado | 14/ago/2026 | Publicar i18n base, instalador em três idiomas e primeira onda de pacotes. |
| alpha5 | 2 semanas | 14/ago/2026 → 28/ago/2026 | Corrigir bloqueadores herdados; fechar i18n, NVIDIA pelo Vega e contratos do Lyra Upgrade. |
| alpha6 | 2 semanas | 28/ago/2026 → 11/set/2026 | Concluir core, serviço, interface e fluxos de update/upgrade; entregar backend parental. |
| alpha7 | 2 semanas | 11/set/2026 → 25/set/2026 | Integrar controles parentais no Vega e executar a trilha de compatibilidade. |
| alpha8 | 2 semanas e 4 dias | 25/set/2026 → 13/out/2026 | Fechar upgrade e gate até 06/out; estabilizar exclusivamente de 06–13/out. |
| beta1 | 4 semanas | 13/out/2026 → 10/nov/2026 | **Feature freeze:** somente bugs, regressões, segurança, desempenho e correções de traduções existentes. |
| beta2 | 4 semanas | 10/nov/2026 → 08/dez/2026 | Estabilidade e atualização; nenhuma feature nova. |
| beta3 | 4 semanas | 08/dez/2026 → 05/jan/2027 | QA linguístico e correções finais; nenhuma infraestrutura ou novo componente traduzido. |
| rc1 | 2 semanas | 05/jan/2027 → 19/jan/2027 | Somente bloqueadores P0/P1 e repetição do gate. |
| rc2 | 2 semanas | 19/jan/2027 → 02/fev/2027 | Somente bloqueadores P0/P1 e preparação da publicação. |
| final (buffer) | 2 semanas | 02/fev/2027 → **~16/fev/2027** | Publicação e verificação dos artefatos; nenhuma mudança funcional. |

### Desktop Alpha 4 — publicação em 14/08

O Lyra Installer da 27.02 oferece somente **inglês dos Estados Unidos
(`en-US`)**, **português do Brasil (`pt-BR`)** e **espanhol da Espanha
(`es-ES`)**, com `en-US` como padrão e fallback. O gate integral mínimo dos
demais pacotes próprios permanece em `en-US`/`pt-BR`; outros idiomas ficam
para um ciclo futuro.

A Alpha 4 registra o ponto alcançado com a infraestrutura de catálogos e o
Lyra Installer em três idiomas. Depois de sua publicação, todos os projetos e
RPMs foram concluídos e testados em `en-US`, `pt-BR` e `es-ES`; o fluxo NVIDIA
também foi concluído e validado antecipadamente na Alpha 5.

O driver não entra no Lyra Installer nem na ISO padrão. O fluxo validado do Vega exige
detecção conservadora, confirmação explícita, Secure Boot verificado, snapshot
Snapper, pacotes meta em lockstep, `dracut`, reinício e rollback. O fluxo só
foi declarado suportado depois da validação no hardware G06 disponível.

### Desktop Alpha 5 — 14/08 a 28/08

- corrigir os bloqueadores herdados do instalador e do pipeline de release
  antes de ampliar o escopo (lyra-os-linux/lyraos-desktop#90, #23 e lyra-os-linux/lyraos-desktop#92).
- aprovar arquitetura, modelo de ameaças, protocolos e máquina de estados do
  Lyra Upgrade (#27), pois esse contrato bloqueia as demais implementações.
- concluir o enquadramento jurídico do ECA Digital (#10), auditar a referência
  do BigLinux (#4), qualificar a base upstream (#6), especificar a
  experiência no Vega (#8) e aprovar a arquitetura e os contratos (#5).
- estabelecer a baseline e a cadência de acompanhamento regulatório LTS
  (#3), sem autorizar ampliação silenciosa após o congelamento funcional.
- concluído antecipadamente: todos os projetos e RPMs nos três idiomas (lyra-os-linux/lyraos-desktop#78),
  NVIDIA pelo Vega e remoção da ISO dedicada (lyra-os-linux/lyraos-desktop#77) e qualificação na imagem
  (lyra-os-linux/lyraos-desktop#79).

### Desktop Alpha 6 — 28/08 a 11/09

- entregar o core, preflight, estado durável e serviço privilegiado do Lyra
  Upgrade para atualizações seguras dentro da mesma release;
- entregar a interface acessível do Lyra Upgrade em `en-US`, `pt-BR` e
  `es-ES`, incluindo retomada da UI, apresentação de falhas, console
  sanitizado, diagnóstico e caminhos orientados de recuperação e rollback;
- integrar as novas telas do Welcome e a pilha ALSA explícita da imagem;
- validar a candidata final com os RPMs efetivamente publicados no OBS,
  incluindo áudio, Welcome, Vega, atualização, Secure Boot e rollback (#1).

O upgrade entre releases pertence à Alpha 7 (#26). O serviço parental
permanece no marco 27.02 e só avança depois da revisão jurídica e da qualificação
técnica; ele não bloqueia a candidata da Alpha 6.

### Desktop Alpha 7 — 11/09 a 25/09

- integrar no Vega a configuração parental e a autorização de aplicativos
  sobre o backend já qualificado (#7).
- concluído antecipadamente: verificação pós-boot, recuperação e rollback
  determinístico pelo snapshot registrado na operação (lyra-os-linux/lyraos-desktop#85).

### Desktop Alpha 8 — 25/09 a 13/10

- **25/set–06/out:** automatizar update, upgrade, reboot, Secure Boot e rollback
  no release gate, usando RPMs reais do candidato (#24).
- automatizar o gate de conformidade, privacidade e regressão do ECA Digital,
  incluindo testes de evasão e evidências ligadas ao release (#9).
- **06–13/out:** nenhuma feature nova. Corrigir defeitos, repetir o gate
  completo e auditar que toda feature 27.02 foi implementada ou formalmente
  removida do escopo (#28).

**13/10/2026 é meta, não promoção automática.** A Beta 1 inicia o congelamento
funcional somente após a última Alpha fechar os gates. Uma
mudança depois desse ponto só pode corrigir bug, regressão, vulnerabilidade,
desempenho ou tradução já existente. Novo componente, novo fluxo, novo idioma
ou nova infraestrutura de i18n volta para o próximo ciclo, salvo P0/P1 com
decisão formal registrada.

Alpha 5, Alpha 6, Alpha 7 e Alpha 8 são obrigatórias. Toda funcionalidade deve
estar encerrada até 25/09; a semana final da Alpha 8 é reservada exclusivamente
para estabilização. O novo fracionamento não
autoriza reduzir os gates para cumprir a data. Fevereiro continua sendo a
folga máxima do cronograma, não motivo para promover uma Beta incompleta.
A final deste ciclo é publicada como **Lyra OS 27.02**.

## Lyra OS 27.10 “Ilíada” (rebase para openSUSE Leap 16.1)

Início em março/2027, ~1 mês após a final da 27.02. A base muda de Leap 16.0
para Leap 16.1 (GA em 03/nov/2026), o que exige revalidar disponibilidade de
pacotes, ABI, shim de Secure Boot e matriz de hardware contra o novo
repositório — não é um bump cosmético de número. O funil é mais enxuto que o
da 27.02 porque o tooling de release e o gate já existem; só a base precisa de
requalificação:

Este ciclo também abre a expansão para idiomas além de `en-US` e `pt-BR`.
Cada idioma novo precisa de catálogo completo dos componentes em escopo,
revisão humana, fallback para `en-US` e gate linguístico antes de aparecer no
seletor do Lyra Installer.

| Estágio | Cadência | Datas |
|---|---|---|
| alpha1 | 2 semanas | 01/mar/2027 → 15/mar/2027 |
| alpha2 | 2 semanas | 15/mar/2027 → 29/mar/2027 |
| alpha3 | 2 semanas | 29/mar/2027 → 12/abr/2027 |
| alpha4 | 2 semanas | 12/abr/2027 → 26/abr/2027 |
| alpha5 | 2 semanas | 26/abr/2027 → 10/mai/2027 |
| alpha6 | 2 semanas | 10/mai/2027 → 24/mai/2027 |
| alpha7 | 2 semanas | 24/mai/2027 → 07/jun/2027 |
| alpha8 | 2 semanas | 07/jun/2027 → 21/jun/2027 |
| beta1 | 4 semanas | 21/jun/2027 → 19/jul/2027 |
| beta2 | 4 semanas | 19/jul/2027 → 16/ago/2027 |
| beta3 | 4 semanas | 16/ago/2027 → 13/set/2027 |
| rc1 | 2 semanas | 13/set/2027 → 27/set/2027 |
| rc2 | 2 semanas | 27/set/2027 → 11/out/2027 |
| final estável (buffer) | 2 semanas | 11/out/2027 → **~25/out/2027** |

`27.02` e `27.10` são as versões canônicas dos ciclos, tanto para o produto
quanto para o campo mecânico `calendar_version` (`AA.MM`) em `release.toml`.
Não há uma numeração semântica `1.x` paralela.

## Campos sincronizados

O renderizador mantém alinhados:

- `<version>`, descrição e volume ID do KIWI;
- nome produzido para a ISO;
- `PRETTY_NAME`, `VERSION_ID`, `BUILD_ID`, `IMAGE_ID` e `IMAGE_VERSION` em
  `/etc/os-release`;
- strings de versão da interface do instalador;
- identificação corrente nos READMEs.

O workflow de CI executa o modo `check` e os testes. Assim, editar um arquivo
gerado sem alterar o manifesto, ou esquecer de renderizar uma mudança de
release, torna o job vermelho.
