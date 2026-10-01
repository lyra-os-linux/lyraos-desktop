# Reinício nativo e recuperação do registro experimental

Em 01/10/2026, 20 controles nativos passaram (6 preparação + 7 primeiro boot + 7 segundo boot), além de 270 testes Python. Dois reinícios reais e ordenados do kernel produziram três boot IDs distintos. A VM descartável foi restaurada, verificada independentemente e desligada. Nenhum arquivo do host, receita, pacote OBS ou ISO foi modificado por este ensaio.

A preparação admitiu o manager supervisionado com o contexto SELinux esperado, confirmou lease ocupada e publicou explicitamente a geração B. O writer V2 foi interrompido em checkpoints com rc91: deixou um journal antigo committed e, depois, uma barreira mais nova sobre a geração B ainda active. Ambos os managers tinham lingering habilitado e estavam ativos antes do reinício.

No primeiro boot, os hashes, modos e proprietários duráveis foram preservados. O helper experimental recuperou o journal antigo sem remover a barreira mais nova; a geração B passou a recovering, sem enrollment. O manager supervisionado iniciado automaticamente por lingering falhou com status224/PAM e mensagem exata do guard. O manager comum iniciou normalmente. Uma tentativa manual posterior também foi negada.

No segundo boot, o helper foi deliberadamente encerrado com status42 antes de recuperar o registro. O estado bloqueado permaneceu idêntico, o manager supervisionado continuou negado por PAM e o manager comum iniciou normalmente. O manual de [loginctl](https://www.freedesktop.org/software/systemd/man/252/loginctl.html) descreve a inicialização no boot com lingering; os resultados deste ensaio estão nos JSON locais.

## Fontes e reprodução

`prepare.py`, `recover-at-boot.py`, `verify-boot.py` e `cleanup.py` usam `common.py`. Exigem root, os dois marcadores de kernel e serial de disco lyra-admission-test. Guard e writer são os mesmos de ../parental-registry-barrier/, sem alterações. Executar exclusivamente em VM descartável com os pré-requisitos documentados nas evidências anteriores. Não instalar estes arquivos em produção. O controller reinicia QEMU após cada systemctl reboot porque usa -no-reboot. `restore-check.py` faz a inspeção final independente; `verify-evidence.py` verifica os artefatos offline, sem modificar o sistema.

`provenance.json` vincula fontes, artefatos e execuções por SHA256. `prepared.json`, `verified-recovery.json` e `verified-fault.json` registram os controles. `cleanup.json` e `restored.json` registram a restauração. O backup original de PAM e os helpers/resultados permanecem em /root da VM como evidência; nenhum hook, módulo, registro ou marcador de lingering deste ensaio permaneceu ativo.

## Limites e tentativas preliminares

Reinícios ordenados e interrupções de processo em checkpoints não qualificam perda de energia, falha de armazenamento, escrita parcial ou falha de fsync. O kernel/initrd foi lançado diretamente; não foi testada a ISO candidata, bootloader, sessão GNOME/GDM ou logout interativo. O launcher usa enforcing=0: o hook colocou SELinux em Enforcing antes de logind, sem qualificar o início do boot. O hook Before=logind é exclusivo da VM, não uma implementação aprovada para o produto. Auditoria completa do kernel não foi comprovada.

A recuperação preserva bloqueio; não existe aqui uma operação autorizada de recovering para novo enrollment. A publicação de controle ocorreu antes dos reinícios. Não foram realizadas mutações reais de conta/NSS. Backend, autoridade, recuperação administrativa, provisionamento, Vega/Polkit/privacidade e revogação geral de produtores continuam pendentes. Proteção parental completa permanece NO-GO (#6/#102). Os 30 controles anteriores de manager/lingering não foram repetidos.

Tentativas preliminares não contam como PASS: CLI incorreta do writer e suposição incorreta sobre retenção do journal foram corrigidas no harness; uma corrida entre remoção de sessão logind e novo manager exigiu aguardar drenagem; a primeira leitura pós-boot antecedeu o hook e passou a aguardar seu artefato. Limpezas explícitas foram feitas antes de repetir a preparação. As execuções correspondentes ficam na proveniência. Não são correções no produto.

Próximo: lacunas de logout/revogação e contrato explícito de recuperação/ciclo real de contas, antes da integração produtiva.
