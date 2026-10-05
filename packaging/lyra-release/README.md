# Identidade do Lyra OS

O lyra-release mantém o marcador de produto do Updater e a identidade exibida
em /etc/os-release. O Leap-release continua fornecendo /usr/lib/os-release e
os metadados de produto da base. Não há conflito ou duplicação de propriedade
RPM: o arquivo /etc/os-release é uma saída gerada, substituída atomicamente.
A verificação RPM do Leap-release apontará essa diferença esperada.

Após instalar/atualizar lyra-release, %posttrans aplica o nome, versão e logo.
Após transações de arquivos da base, %transfiletriggerin lê as alterações nos
prefixos /usr/lib e /etc e só aplica o auxiliar se os-release estiver na lista.
Usar os diretórios com filtro foi validado no RPM 4.20.1 do Leap; o ensaio com
prefixos de arquivo exatos não reaplicou a identidade. Não exige serviço,
monitoramento periódico, atributos immutable ou bloqueio de atualizações.

O suporte desta correção é Desktop 1.1 sobre Leap 16.1. O marcador próprio
continua sendo a autoridade do Updater. ID/ID_LIKE/VERSION_ID seguem o contrato
da imagem Lyra; LYRA_BASE_ID/LYRA_BASE_VERSION_ID e CPE_NAME conservam a origem.
Os campos de imagem existentes são salvos para sobreviver à substituição do
arquivo upstream. Não inventa novo estágio, checksum ou identificação de ISO.

O auxiliar mantém a identidade anterior e o digest do arquivo gerado em
/var/lib/lyra-release/identity-state.json. Na remoção final do pacote restaura a
identidade anterior somente se não houve uma edição posterior. Também preserva
identidades locais de outro ID e recusa bases/edições fora do escopo. Se houve
edição posterior, conserva arquivo e estado para revisão administrativa.

Validação: 10 testes, RPM construído e instalação, duas reinstalações reais do
Leap-release e remoção em overlay descartável. Sete verificações passaram;
evidências em docs/evidence/release-identity-20261005. A VM original não foi
modificada pelo ensaio de RPM. Três tentativas anteriores que falharam estão
arquivadas. O desligamento fechou o canal antes da resposta; QEMU exit0 confirma
a parada, sem alegar resposta bem-sucedida do RPC de poweroff.

O RPM assinado 1.1-lp161.2.1 foi promovido pelo SR1382519 e instalado na estação
como atualização de um pacote, via API do projeto release. A proteção automática
está ativa. A publicação pública do OBS, somente Leap16.1, passou pelo gate do
canal completo e pela verificação das assinaturas de metadata/RPM; o SHA256 do
RPM público é idêntico ao artefato já instalado. Evidência assinada e da estação:
`docs/evidence/release-identity-signed-20261005`.
A inclusão e qualificação do checksum da próxima ISO continuam pendentes.
