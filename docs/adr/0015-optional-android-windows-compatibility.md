# ADR 0015: compatibilidade Android e Windows permanece opcional e desacoplada da ISO

- Estado: substituída pela ADR 0016
- Data: 2026-08-26
- Relacionadas: issues #14, #15, #16, #17, #18, #19, #20 e #50

## Contexto

A Alpha 7 abriu a avaliação de execução de aplicativos Android e Windows sem
autorizar que runtimes ampliem silenciosamente a instalação padrão. A mudança
coincide com a migração do Desktop para openSUSE Leap 16.1, cuja qualificação
tem precedência sobre novos componentes de compatibilidade.

No levantamento feito em 2026-08-26:

- `wine` 11.0 e `wine-gecko` possuem builds concluídos em
  `openSUSE:Backports:SLE-16.1`; `wine-mono` 10.1.0 está em
  `openSUSE:Leap:16.1:NonFree`;
- o projeto mantido `Emulators:Waydroid` publica Waydroid 1.6.3 e seus módulos
  para Tumbleweed, Slowroll e Leap 16.0, mas não possui target Leap 16.1;
- Waydroid requer Binder por DKMS ou KMP, LXC, namespaces, política SELinux,
  rede privilegiada e uma imagem Android separada. O próprio pacote registra
  acesso direto do container ao hardware necessário;
- Bottles oferece oficialmente apenas o pacote Flatpak como formato suportado
  e testado. Runners, DXVK, VKD3D e outros componentes têm cadência própria e
  são obtidos no primeiro uso com verificação de checksum.

Usar os pacotes Waydroid destinados ao Leap 16.0, copiar um projeto pessoal do
OBS ou introduzir módulos de kernel próprios contrariaria a base 16.1 e
aumentaria o risco operacional. Reempacotar Bottles e seus componentes também
transferiria ao Lyra uma cadência de segurança incompatível com o objetivo LTS.

## Decisão

### Instalação padrão

Nenhum runtime Android ou Windows entra em `kiwi/config.xml`, nenhum serviço é
habilitado por padrão e nenhuma associação de `.exe`, `.msi` ou `.apk` executa
arquivos automaticamente. A ISO e o sistema instalado permanecem completos
sem esses componentes.

### Aplicativos Windows

Bottles via Flathub é o baseline aprovado para um piloto opcional. O Lyra não
reempacota Bottles, runners ou bibliotecas baixadas por ele e não concede
overrides globais de filesystem. O usuário escolhe instalar o aplicativo e
autoriza diretórios adicionais de forma granular quando necessário.

Os pacotes Wine oficiais do Leap 16.1 são a alternativa de diagnóstico e um
caminho futuro possível, mas não formam nesta Alpha uma segunda experiência de
produto concorrente com Bottles. Integração no Vega depende de contrato que
mostre origem, tamanho, permissões, downloads posteriores e limitações antes
da instalação.

### Aplicativos Android

Waydroid fica **no-go para integração na Alpha 7**. A avaliação pode continuar,
mas implementação e empacotamento só reabrem quando existirem simultaneamente:

1. target Leap 16.1 mantido e publicável para Waydroid e Binder;
2. origem, licença, assinatura, atualização e retenção da imagem Android
   aprovadas;
3. compatibilidade comprovada com o kernel do Leap 16.1, SELinux, Secure Boot,
   suspensão e as GPUs homologadas;
4. remoção comprovada de módulos, políticas, mounts, namespaces, regras de
   rede e serviços;
5. responsável e prazo definidos para CVEs do runtime e da imagem.

Não é permitido contornar o gate usando RPM do Leap 16.0, DKMS de repositório
ad-hoc, script remoto privilegiado ou imagem Android sem procedência fixada.

## Fronteiras de confiança

- arquivos Windows permanecem na área privada do Flatpak/Bottles;
- acesso ao diretório pessoal inteiro não é concedido nem recomendado;
- compartilhamento usa portal ou diretório explicitamente autorizado;
- executáveis de terceiros continuam não confiáveis mesmo dentro do runtime;
- credenciais, Google Play Services, lojas proprietárias e componentes sem
  licença redistribuível não são fornecidos pelo Lyra;
- diagnósticos são locais e exportados somente por ação do usuário;
- compatibilidade nunca é apresentada como suporte universal ao aplicativo.

## Gates do piloto Windows

Antes de qualquer exposição pelo Vega ou promoção para a Beta 1:

- instalar e remover Bottles sem alterar o baseline do host;
- validar um aplicativo livre ou redistribuível em Intel, AMD e NVIDIA
  disponível, com caminho sem Vulkan documentado;
- verificar áudio, Wayland/XWayland, clipboard e acesso a arquivos;
- confirmar ausência de acesso ao `$HOME` fora de permissões explícitas;
- interromper download e criação de bottle e comprovar retomada ou reversão;
- atualizar e remover runner sem afetar outros bottles;
- confirmar ausência de serviços, mounts, portas e associações residuais;
- medir armazenamento, RAM, CPU e impacto no boot;
- registrar versões e checksums dos componentes usados no teste;
- manter P0/P1 e falha de isolamento como bloqueadores de promoção.

O estado do host deve ser capturado sem privilégio antes da instalação, com o
aplicativo instalado e depois da remoção:

```bash
./scripts/bottles-pilot-evidence.py before --output bottles-before.json
./scripts/bottles-pilot-evidence.py installed --output bottles-installed.json
./scripts/bottles-pilot-evidence.py removed --output bottles-removed.json
./scripts/bottles-pilot-evidence.py review \
  --before bottles-before.json \
  --installed bottles-installed.json \
  --removed bottles-removed.json \
  --output bottles-review.json
```

O coletor não instala, executa nem remove software. Ele apenas registra estado,
permissões, overrides, serviços de usuário e sockets em escuta; `observed` não
significa aprovação do isolamento, que continua dependendo da revisão das três
evidências e dos testes negativos. A revisão automática retorna
`review-required` quando não encontra resíduos; somente inconsistência de fase
ou resíduo detectável produz `failed`. Nunca produz `passed`.

## Reversão

Como os componentes não entram na composição da ISO, a reversão primária é
retirar o ponto de descoberta do Vega e desinstalar o Flatpak opcional. Dados
do usuário não são apagados automaticamente; a interface deve distinguir
remoção do aplicativo e exclusão irreversível dos bottles.

Qualquer protótipo Android permanece fora dos repositórios de release. Se um
gate futuro falhar, seu projeto staging é desabilitado e nenhuma dependência,
serviço ou repositório chega ao sistema do usuário.

## Consequências

- a migração Leap 16.1 continua qualificável sem regressões causadas por
  módulos ou serviços de compatibilidade;
- Windows pode ser experimentado com o formato sustentado pelo upstream, mas
  sua cadeia dinâmica exige evidência adicional antes de integração no Vega;
- Android é adiado de forma explícita, sem importar artefatos 16.0 para cumprir
  uma data;
- #19 não é transferida automaticamente à Beta 1: só um novo go autoriza sua
  reabertura neste ciclo;
- #16 passa a tratar apenas integrações próprias do Lyra; não duplica os
  pacotes Wine oficiais nem o Flatpak Bottles.
