# ISO Desktop única e NVIDIA opcional — decisão de 16/09/2026

O Lyra Desktop terá **uma única ISO GNOME sem NVIDIA pré-instalada**. Após
instalar o sistema, o usuário poderá optar pelo driver no Vega GTK. A decisão
substitui as duas variantes planejadas em 14/09; a variante dedicada NVIDIA
foi retirada do escopo, sem reduzir os testes do driver.

A construção e a qualificação continuam em
[#63](https://github.com/lyra-os-linux/lyraos-desktop/issues/63) e
[#56](https://github.com/lyra-os-linux/lyraos-desktop/issues/56).
A issue histórica #62 permanece encerrada como não planejada. GNOME é o alvo
Desktop; KDE/XFCE continuam em segundo plano. A variante **Server com llama.cpp
+ NVIDIA** permanece na [Server #21](https://github.com/lyra-os-linux/lyraos-server/issues/21).

## Contrato de distribuição e qualificação

- Manter uma receita KIWI local, com inventário, checksum, SBOM e revisões RPM
  rastreáveis. OBS publica RPMs; não constrói a ISO.
- Impedir a entrada indireta da pilha NVIDIA por recomendações. Preservar
  Mesa, firmware e drivers necessários a Intel/AMD e operação híbrida.
- Incluir Vega GTK/vegad qualificados. Diagnóstico e abertura não pedem senha;
  instalação exige confirmação e autorização administrativa.
- Usar RPMs oficiais NVIDIA, módulo correspondente assinado pela SUSE e o
  metapacote `lyra-nvidia` publicado no OBS. Conjunto inicial: 610.57.04.
  Não usar o instalador `.run` nem escolher uma família por suposição.
- Validar GPU suportada, dependências, versões, assinatura, kernel atual e de
  destino, snapshots e recuperação. Não oferecer instalação parcial ou sem
  pré-condições satisfeitas. A presença de RPMs não comprova GPU funcional.
- A instalação opcional requer acesso aos repositórios. Não prometer driver
  proprietário no live ou instalação NVIDIA offline; qualificar e documentar
  os hardwares que inicializam/instalam pela imagem sem essa pilha.
- Testar instalação, update/reboot e recuperação; conferir também GNOME
  Software/PackageKit. Validar assinatura/Secure Boot, renderização/offload,
  Wayland, monitor externo, DPMS e suspensão em hardware real representativo.
  GPU virtual não qualifica essas funções físicas.
- Os testes locais de integração não homologam a ISO. Publicar somente após
  qualificar a candidata exata, sem P0/P1 aberto e com evidências identificadas.

## Acompanhamento

A [issue #82](https://github.com/lyra-os-linux/lyraos-desktop/issues/82) acompanha
kernel/KMP, versões oficiais e segurança. Desde 15/09, a estratégia é qualificar
o conjunto oficial adotado, substituindo a espera pelo conjunto antigo do Leap
até a RC1. Manter atualizações liberadas, sem locks de kernel. O contrato de
versões do metapacote exige manutenção e nova qualificação quando o driver muda.

Ordem do ciclo: issues → auditoria #78 → construir/testar a ISO GNOME única →
Alpha 8 após os gates. A auditoria ampla continua adiada.

## Contrato histórico do fluxo Vega G06

Os registros abaixo preservam ensaios e políticas anteriores; não comprovam
qualificação na base e no conjunto G07 atuais. Qualquer reaplicação precisa
conferir versão, propriedade dos arquivos e reversão. A política vigente de
atualizações liberadas prevalece sobre as retenções propostas nesse histórico.

- detectar conservadoramente GPU G06 suportada e bloquear hardware incerto;
- exigir confirmação explícita;
- verificar o estado do Secure Boot;
- criar snapshot Snapper somente leitura antes da primeira mudança;
- usar exclusivamente pacotes RPM do repositório oficial NVIDIA para Leap;
- instalar `nvidia-open-driver-G06-signed-kmp-meta` e
  `nvidia-userspace-meta-G06` em conjunto;
- rejeitar instalação parcial ou versões desalinhadas, auditando todos os
  RPMs G06 efetivos e não apenas os metapacotes;
- executar `dracut --force`, orientar o reinício e preservar rollback;
- após o reboot, verificar módulo ativo, `nvidia-smi`, Wayland e conectores
  DRM antes de declarar sucesso;
- qualificar suspensão por versão e topologia gráfica, bloqueando-a de forma
  reversível quando houver regressão conhecida;
- reconciliar a política no início do `vegad`, inclusive após atualizações que
  não tenham sido iniciadas pela tela NVIDIA.

## Descobertas preservadas

Testes anteriores encontraram um caso real em que o módulo assinado estava na
versão `580.159.03`, enquanto `nvidia-video-G06`, `nvidia-gl-G06` e
`nvidia-common-G06` permaneciam em `570.172.08`. O firmware GSP esperado não
existia e a saída HDMI ligada à GPU dedicada falhou. Os metapacotes de KMP e
userspace em lockstep corrigiram o cenário.

No gate histórico, a política proposta bloqueava mudanças sem KMP compatível.
A decisão vigente mantém atualizações liberadas, sem locks de kernel. Ainda é
necessário qualificar kernel, módulo, userspace e firmware juntos e oferecer
recuperação; não interpretar esse histórico como autorização para recriar locks.

Em 16/08/2026, o notebook híbrido Acer Nitro AN515-57 reproduziu uma segunda
classe de falha com a pilha `580.159.03`: durante a suspensão, o módulo NVIDIA
falhou em `mmuWalkUnmap`/`gpuSanityCheckRegisterAccess`, manteve o GNOME Shell
preso no kernel e provocou soft lockups. SMART, log NVMe, contadores Btrfs e um
scrub completo não encontraram erro de armazenamento. Essa combinação fica em
quarentena de suspensão e hibernação até uma versão posterior passar pelo gate.

A quarentena usa exclusivamente o drop-in gerenciado
`/etc/systemd/sleep.conf.d/90-lyra-nvidia-quarantine.conf`. O Vega só remove o
arquivo se o marcador de propriedade estiver presente, e o remove
automaticamente quando uma versão qualificada substitui a versão afetada.

## Gate histórico G06

- GPU NVIDIA real, incluindo o notebook híbrido disponível;
- Secure Boot ligado e desligado;
- instalação, reboot, `nvidia-smi`, Wayland e monitor externo;
- suspensão e retomada controladas, sem soft lockup, erro NVRM, falha de freeze
  ou incremento inesperado de desligamentos inseguros;
- aplicação e remoção automática da quarentena em versões bloqueada/aprovada;
- atualização conjunta de kernel/driver;
- falha parcial injetada e rollback para uma baseline inicializável;
- evidência revisável sem credenciais.

O fluxo não é declarado suportado enquanto qualquer item acima estiver sem
evidência ou houver P0/P1 aberto.
