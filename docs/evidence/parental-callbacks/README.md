# Callbacks do GNOME no domínio restrito — 25/09/2026

**Correção experimental de componente. #6/#102 continuam abertas.** Não há
alteração na receita ou nos RPMs publicados. Continua o [ensaio do GDM](../parental-gdm/README.md).

## Causa demonstrada

O GNOME terminava com `could not allocate closure` mesmo depois de permitir
`execmem` exclusivamente ao seu domínio. O programa mínimo [probe.c](probe.c)
reproduziu a falha usando a biblioteca oficial instalada: `ffi_closure_alloc`
retornou NULL/ENOMEM no domínio do Shell, mas executou o callback na conta
comum. Não era falta de RAM.

O [SRPM oficial assinado](source.json) corresponde ao mesmo DISTURL de
`libffi8-3.4.6-160100.2.1` instalado. O pacote desativa trampolines estáticos;
em `src/closures.c`, `dlmmap` evita a alocação anônima RWX quando SELinux está
ativo e `dlmmap_locked` mapeia um arquivo de memória como executável.
A [auditoria](denial.txt) confirmou negação de `execute` para `memfd:libffi`,
rotulado com o tipo de memória comum da conta, em enforcing.

## Correção e controles negativos

O [delta CIL](shell-memory.cil) atribui um tipo exclusivo aos arquivos de
memória criados pelo Shell. Apenas o domínio do Shell recebe execução nesse
tipo. Substitui a transição antiga; não é uma política completa para instalar.
Não libera execução dos arquivos do usuário nem da memória da conta restrita.

Comparação nativa [antes](before.json) / [depois](after.json):

| Caso | Resultado depois |
| --- | --- |
| Callback fora do domínio restrito | Executou e retornou 42 |
| Callback no domínio do Shell | Executou e retornou 42 |
| Callback no domínio geral da conta | Negado |
| Mapeamento executável do tipo privado pela conta | Negado, EACCES |
| Escrita no tipo privado pela conta | Negada, EACCES |
| Escrita pelo mesmo UID fora do domínio | Permitida: confirma que a negação anterior é SELinux, não DAC |

Os dois testes do tipo privado usam um arquivo de fixture pertencente ao UID
1003, modo0600 e rótulo exclusivo. Não representam ainda um ataque real por
passagem de descritores. O teste substitui temporariamente o executável de
entrada por um programa instrumentado; esse programa não é o launcher do
produto. Os 12 controles de execução e seis testes de configuração anteriores
também passaram com a política alterada.

## Efeito na sessão real e limites

O Shell oficial iniciou e permaneceu ativo no domínio dedicado durante a
coleta do ensaio Wayland, com a falha de callbacks eliminada. A
[captura de `/proc`](gnome.json) confirmou o perfil dconf de root, backend
dconf e ausência das variáveis de código injetadas na unidade. Esse primeiro
ensaio usou `--no-x11` para separar os componentes.

O [ensaio seguinte](session-exercise.py) manteve o caminho normal e adicionou
um tipo não executável para os arquivos de lock criados pelo Mutter em `/tmp`,
além de autorização para os dois executáveis oficiais AT-SPI. A
[captura nativa](session.json) mostra Shell, barramento de acessibilidade e
registro AT-SPI ativos nos domínios esperados, com os 18 controles anteriores
passando. O servidor XWayland ainda tem execução negada. Não foram aprovados
aplicativos X11, leitor de tela ou a sessão completa. Serviços de configurações,
registro no GDM, Polkit e outros componentes ainda têm negações.

O programa compila com `gcc probe.c -lffi -lselinux -o probe`; executar fora da
VM não aplica confinamento. O [ensaio reproduzível](exercise.py) compila este probe na VM; requer
`/root/trusted-shell.c` e `/root/trusted-shell-config-faults.py` copiados dos
arquivos correspondentes desta pasta. Para o ensaio gráfico, copiar também
`session.py` para `/root/restricted-shell-session.py`; esse coletor aguarda
o encerramento do gerenciador do usuário antes de voltar a fixture para
permissive. Os resultados aceitos são coletados em enforcing. O worker de diagnóstico compilado da
etapa GDM e os helpers/política anteriores são pré-requisitos explícitos.
Fontes oficiais, logs completos de auditoria e restauração ficam em `analysis/2026-09-25/parental-callbacks/`.
O ensaio requer a VM marcada `lyra.parental-selinux-test=1` e os perfis e
helpers das etapas anteriores; não executar em uma conta real. O GDM original,
rótulos e arquivos foram restaurados e o módulo temporário removido.

Próximos: integrar os serviços da sessão, qualificar XWayland/acessibilidade,
testar descritores compartilhados e injeção entre domínios, todas as entradas
da conta, aplicativos reais, recuperação e atualização. A execução permitida
do mesmo UID fora do domínio reforça que a admissão completa ainda falta.
