# Handoff — validação do instalador KDE (2026-09-02)

## Estado ao reiniciar o host

A instalação limpa da ISO KDE foi concluída e o sistema instalado iniciou pelo
disco virtual. A validação final de first boot passou.

Resultado observado dentro da VM:

- KDE Plasma abriu normalmente;
- `graphical.target` é o alvo padrão;
- `display-manager.service` está ativo;
- a unidade canônica resolve para `display-manager-legacy.service` e executa
  `/usr/bin/sddm`;
- o pacote instalado do display manager chama-se `sddm-qt6` (por isso
  `rpm -q sddm` não encontra um pacote com o nome antigo);
- `plasma6-desktop-6.6.4-bp161.1.2.x86_64` está instalado;
- NetworkManager, firewalld e CUPS estavam ativos;
- `plasmashell` estava em execução;
- não havia unidades systemd com falha.

O gate correto foi executado como usuário normal, depois de autenticar o sudo:

```console
sudo -v
lyra-system-smoke first-boot --acknowledge-journal vm-tdx
tail -2 first-boot-result.json
```

Resultado final:

```json
"status": "passed"
```

O reconhecimento `vm-tdx` cobre exclusivamente a mensagem esperada nesta VM:

```text
virt/tdx: TDX not supported by the host platform
```

Executar todo o smoke com `sudo` não é válido, pois o gate rejeita corretamente
`root` no check `installed-user`. O binário deve ser iniciado pelo usuário
instalado, usando a credencial sudo previamente armazenada para as leituras
privilegiadas.

## Correção compartilhada e risco para GNOME

O problema era uma suposição específica do GNOME no gate compartilhado, não na
cópia de arquivos ou na seleção de pacotes do instalador. O smoke exigia
`gdm.service`; isso foi substituído pela unidade canônica
`display-manager.service`, válida para GDM, SDDM e LightDM.

Commit no repositório compartilhado:

- `lyraos-desktop`: `a49d8ac` — `Check the canonical display manager unit`

Commits dos sabores que incorporam o compartilhado corrigido:

- `lyraos-desktop-kde`: `0ea73ae`
- `lyraos-desktop-xfce`: `9be37cc`

Branch atual do compartilhado no momento do checkpoint:

- `alpha8-fail-closed-gates`, alinhada com
  `origin/alpha8-fail-closed-gates`.

A alteração não muda pacotes, configuração do GDM ou conteúdo instalado no
GNOME. Portanto, não há mecanismo funcional pelo qual ela quebre o GNOME. O
risco residual é apenas de cobertura: o gate genérico confirma que há um
display manager ativo, mas não que cada sabor usa a implementação esperada.
Como endurecimento futuro, considerar contratos específicos por sabor.

Testes repetidos no host após a instalação:

```console
python3 -m unittest tests.test_installer_ui tests.test_live_smoke \
  tests.test_system_smoke tests.test_image_build
```

Resultado: 88 testes passaram.

## Artefatos da VM

Diretório do ensaio:

```text
/var/tmp/lyraos-desktop-kde-1.1-security-final-1003
```

Artefatos importantes:

- ISO: `iso/LyraOS-Desktop-KDE-1.1-alpha.7-x86_64.iso`;
- disco instalado: `vm/lyra-os-install.qcow2`;
- monitor: `vm/qemu-monitor.sock`;
- evidência live/installed: `vm/upgrade-guest-evidence.jsonl`;
- UUID da instalação: `59f8c5de-b26b-4d30-9213-5beec0b7fee5`.

O arquivo de evidência contém um boot `session: live` e um boot posterior
`session: installed`, ambos com a mesma UUID de instalação.

## Próximo passo recomendado

1. Após o reboot do host, reler este handoff e confirmar o estado dos três
   repositórios.
2. Considerar uma validação curta do GNOME com o gate canônico para encerrar o
   risco residual de regressão antes da promoção.
3. Se desejado, criar contratos específicos que garantam GDM no GNOME, SDDM no
   KDE e LightDM no XFCE, mantendo o check canônico compartilhado.

## Trabalho paralelo registrado

Foi criada a issue de pesquisa sobre o legado do Poseidon Linux e a possível
experiência Lyra para cientistas:

- <https://github.com/lyra-os-linux/lyraos-desktop/issues/59>

