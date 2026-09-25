# GDM oficial e admissão da conta restrita — 25/09/2026

Continuação da [ativação gráfica](../parental-graphical/README.md).
**#6/#102 permanecem abertas. Não há proteção da conta inteira qualificada.**
Esta pasta contém uma proposta de correção e evidências de diagnóstico;
a receita e os pacotes publicados não usam o patch.

## Defeito localizado no GDM

PAM prepara o contexto SELinux da conta para o próximo `exec`. O GDM executa
os hooks de root PostLogin e PreSession antes do fork da sessão; nessa ordem,
os hooks tentam consumir o contexto destinado ao usuário e falham na fixture.
Limpar o contexto apenas no processo pai depois do fork não corrige os hooks.

O [patch](gdm-root-hook-context.patch) salva e limpa o contexto pendente apenas
durante a chamada dos hooks e o restaura antes do fork. Falhas ao salvar,
limpar ou restaurar retornam erro. Os chamadores de PostLogin e PreSession
tratam esse retorno com PAM_ABORT e não criam a sessão. PostSession ocorre
após a sessão e mantém o comportamento de limpeza do GDM.

O SRPM oficial assinado `gdm-48.0-160100.2.1` tem o mesmo DISTURL do pacote
da VM. Todas as alterações aplicáveis a x86_64 foram aplicadas antes do patch
de diagnóstico, que entrou sem fuzz. [Proveniência](source-provenance.json).
O worker compilou e os três hooks oficiais passaram no ensaio nativo com
SELinux enforcing. [Resultados e trechos do journal](native-result.json).
A compilação usa opções de diagnóstico (Wayland, sem
X11/XDMCP/Plymouth/audit); **não é uma reconstrução do RPM de produção**.

## Testes de falha reproduzíveis

`test-hook-context.py` compila a função C extraída do código corrigido, com
stubs que injetam falhas nas APIs SELinux. Exige Python 3 e GCC; não precisa
de root, SELinux ativo ou VM:

```sh
python3 docs/evidence/parental-gdm/test-hook-context.py
```

São oito casos com suporte SELinux: fluxo normal; erro ao salvar; erro ao
limpar; erro ao restaurar; hook que falha mas exige restauração; ausência de
contexto pendente; SELinux desativado em runtime; sessão de programa. Outros
dois verificam a compilação sem suporte SELinux. Todos passaram, inclusive
quando a função foi extraída diretamente da árvore oficial corrigida.
[Resultado](hook-tests.json). O teste aceita esse arquivo-fonte como argumento
para repetir a extração, em vez de usar o trecho incluído nesta pasta.

## Limite atual da sessão GNOME

A conta comum abriu GNOME Wayland oficial em enforcing na VM de comparação.
A conta restrita progrediu pelos hooks e pelo launcher do GDM, mas a sessão
completa continua reprovada. O `/usr/bin/gnome-session` oficial é um wrapper
shell e pode iniciar o shell de login do usuário. O ensaio chamou diretamente
`gnome-session-binary`; essa substituição não preserva ainda toda a semântica
de idioma e inicialização e não deve ser distribuída.

Com os executáveis nativos autorizados apenas na fixture, GNOME Shell
48.8/GJS 1.84.2/mozjs 128.14.0 falha ao criar o contexto JavaScript: `execmem`
é negado no domínio geral. `GJS_DISABLE_JIT=1` não eliminou essa necessidade.
Liberar `execmem` para todo o domínio enfraqueceria o bloqueio já testado de
código arbitrário; a próxima prova usa um domínio exclusivo do desktop.
Essa separação, as fontes de JavaScript/extensões e o ambiente de inicialização
ainda precisam de qualificação. Não inferir segurança apenas de um login que
funcione ou de uma lista de negações no journal.

## Restauração e próximos requisitos

Os ensaios aconteceram exclusivamente no disco descartável marcado
`lyra.parental-selinux-test=1`. Scripts de ensaio restauraram bytes, modos e
rótulos dos executáveis, removeram os módulos temporários, autologin e PAM
de diagnóstico, pararam o GDM e deixaram a fixture permissiva fora dos testes.
SHA256 do worker oficial restaurado:
`40e1387811b74adcde44b8a34f03db1d032190867e1c5f4092bb9aa1362fdab8`.
Scripts, fontes expandidas e journals completos ficam no workspace em
`analysis/2026-09-25/parental-gdm/`.

Permanecem necessários: sessão GNOME e aplicativos reais, ambiente adulterado,
extensões/código carregado, portais, identidade de produção, todas as entradas
alternativas (TTY/SSH/cron/lingering), conta comum, recuperação e atualização.
Um processo do mesmo UID fora do domínio ainda executa Python na fixture:
o ensaio de domínio não equivale a proteção da conta. Não publicar o worker
de diagnóstico, encerrar #102 ou qualificar uma ISO com estas evidências.
