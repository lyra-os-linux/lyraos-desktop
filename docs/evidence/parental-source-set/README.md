# Plano de fontes presentes e opcionais — 04/10/2026

8 controles na VM e 570 testes Python PASS (16 novos). A matriz nativa passou na
primeira execução, comando rc0/stderr vazio. VM restaurada e desligada. Produto,
host/PAM/receitas/RPM/OBS/ISO intactos; #6/#102 abertas, parental integral NO-GO.

`SourceSet` é uma extensão experimental do leitor histórico, sem modificá-lo.
Vincula diretórios presentes/ausentes, arquivos regulares obrigatórios/opcionais,
identidades dos ancestrais, identidade do lock e aliases exatos declarados pela
fábrica. Para caminho ausente, guarda o componente inexistente, sufixo restante,
identidade e stamp do ancestral existente. Assim, criar só um diretório intermediário
já invalida o plano; ausência não é descartada silenciosamente.

A abertura ocorre por descritores e O_NOFOLLOW, com conferência de donos/modos.
Arquivos e árvores presentes mantêm hashes/identidades e limites do núcleo anterior;
o orçamento agregado inclui arquivos soltos e diretórios. Alias permitido exige
symlink do dono confiável com texto exato, inode/stamp e identidade do pai. Na VM,
o único alias declarado é /lib -> usr/lib e a árvore conferida é /usr/lib: não há
resolução genérica de links nem exceção para links desconhecidos no scanner.
Duas capturas precisam coincidir. Escritores cooperantes usam o mesmo lock EX;
o leitor usa SH nos efeitos, sem mantê-lo durante a autorização externa.

Na VM, a fábrica usa os 20 arquivos do grafo levantado anteriormente mais o
/etc/dbus-1/system-local.conf opcional, duas árvores de políticas e as três raízes
reais de ativação do pacote v36. Antes de começar, confere versão dos pacotes e
hashes do grafo anterior. O plano registra três ausências: o override e duas raízes
alternativas. Integração usa BrokerFence histórico e ListActivatableNames real.
A classificação da fábrica aceita apenas o mapa original de fontes/hashes;
fonte nova invalida o plano antigo e também recusa um plano novo até reconciliação.
Isso é catálogo fechado de fixture, não classificação completa de apps upstream.

Controles nativos:

- autorização negada não executa o marcador;
- criação do override sob EX durante autorização invalida antes do marcador;
- criação das raízes /usr/local/share e /usr/lib com definição nova recusa antes
  do marcador; planos novos recusam fonte não classificada;
- política vendor criada entre callbacks interrompe a segunda;
- após remover a fonte/recarregar, plano novo é conferido e EX recebe contenção
  dentro de efeito sob SH;
- hashes das configurações, contas e PAM, lista original de nomes ativáveis e
  PID454 do barramento são preservados.

Os callbacks são marcadores de teste somente leitura, não stops de processos.
A política entre callbacks é uma injeção root deliberadamente fora do protocolo
cooperante do lock. Não houve ativação de payload, revogação real, mudança de PAM,
MAC ou contas. Troca do alias foi testada em diretórios temporários Python; /lib
não foi modificado na VM. Não atribuir revogação nativa anterior a esta matriz.

Os 16 testes novos exercitam filesystem/flock reais, ausência do override e
ancestral, raiz alternativa, aliases substituídos/inesperados, symlink no caminho
ausente, configuração obrigatória ausente, arquivo alterado, permissões inseguras,
budget combinado, plano de especificação diferente e interrupção entre efeitos.
Dono alternativo/ancestrais mapeados são declarados na fábrica de teste; o padrão
do núcleo e a execução na VM permanecem root. Suíte no worktree, não export limpo.

Não resolve grafo automaticamente depois de uma atualização. O conjunto observado
é fixado pela fábrica confiável: se a configuração muda, requer nova resolução e
qualificação. Não avalia semântica de políticas, precedência de nomes duplicados,
handlers carregados, fontes de unidades/timers/cron ou revisão/antirollback. A
captura não é vigilância contínua nem promessa contra root hostil. Um novo snapshot
por si só não autoriza aceitar fonte nova. Não há certificado global/publicação
Active, API cliente de caminhos ou journal de caminhos/comandos de apps.

Benefício: impede que um plano autorizado ignore fontes que surgem onde antes não
havia arquivos ou diretórios. Risco: recusa conservadora em updates/manutenção e
alterações no ancestral de uma ausência; integração fica isolada. Reversão: remover
somente os caminhos originalmente ausentes e reload, já executados. Restauração
independente confere as duas raízes ausentes, override/policy/lock removidos,
config/PAM/contas/alias e broker preservados. Helpers/logs permanecem na VM; não
é rollback completo de disco nem auditoria de kernel. Nenhum RPM instalado.

Próximo: classificar as definições e a precedência dos produtores do inventário
real, recusando duplicidade ambígua e fonte sem adaptador. Só depois qualificar
inibição/cobertura completa; fonte observada ou hash conhecido não constitui
produtor seguro nem certificado para toda a conta.

Verificação offline: `python3 docs/evidence/parental-source-set/verify-evidence.py`.
