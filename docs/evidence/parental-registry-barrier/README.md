# Barreira persistente e leases por geração — ensaio v2

Em 01/10/2026, o protótipo v2 resolveu na VM os dois gaps observados no v1:
`begin` agora persiste a negação antes de testar a quiescência, e uma sessão de
A não conserva o lock de metadados nem impede B de concluir sua transição.
Este é código experimental de evidência, não um serviço de controle parental.
O v1 e suas evidências permanecem preservados em `../parental-identity/`.

## Contrato exercitado

- `.transaction.lock` serializa apenas leituras/gravações curtas do registro.
  PAM mantém esse lock só durante a decisão; contenção nega sem esperar.
- `.lease-<generation>.lock` conserva um inode estável para cada associação.
  O PAM mantém lease compartilhado até close/end; o writer tenta exclusivo
  sem bloquear. Uma geração em uso não pode ser tombstonada.
- `begin` publica/fsync a `.barrier-<generation>`, prepara seu journal,
  grava `transitioning` e journal `blocked` antes de tentar o lease exclusivo.
  `Busy` deixa a barreira durável. Repetir `begin` após fechar as sessões
  retoma a mesma transação bloqueada; não gera outro enrollment.
- Journals são independentes por geração. Nome/UID/GID/grupo de registros
  não tombstonados não podem colidir; a transição de B não pode reutilizar
  uma identidade ainda ocupada por A.
- `publish` exige tombstone e quiescência da geração antiga. Grava o alvo
  no journal, cria novo lease e barreira de publicação antes de gravar
  `active`. Só remove a barreira nova após journal `committed` durável.
  A barreira antiga continua negando a geração tombstonada.
- Recuperação explícita mantém transações incompletas em `recovering` e
  nunca as reinscreve. Uma barreira publicada antes de seu journal também
  impede admissão. Recuperar um commit antigo não remove uma barreira
  posterior de outra transição da geração nova; a barreira de publicação
  identifica sua transação de origem.

Os arquivos são root-only, regulares, sem symlinks/hardlinks, com limites
compatíveis com o leitor PAM. O leitor nunca cria o lease ausente. Enforcing
SELinux e o contexto pendente exato continuam obrigatórios nas contas
supervisionadas; contas comuns mantêm seu fluxo.

## Resultados

| Ensaio | Verificações | Evidência |
| --- | ---: | --- |
| Writer, isolamento e interrupções | 52 | `writer-result.json` |
| Manager nativo e lingering | 30 | `native-manager-result.json` |
| PAM real com duas contas | 18 | `two-account-pam-result.json` |
| Senha real/GDM nativo | 22 | `gdm-result.json` |

O writer foi interrompido via `os._exit(91)` em 22 checkpoints; o teste verifica
negação antes/depois da recuperação e estabilidade numa segunda recuperação.
Uma interrupção antes da primeira publicação de barreira não é uma transição
confirmada e conserva a associação original ativa. Os demais checkpoints
pré-commit não admitem a associação nova.

O PAM de duas contas mantém um handle aberto de A; `Busy` passa a impedir
outra admissão de A, enquanto B entra, transiciona e entra com geração nova.
A continua viva até close/end. Um controle adicional mantém o registro
`active` e publica apenas a barreira: PAM nega A e permite B. Assim a negação
não depende apenas do estado `transitioning`. Esse harness root/libpam e o
payload ELF não autenticam um login; a senha real é exercitada no ensaio GDM.

O ensaio manager usa o PAM vendor `systemd-user`, observa o lease em `sd-pam`,
lingering sem login interativo e reload/reexec. Após Busy, é necessário
encerrar o manager e reinscrever explicitamente antes dos testes de falhas.
A espera por descarte de registros logind/runtime não corrige nem comprova
resolução de uma corrida upstream.

O GDM repete os 22 cenários anteriores com writer/guard v2, senha guest
aleatória via stdin, worker diagnóstico e sessão ELF mínima. Worker e
`sd-pam` conservam leases por geração. As oito recusas de abertura exigem
causa exata, worker/manager/conta corretos, tentativa SESSION_OPENED, NONE,
parada, session-start-failed e saída; depois há 2 segundos sem payload nem
sucesso posterior. Senha incorreta é uma recusa de autenticação distinta.
Senha correta enviada após a barreira autentica/autoriza, mas não abre sessão.
Conta comum continua entrando nos controles correspondentes.

## Reprodução e integridade

Usar apenas a VM descartável com marcadores `lyra.parental-selinux-test=1`,
`lyra.parental-identity-test=1`, serial `lyra-admission-test` e disco
`/tmp/lyra-parental-identity-20260928/system.raw`. Os scripts exigem esses
marcadores e root. Não instalar o módulo nem usar o writer no host.

Copiar `writer.py`, `pam-guard.c`, `diagnostic.py`, `native-manager.py`,
`two-account-pam.py`, `gdm.py`, `restore-check.py` para `/root/barrier-<nome>`.
Executar sequencialmente diagnostic → native-manager → two-account-pam → gdm
→ restore-check. Os ensaios pressupõem os helpers das etapas anteriores;
`provenance.json` registra seus hashes e os IDs de execução efetivos.
O GDM reutiliza `../parental-registry-gdm/launcher.cil` e `evidence.py`,
`../parental-password/client.py`, `../parental-managers/session.c` e
`../parental-transitions/transition.py`. O PAM reutiliza
`../parental-identity/pam-probe.py` e `pam-lease-holder.py`.

A conferência offline executada foi:

```sh
python3 docs/evidence/parental-registry-barrier/verify-evidence.py
python3 -m unittest discover -s tests -p 'test_*.py'
```

Hashes dos fontes e resultados conferidos; 270 testes Python passaram.
`restored.json` confirma de forma independente managers/GDM parados, ausência
de processos/sessões das fixtures, remoção de registro/módulo/política,
worker oficial restaurado e SELinux Permissive. Os ensaios confirmam também
restauração de shadow/PAM/GDM/desktops/AccountsService. A VM foi desligada,
QEMU terminou com código 0. Nenhuma senha aparece na evidência exportada.

## Limites e próximo trabalho

Não houve instalação no host, alteração de receita, publicação OBS ou ISO.
Não é boot da candidata, GNOME completo, UX ou confinamento do greeter. O
cliente GDM parte do controlador root e baixa UID/GID a gdm; não representa
uma invasão. O rótulo do estado é aplicado pelo controlador da fixture, não
por gerenciamento MAC de produto.

Houve perda de eventos audit por backlog (avisos até `audit_lost=520`). Não
usar esses logs como inventário completo AVC; as conclusões funcionais vêm de
eventos PAM/GDM explícitos e observação dos processos/contextos. Não foram
ensaiados perda física de energia, falhas reais de armazenamento nem fsync
com erro. A recuperação ainda é helper manual, não serviço no boot.

A barreira impede admissões cooperativas novas; não revoga uma sessão já
admitida, um túnel SSH previamente autenticado ou produtores que não passam
por esse guard. A quiescência de leases não comprova que todos os processos,
cron/timers/D-Bus/serviços `User=` terminaram. Não autoriza hot enrollment de
handles iniciados sem o guard, mudança arbitrária de contas por root, adoção
da arquitetura de produto ou fechamento de #6/#102.

Próximo ensaio: revogação de conexões/autenticações antigas e produtores
persistentes, mantendo esta barreira v2 como base. ADR, autoridade/recuperação,
serviço de ciclo de vida, UI/Polkit/privacidade e update/rollback continuam
pendentes de decisão e qualificação.
