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
a carga em uma máquina com suspeita de corrupção. O `stress-ng` foi instalado,
mas não foi executado após esse resultado.

Não surgiram mensagens de erro de memória, MCE, EDAC ou Btrfs no journal do
kernel durante a curta execução. A ausência é esperada caso a plataforma sem
ECC não consiga observar e reportar a falha.

## Interpretação

A primeira leitura diferiu do padrão esperado por um bit e a releitura retornou
o valor correto. Isso é consistente com uma falha transitória no caminho de
memória e reforça a hipótese de hardware ou firmware levantada na issue #60.
O resultado não identifica sozinho o componente: módulo, contato, slot,
controlador de memória, cache, alimentação e configuração de firmware continuam
como possibilidades.

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
