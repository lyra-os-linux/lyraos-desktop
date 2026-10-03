# Fontes de configuração do D-Bus instalado — 03/10/2026

12 controles na VM PASS, primeira execução, comando nativo rc0/stderr vazio.
Suíte completa rerodada: 554 testes Python PASS, incluindo 16 novos testes do
índice de dependências. Host/produto/PAM/receitas/RPM/OBS/ISO intactos; VM desligada.
#6/#102 abertas, controle parental integral NO-GO.

## Achados concretos

A VM usa dbus-broker-36-160100.2.1 e dbus-1-1.14.10-160100.2.1. A linha real do
launcher é `/usr/bin/dbus-broker-launch --scope system --audit`. Binários e fontes
do ensaio estão vinculados por SHA-256. A configuração lida começa em
/usr/share/dbus-1/system.conf; seu índice alcança 20 arquivos, 6 diretivas de
dependências e 17 arquivos no includedir vendor /usr/share/dbus-1/system.d.
Também referencia /etc/dbus-1/system.conf, /etc/dbus-1/system.d, o override opcional
/etc/dbus-1/system-local.conf (ausente) e contexts/dbus_contexts sob a raiz SELinux
/etc/selinux/targeted. SELinux está habilitado, com a VM em Permissive; este ensaio
não qualifica políticas, identidades NSS nem enforcement.

A fonte upstream [v36 launcher.c](https://github.com/bus1/dbus-broker/blob/v36/src/launch/launcher.c)
lista /usr/local/share, /usr/share e /lib para serviços de sistema. A versão atual
upstream inclui outras raízes; por isso não usar main como descrição do pacote
instalado. A leitura da tag é referência, não prova de ausência de patches da distro.
A decisão desta etapa usa probes do binário real: criar uma definição de serviço,
recarregar configuração, consultar ListActivatableNames, remover e recarregar.
O payload /usr/bin/false não é solicitado nem executado por este ensaio.

| Diretório testado | Nome fica ativável no pacote instalado? |
|---|---|
| /usr/local/share/dbus-1/system-services | Sim |
| /lib/dbus-1/system-services (aqui /usr/lib/dbus-1/system-services) | Sim |
| /usr/share/dbus-1/system-services | Sim |
| /etc/dbus-1/system-services | Não |
| /run/dbus-1/system-services | Não |

Esses negativos valem para esta configuração/pacote, não para toda versão futura.
O ensaio anterior vigiava somente a terceira raiz e /etc/dbus-1/system.d; deixou
fora duas raízes reais de ativação, políticas vendor e overrides/includes. A flag
global negativa anterior estava correta: esta lacuna impede emitir cobertura.
Ordem de resolução de nomes duplicados/precedência ainda não foi qualificada.
O probe /lib resolve o alias na VM como observação; não libera symlinks no scanner.

## Implementação e limites

`dependencies.py` é um índice limitado de diretivas, não substituto do parser do
broker. Preserva ordem e duplicatas, includes opcionais ausentes e condicionais
SELinux sem descartá-los; recusa dependências aninhadas, novos tipos/atributos,
valores booleanos ambíguos, servicedir relativo e expansão de entidades. Entrada
até 64KiB/4096 nós; o parser XML não busca DTD externo. Diretórios padrão ficam
como diretiva sem expansão presumida: a fábrica deve vinculá-los à versão instalada.
Não interpreta semântica de policy/limit/SELinux nem emite autorização/certificado.
A referência de includes está em [v36 config.c](https://github.com/bus1/dbus-broker/blob/v36/src/launch/config.c).

`native.py` indexa o grafo com leitura de arquivos via descritores e conferência
root/regular/nlink/modo usando a primitiva histórica Namespace.open_absolute.
Includedirs são observados; o percurso não é um snapshot transacional do grafo.
Ciclos e limites são recusados. O include opcional ausente é registrado, mas sua
não existência ainda não está protegida pelo plano/lock. Nenhum novo escritor,
autorização real ou caminho de publicação foi instalado. Os snapshots não entram
no journal de produto. A interpretação de dependências/policies não é completa.
Configuração em disco não prova identidade do conteúdo que o broker carregou.

Revalida hashes das configurações e bytes de passwd/group/PAM ao fim dos probes.
Broker450 mantém PID e retorna exatamente ao conjunto inicial de nomes ativáveis.
Cada arquivo criado é removido e cada diretório originalmente ausente é retirado
após seu probe; o fluxo nativo verifica essas remoções. O campo cleanup
created_paths_absent usa as listas residuais, vazias no caso de sucesso, e não
constitui sozinho prova de remoção; há verificação independente dos cinco arquivos
reservados e de ausência dos nomes carregados em restored.json. Não é auditoria
completa de arquivos, processos/kernel ou proteção contra root hostil. Helpers/logs
ficam em /root/dbus-config-audit; nenhum pacote ou política PAM/MAC foi instalado.

Benefício: corrige a lista de fontes a cobrir antes de qualquer alegação global,
com evidência do pacote executado. Risco de falso aceite por tratar o índice como
parser completo: gates permanecem fechados e as flags de semântica/identidade
carregada/cobertura global são false. Reversão: remoção das definições/diretórios
reservados e reload, já executados, preservando o broker. Suíte no worktree,
sem alegação de export limpo. Não houve falha nativa preliminar nesta matriz.

Próximo: vincular grafo de dependências, todas as raízes reais e ausência dos
includes opcionais ao plano; detectar adição do override, fonte alternativa,
symlink/alias trocado e precedência ambígua antes de efeitos. Depois qualificar
classificação e inibição de rotas fora do namespace de fixture. Não transformar
este levantamento em certificado global ou conclusão do controle parental.

Verificação offline: `python3 docs/evidence/parental-dbus-config/verify-evidence.py`.
