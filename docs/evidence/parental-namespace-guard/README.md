# Conferência de mudanças nas fontes de produtores — 03/10/2026

Implementação experimental, somente leitura: `namespace.py` captura todas as
entradas das árvores declaradas pela fábrica confiável, incluindo arquivos com
extensões desconhecidas e diretórios vazios. O plano vincula o conjunto exato de
raízes, conteúdo por SHA-256, inode/dispositivo, proprietário, modo, tamanho,
mtime/ctime e identidade do lock permanente. Mudanças invalidam o plano.
Não modifica o inventário histórico nem permite marcar um produtor como completo.

O leitor abre cada componente do caminho com O_NOFOLLOW, confere proprietários
e permissões, rejeita links simbólicos/hardlinks e objetos especiais, e limita
entradas, bytes e profundidade. Enumeração e leitura são por descritores; cada
entrada é revalidada, assim como a listagem do diretório. Duas capturas consecutivas
precisam coincidir. Arquivo ausente, árvore insegura ou limite excedido gera recusa;
o leitor não cria lock ou diretório faltante.

`plan()` usa lock compartilhado não bloqueante. `execute()` confere o plano antes
de autorizar, solta o lock para autorização e o readquire antes de qualquer efeito.
Confere fontes e identidade do lock antes/depois de cada callback. Escritores
cooperantes precisam usar o mesmo inode de lock EX. Se a fonte muda após o primeiro
efeito, os seguintes não executam. Não desfaz efeitos anteriores, não publica
Active, não remove barreiras e não implementa journal ou autorização Polkit real.
As callbacks são internas à fábrica, nunca caminhos/ações enviados pela GUI.

26 testes novos usam árvores reais temporárias no worktree e flock real, incluindo:
adição/remoção, edição, substituição atômica por bytes idênticos, subdiretórios,
primeiro arquivo numa árvore vazia, troca do diretório raiz, troca do lock durante
a autorização/efeitos, contenção de escritor, autorização negada/com exceção,
links/FIFO, permissões inseguras, limites e mudança entre as duas capturas.
Duas integrações com o núcleo `Discovery` verificam recusa antes de qualquer stop
e interrupção entre stops com fechamento dos pins. Nessas duas integrações o
backend de processos é sintético: não são novas provas de revogação nativa.

Suíte completa: **530 testes Python PASS**, incluindo os 26 novos. Executada no
worktree, sem alegação de export limpo. Não foi iniciada VM nesta etapa; a VM
anterior permanece desligada. Evidência anterior de 23 controles nativos não
qualifica automaticamente esta nova implementação. Falhas preliminares do teste
vieram do proprietário 65534 das raízes de mount do sandbox: a fábrica de teste
agora declara explicitamente esses proprietários de ancestrais. O padrão do núcleo
continua root (0); dono alternativo e ancestrais são opções de fábrica de teste,
nunca seletores de cliente. A configuração de produção ainda não existe.

Benefício: detecta mudanças nas fontes fora da lista de rotas conhecidas, evitando
usar um plano antigo depois de adicionar um produtor. Risco: a conferência estrita
pode recusar árvores upstream com links legítimos ou mudanças durante updates;
não foi habilitada no produto. Reversão: remover apenas estes arquivos experimentais,
sem alterar barreira/configuração de conta. Não há pacote, serviço ou hook instalado.

## Limite da garantia e próximo aceite

A conferência cobre **mudanças nas árvores escolhidas**, não prova que essas árvores
incluem todos os produtores. Não resolve configuração do manager em memória,
solicitações pendentes, handlers carregados, descritores antigos, outras fontes,
rotas dinâmicas, subprocessos, NSS ou revisão monotônica/antirollback. A captura é
uma observação limitada no tempo, não vigilância contínua. Escritas root fora do
protocolo do lock pertencem à manutenção confiável, sem promessa contra root hostil.
Uma fonte desconhecida já presente no snapshot precisa de classificação/adaptador;
sua inclusão no hash não autoriza considerá-la suportada. Os snapshots ficam em
memória; não acrescentar caminhos/comandos de apps ao journal do produto.

Próximo aceite: usar esta conferência na VM para as fontes efetivamente consultadas
pelo adaptador D-Bus, com autoridade de fábrica root, adição de rota após autorização,
alteração entre efeitos, reconciliação da configuração carregada e recusa de fonte
não classificada. Só depois avaliar autoridade de cobertura mais ampla. Não inventar
um certificado global a partir do scanner ou de sete chaves de adaptadores.

#6/#102 permanecem abertas; controle parental integral NO-GO. Host/PAM de produto,
receitas/RPM/OBS/ISO intactos. Verificação offline:
`python3 docs/evidence/parental-namespace-guard/verify-evidence.py`.
