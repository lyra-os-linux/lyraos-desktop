# Decisões de produto — controle parental experimental

**Registro:** 07/10/2026. Decisões declaradas pelo mantenedor na conversa de
especificação. Este registro define comportamento pretendido; não comprova
implementação, cobertura técnica nem conformidade jurídica.

## Escopo e lançamento

- A Alpha 8 pode seguir sem controle parental se houver evasão conhecida ou
  qualquer bloqueio técnico relevante. Adia-se o recurso, não a Alpha 8 inteira.
- Se os gates técnicos passarem, publicar controle de aplicativos e sinal de
  idade como experimentais, disponíveis ao público. Nenhuma conta é
  supervisionada automaticamente: a configuração é explícita.
- Explicar o caráter experimental e a cobertura nas notas de versão, descrição
  pública e configuração do responsável. Não afirmar proteção completa ou
  conformidade legal sem evidência correspondente.
- O parecer já aprovado, segundo o mantenedor, examinou lista local de apps,
  aviso, retirada da supervisão e sinal de idade declarada. Buscar novo parecer
  é desejável, mas sua obtenção não é requisito automático para a Alpha 8.
  Revisar a matriz pública de responsabilidades (#10) com o profissional antes
  da Beta 1. As faixas e a API podem ser refinadas após essa revisão.
- Se houver problema grave após publicar, impedir novos vínculos e novas
  consultas de idade, preservando restrições existentes até correção ou
  recuperação assistida.

## Contas, papéis e ciclo de vida

- Primeira versão: somente contas **locais novas** criadas para supervisão no
  Lyra. Contas de rede e conversão de contas comuns existentes ficam fora do
  escopo. Contas comuns continuam funcionando como hoje.
- O administrador local cria a conta supervisionada e vincula um único
  responsável. O responsável pode ter conta comum, com autorização restrita à
  criança vinculada. Só ele altera regras; o administrador pode recuperar o
  vínculo sem reduzir restrições.
- A conta supervisionada usa somente sessão gráfica GNOME local. Bloquear
  login por TTY, SSH e sessão remota. A proteção cobre o uso dessa conta sem
  privilégios dentro do Lyra; inicialização externa e acesso físico ao disco
  ficam fora da promessa do recurso. Administrador/root mantém poderes de
  gestão e as demais contas não recebem restrições parentais.
- Para retirar a supervisão antes da maioridade, o administrador inicia a
  operação e ele e o responsável a aprovam. Se forem a mesma pessoa, são
  necessárias duas confirmações explícitas. Arquivos e configurações pessoais
  permanecem; dados parentais são apagados, exceto marcador aleatório mínimo
  antirrestauração. Snapshots e backups controlados pelo Lyra precisam ser
  tratados; se a limpeza segura não puder ser confirmada, bloquear a retirada
  comum e explicar o motivo.
- O responsável altera a faixa declarada quando considerar necessário; não há
  data de nascimento armazenada nem prazo periódico de confirmação. A mudança
  para 18+ exige administrador e responsável e encerra a supervisão. A conta
  passa a funcionar exatamente como uma conta comum, sem sinal de idade.
- Quem alegar maioridade pode procurar o administrador **fora da interface da
  criança**. Se o responsável discordar, o administrador pode verificar a
  maioridade e retirar a supervisão sem ele. Não guardar documento ou imagem;
  decisão e data são apagadas com os dados parentais ao concluir. Se backups
  do Lyra ainda impedirem a limpeza, cessar imediatamente as restrições da
  pessoa adulta e manter os dados parentais bloqueados até a limpeza.

## Aplicativos e interface

- Nenhum aplicativo de usuário vem aprovado para uma nova conta
  supervisionada. Permitir apenas a infraestrutura estritamente necessária à
  sessão GNOME. A lista de execução é explícita e específica por criança.
- O responsável revisa identidade, origem e descrição do app no Vega GTK;
  vegad aplica a política. Essa revisão não é auditoria de código nem garantia
  sobre o comportamento interno de apps de terceiros.
- O responsável pode aprovar apps Flatpak e RPM identificáveis de qualquer
  origem configurada, com origem e alerta visíveis. Administrador ou
  responsável instala Flatpak com permissão restrita; instalar RPM exige
  administrador. Instalação global por administrador nunca aprova
  automaticamente a execução pela criança.
- Na conta supervisionada, instalações pelo gestor de pacotes exigem aprovação
  prévia. Um navegador aprovado ainda pode baixar arquivos; o Lyra controla
  instalação e execução, sem prometer filtrar cada download ou site. AppImage,
  scripts e executáveis avulsos sem identidade aprovável ficam bloqueados.
- Aprovação de um app RPM não autoriza todos os programas do pacote. Processos
  auxiliares só são admitidos quando identificados como componentes do app
  aprovado. Atualizações assinadas preservam autorização se identidade,
  origem e finalidade não mudarem; mostrar a nova versão ao responsável.
  Mudança de repositório, assinatura, publicador ou finalidade exige nova
  aprovação.
- Revogação impede novos processos imediatamente, avisa o usuário e concede
  até 10 segundos para o processo já aberto encerrar antes de interrompê-lo.
- A criança vê apenas aviso simples de supervisão e orientação para falar com
  o responsável. Não há tela detalhada de regras nem solicitação de apps ou
  revisão na conta da criança. Um navegador aprovado não implica filtro de
  sites/conteúdo na Alpha 8.

## Sinal de idade experimental

- Primeira versão: somente para apps Flatpak/RPM locais identificados e
  autorizados a consultar por conta supervisionada. Sites no navegador e
  contas comuns não recebem sinal.
- O responsável declara uma faixa **não verificada**: 0–12, 13–17 ou 18+.
  A faixa 18+ encerra a supervisão, logo não gera sinal pela API desta versão.
  Não apresentar a declaração como idade verificada.
- Um app recebe apenas resposta para a idade mínima e a finalidade previamente
  declaradas e aprovadas pelo responsável. Cada par limite/finalidade exige
  autorização própria. Finalidade permitida: verificar idade mínima para
  acesso ou conteúdo; não publicidade ou perfilamento. Sem finalidade clara,
  negar a consulta.
- Se toda a faixa declarada atende ao mínimo, responder positivamente; se
  toda a faixa está abaixo, responder negativamente. Se o limite cruza a
  faixa, responder **indeterminado**, sem autorizar com base nesse sinal. Se o
  app exigir verificação confiável, informar indisponibilidade e deixar a
  verificação ao próprio app. Sem sinal ou finalidade autorizada, negar sem
  revelar idade nem confirmar vínculo parental.
- Alterar a faixa revoga as autorizações/respostas antigas; revogação de
  permissão interrompe consultas futuras e invalida credenciais emitidas. O
  Lyra não consegue apagar conhecimento que um terceiro já recebeu; explicar
  esse limite ao responsável. Não aceitar consultas arbitrárias a múltiplos
  limites para reconstruir a faixa.

## Continuidade, recuperação e dados

- Emissor e renovação de política são locais, sem dependência de internet.
  Se o serviço parar, usar a última política íntegra e assinada por até **sete
  dias** desde a renovação; bloquear mudanças. Política expirada ou inválida
  bloqueia o login da criança, sem liberação temporária. Administrador ainda
  pode usar sua própria conta e ferramentas de recuperação.
- Se chave/estado forem perdidos, administrador e responsável restauram estado
  íntegro. Sem backup íntegro, recriam política do zero, inicialmente com zero
  apps aprovados. A criança só volta a entrar após política válida.
- Exibir ao responsável política atual e mudanças de aprovação/revogação;
  não coletar histórico de abertura, tempo de uso, navegação ou lista de
  processos para supervisão. Guardar somente eventos mínimos de autorização
  por janela móvel de 30 dias enquanto a supervisão estiver ativa. Ao retirar,
  apagar esses registros imediatamente, preservando apenas o marcador técnico
  antirrestauração descrito acima.

## Gates de implementação

Estas decisões não alteram o `NO-GO` técnico atual. Antes de habilitar o
recurso, comprovar enforcement sem evasão nos canais anunciados, identidade
confiável dos apps e componentes auxiliares, instalação/autorização separadas,
isolamento de contas comuns, ciclo de vida de identidade e recuperação,
integridade após rollback, API de idade com autorização por finalidade e
limite, UX Vega/GNOME, e qualificação da ISO/instalação. Falha nesses gates
adia somente o recurso parental na Alpha 8.
