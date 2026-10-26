# Gate #9: controle parental básico

Gate da [issue #9](https://github.com/lyra-os-linux/lyraos-desktop/issues/9)
para o controle parental básico do Lyra OS 16.1
([plano](parental-controls-plan.md),
[qualificação](parental-controls-upstream-qualification.md)). Roda na VM do gate
da candidata, sobre a instalação feita pelo instalador, e entra na evidência
da ISO como os demais gates. Resultado `NO-GO` se qualquer item falhar.

## Parte automática

Na VM instalada, como a conta administradora criada no instalador:

```sh
kiwi/test/guest/installed-gate.sh parental
```

A seção `parental` cria uma conta supervisionada temporária
(`lyra-gate-child`) pelo vegad, como o Vega faz, e confere:

| Item | Esperado |
| --- | --- |
| Pacotes | `lyra-parental-controls`, `malcontent-control`, `sheliak`, `vegad`, `vega-gtk` instalados |
| Flatpak | ausente por padrão |
| Conta | criada no grupo `lyra-supervised` |
| malcontent | Console, `gnome-terminal`, fish e Vega no filtro da conta |
| Administração | `SetAdmin` recusado para a conta supervisionada |
| `sudo` e `su` | recusados com a senha da própria conta |
| SSH | `DenyGroups lyra-supervised` em vigor |
| TTY | `/etc/pam.d/login` igual ao do fornecedor mais a linha `pam_access` |
| Alt+F2 | travado só no perfil dconf da conta supervisionada |
| Settings | regra polkit de leitura presente |

A conta temporária é removida no fim, mesmo quando um item falha. Junto com a
seção `sudo-policy`, que prova que uma conta fora do `wheel` não usa `sudo`.

## Parte manual

Na sessão gráfica, com uma conta supervisionada criada pelo Vega (Usuários →
Novo usuário → Conta supervisionada) e regras definidas pelo botão "Controle
Parental": navegadores restritos e um aplicativo bloqueado.

1. Vega, Usuários: selo "Supervisionada", "Tornar admin" desabilitado, quadro
   do que a supervisão cobre e não cobre no editor.
2. Configurações → Sistema → Usuários → conta da criança: "Controle parental"
   mostra o estado real, não "Desabilitado".
3. Sessão da criança: navegadores, terminais e Vega ausentes do dock, do menu
   Aplicativos, do menu Iniciar e da busca (Shell e Sheliak).
4. Sessão da criança: Alt+F2 não abre nada.
5. Sessão da criança: `Ctrl+Alt+F3` recusa o login dela; o administrador entra.
6. Vega, Software: "Habilitar Flatpak" mostra o aviso com o parágrafo de
   atenção, pede a senha do administrador e o Flathub aparece; o quadro da
   conta supervisionada passa a mostrar o aviso do Flatpak.

## Reinício, atualização e rollback

Repetir `installed-gate.sh parental` e os itens 3 a 5 depois de:

1. reiniciar a VM;
2. `zypper up` com os repositórios do Lyra;
3. rollback para o snapshot anterior à atualização pelo Vega ou pelo Snapper,
   seguido de reinício.

## Limites aceitos

Não fazem parte do gate e estão documentados como fora do escopo: atalhos
`.desktop`, scripts e macros próprios da criança, programas baixados na pasta
pessoal e Flatpak habilitado pelo administrador (qualificação R23 e R6/R7).
