# Referências da configuração systemd — ensaio isolado

O objetivo é vincular `SystemdService` à unidade canônica, identidade local configurada, `ExecStartEx`, arquivo principal, drop-ins, executável e contas locais. A referência imutável é revalidada por duas leituras tipadas e duas conferências de arquivos. Uma configuração alterada invalida a referência. Isso prepara a integração do controle parental sem liberar contas nem conceder cobertura aos produtores.

## Resultado

602 testes Python passaram, incluindo 16 novos. A terceira tentativa nativa passou em 15 controles: nove referências reais, revalidação de todas, distinção de identidade/comando configurados, recusas, duas injeções por adaptadores e preservação. Os 12 `SystemdService` do catálogo anterior foram consultados. Nove entraram no subconjunto; três foram recusados: PolicyKit1 e login1 usam `Type=notify-reload`, timesync1 tem flag `ambient` em `ExecStartEx`. São configurações legítimas da base, ainda sem suporte neste contrato, não defeitos upstream. Nenhum produtor foi certificado; o serviço Exec-only restante requer abordagem separada.

A primeira tentativa (`attempt-1-native.py`) usou `GetUnit` e falhou antes de criar referências: a unidade Accounts estava definida em disco, mas não carregada. A segunda (`attempt-2-native.py`) usou `LoadUnit`, capturou nove referências e revalidou todas, mas falhou por exigir polkit no subconjunto aceito. A terceira corrigiu somente o ensaio, mantendo as recusas do núcleo. Resultados, fontes executadas e stderr das duas falhas estão arquivados. O núcleo/testes da suíte de 602 não mudaram entre as tentativas; somente o executor nativo mudou.

`LoadUnit` carrega a definição no manager sem solicitar início/parada. Pode alterar seu cache. Não se afirma reversão desse cache. Não foram editadas unidades, executáveis, contas ou PAM. `restore.py` conferiu independentemente todos os fingerprints aceitos, contas/PAM, declarações anteriores, PID do broker e ausência do lock não usado. QEMU sessão 20624 terminou com exit 0 após poweroff. Helpers/logs permanecem sob `/root/systemd-reference-test`; esta é preservação do escopo, não rollback integral do disco.

## Limites e reversão

Este código fica exclusivamente em evidências e testes, sem integração ao produto, RPM, OBS ou ISO; remover o commit local reverte a entrega. Callbacks são fornecidos pela fábrica confiável root, sem API pública para injetar caminhos ou fabricar referências. O executor abre arquivos via Namespace histórico, recusando symlinks, arquivos não regulares, múltiplos links, proprietário não root e escrita por grupo/outros; liga stamp e SHA256 com limite de 32 MiB. O núcleo depende dessa garantia do backend.

O subconjunto aceita tipos simple/exec/dbus/notify, um comando literal absoluto, identidade local e fontes únicas. Recusa DynamicUser, PAMName, RootDirectory/RootImage, grupos suplementares, flags de execução e expansão de ambiente/specifiers. Não é um leitor completo de configuração systemd. Propriedades são consultadas separadamente; as duas passagens não oferecem snapshot atômico nem impedem ABA. NeedDaemonReload falso e fingerprints não provam que o manager compilou exatamente esses bytes, nem cobrem todo ambiente, sandbox, capabilities ou fontes indiretas. Esses requisitos continuam no adaptador de execução.

UID/GID aqui são **configurados**, não credenciais efetivas. PID e timestamps de ExecStartEx são telemetria excluída da referência. Não foram qualificados pidfd, UID efetivo, descendentes, serviços compartilhados privilegiados, capabilities/MAC, ativação pendente ou revogação real. Falhas NeedDaemonReload/fingerprint foram injetadas nos provedores, sem editar disco; não equivalem a fault injection real. Nenhum root producer é isento. full_account_protection/global_coverage/running_credentials/real_activation_or_revocation continuam false. #6/#102 permanecem abertas e o controle parental integral permanece NO-GO.

Próximo: integrar a referência à observação do processo real e ao adaptador de ativação/revogação, incluindo políticas explícitas para os três casos recusados. Uma mudança de fonte ou credenciais precisa recusar efeitos antes de qualquer liberação.

## Conferência

Execute `python3 docs/evidence/parental-systemd-reference/verify-evidence.py` na worktree. O verificador confere hashes, fontes exatas das três tentativas, retornos, controles, resultados e preservação. A suíte foi executada na worktree, não em export limpo. `provenance.json` registra fontes e resultados; hashes garantem consistência local, não assinatura/autenticidade independente.
