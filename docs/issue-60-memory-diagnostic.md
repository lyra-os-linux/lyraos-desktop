# Diagnóstico de memória da issue #60

Data: 2026-09-02

Issue: <https://github.com/lyra-os-linux/lyraos-desktop/issues/60>

## Objetivo

Investigar se as falhas de checksum do Btrfs e os crashes de processos
independentes podem estar relacionados a uma instabilidade no subsistema de
memória que não foi detectada pelo MemTest86+.

## Ambiente do ensaio

- Lyra OS 27.02 Alpha 6;
- aproximadamente 15 GiB de RAM física;
- dois módulos DDR4 SODIMM de 8 GiB e 3200 MT/s, configurados a 2933 MT/s;
- módulo `Controller0-ChannelA-DIMM0`: A-DATA `AD4S320038G22-BHYD`;
- módulo `Controller1-ChannelA-DIMM0`: fabricante `0x0080`, sem part number;
- `stressapptest-1.0.11-bp160.1.12.x86_64`;
- `stress-ng-0.17.04-160000.2.2.x86_64`;
- nenhum contador EDAC exposto pelo kernel;
- nenhuma mensagem MCE, EDAC ou `Hardware Error` no journal do boot antes do
  ensaio.

O conteúdo de `/usr/bin/stressapptest` correspondia ao checksum registrado no
pacote RPM instalado:

```text
c51957c6502be0b86b31be4304b171efb9e423b9004ca2458be6c7945fd2b7e6
```

## Execução

O teste foi configurado inicialmente para 15 minutos, usando 10 GiB de memória
e cópias com maior carga de CPU. Não foram habilitadas operações de teste em
disco:

```console
stressapptest -s 900 -M 10240 -W -l /tmp/lyra-stressapptest.log
```

O programa detectou uma divergência após 44 segundos:

```text
Report Error: miscompare : DIMM Unknown : 1 : 44s
Hardware Error: miscompare on CPU 6(<-6) at 0x7f18d921aa08:
read:     0x4a4a4a4ab5b5b5b4
reread:   0x4a4a4a4ab5b5b5b5
expected: 0x4a4a4a4ab5b5b5b5
'Checker8b10b32' read error.
```

O ensaio foi interrompido imediatamente depois da detecção para não prolongar
a carga em uma máquina com suspeita de corrupção.

Não surgiram mensagens de erro de memória, MCE, EDAC ou Btrfs no journal do
kernel durante a curta execução. A ausência é esperada caso a plataforma sem
ECC não consiga observar e reportar a falha.

## Testes complementares

### `stress-ng`

Foi executado um teste independente de memória, com dois workers de 5 GiB,
durante cinco minutos:

```console
stress-ng --vm 2 --vm-bytes 5G --vm-method all --verify --klog-check \
  --timeout 5m --metrics-brief --vmstat 30 \
  --log-file /tmp/lyra-stress-ng.log
```

O `stress-ng` concluiu 67.623.150 bogo operations com os dois workers
aprovados, zero falhas de verificação e zero métricas não confiáveis. Nenhum
erro relevante apareceu no journal do kernel.

### Repetição integral do `stressapptest`

O comando original foi repetido durante os 15 minutos completos, usando um
novo log:

```console
stressapptest -s 900 -M 10240 -W \
  -l /tmp/lyra-stressapptest-retest.log
```

O resultado final foi:

```text
Stats: Found 89 hardware incidents
Stats: Completed: 19767688.00M in 900.11s 21961.53MB/s,
       with 89 hardware incidents, 0 errors
Status: FAIL - test discovered HW problems
```

Os 89 incidentes ocorreram em endereços, workers e padrões de teste distintos.
Em todos eles, o XOR entre a primeira leitura e o valor esperado foi `0x1`, ou
seja, somente o bit menos significativo divergiu. Em 85 eventos a releitura
voltou ao valor esperado; em quatro, o mesmo bit continuou incorreto na
releitura.

Depois dos testes, os contadores persistentes do Btrfs continuavam em 21
eventos de corrupção, sem erro de escrita, leitura, flush ou geração. Nenhum
novo erro relevante apareceu no journal do kernel.

## Interpretação

A primeira leitura diferiu do padrão esperado por um bit e a releitura retornou
o valor correto. A repetição integral confirmou 89 ocorrências no mesmo bit,
incluindo quatro que persistiram na releitura. Isso é consistente com uma falha
numa via física comum do caminho de memória e reforça a hipótese de hardware ou
firmware levantada na issue #60. O resultado não identifica sozinho o
componente: módulo, contato, slot, controlador de memória, cache, alimentação e
configuração de firmware continuam como possibilidades.

Os dois módulos instalados são de fabricantes diferentes. Essa combinação não
prova defeito ou incompatibilidade, mas torna importante testar cada módulo
isoladamente antes de comprar peças. O `stress-ng` aprovado também não invalida
o resultado: ele usa algoritmos e padrões de acesso diferentes, enquanto o
`stressapptest` reproduziu a mesma assinatura em duas execuções.

Uma corrupção persistente do executável usado no ensaio é improvável, pois seu
checksum corresponde ao pacote RPM. Um defeito no kernel ou no próprio teste
ainda não pode ser descartado sem uma reprodução independente.

## Próximas validações

1. Fazer backup antes de novas cargas ou escritas intensas.
2. Repetir o `stressapptest` em um sistema live com outro kernel e com a
   partição principal desmontada.
3. Testar cada módulo de memória separadamente.
4. Alternar os módulos entre os slots para separar falha de módulo e de placa.
5. Se os módulos passarem isoladamente e falharem juntos, investigar timings,
   controlador de memória, BIOS e alimentação.
6. Manter imagens e artefatos produzidos durante o período afetado como não
   confiáveis até concluir a investigação.
