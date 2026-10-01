# Encerramento normal da sessão GDM e lingering

Em 01/10/2026: **8 controles nativos PASS, 270 testes Python PASS**, restauração independente PASS e VM desligada/QEMUrc0. Um dos controles reproduz a lacuna: saída da sessão não implica quiescência do manager com lingering.

Ensaio experimental derivado de [GDM/barreira V2](../parental-registry-barrier/README.md), exclusivo da VM descartável com serial lyra-admission-test e os dois marcadores de kernel. O worker diagnóstico, cliente peer GDM, autenticação pam_unix e guard/writer V2 são os mesmos das etapas anteriores. Não instalar no host ou em pacote de produção.

A sessão ELF mínima agora retorna espontaneamente 0 após 30 segundos. O observador não envia sinal ao payload/worker, não chama encerramento de sessão nem para GDM durante a observação. Isso permite distinguir o fechamento natural do worker/PAM da lease do manager, que tem lingering habilitado. Não representa o botão de logout nem a sessão completa do GNOME.

O ensaio compara o bloqueio antes/depois da saída, observa saída de payload e worker por pidfds e o inventário de leases por inode, mantém o PID do manager comum e do GDM, e só então invoca terminate-user para a conta supervisionada. A ausência de leases permite tombstone da geração; o marcador de lingering permanece até a limpeza para confirmar que não autoriza reinício do manager bloqueado.

[loginctl](https://www.freedesktop.org/software/systemd/man/252/loginctl.html) documenta que lingering mantém o manager após logout. A revogação exercitada aqui cobre a sessão e o manager desta fixture. As etapas SSH/systemd/D-Bus/cron já mostraram que logind não revoga todos os produtores. Não inferir quiescência de uma conta inteira, resistência a root, revogação de handles sem guard ou recuperação autorizada.

A senha aleatória fica apenas na VM e entra via stdin; o shadow original é restaurado. Os resultados passam por verificação de ausência desses segredos antes de exportar. O harness restaura arquivos PAM/GDM/AccountsService/desktops, worker oficial, rótulos, senha e SELinux; remove módulo/registro/política/sessão e os dois marcadores de lingering. Inspeção independente e desligamento são registrados na proveniência.

Reprodução: transferir exercise.py para /root/session-exit-exercise.py e session.c para /root/logout-session.c. Os demais helpers são os das evidências GDM/barreira V2. Executar python3 /root/session-exit-exercise.py pela VM marcada, sem outro ensaio simultâneo. Conferir result.json, restored.json e verify-evidence.py offline.

Limites: kernel/initrd direto e worker diagnóstico, não ISO candidata, GNOME, desbloqueio ou UX. Não há decisão de arquitetura de produção nesta evidência. #6/#102 permanecem abertas. Recuperação administrativa e ciclo real de contas/NSS ainda precisam contrato e qualificação.

Na tentativa preliminar, payload e worker saíram, mas uma expectativa incorreta exigia ausência de qualquer sessão logind da conta. No systemd257 desta VM, o manager aparece com Class=manager/Service=systemd-user. O harness passou a conferir a ausência da sessão de login e a permanência apenas dessa classe de manager. A tentativa (rc1) e sua limpeza estão em preliminary-result.json; não conta como qualificação concluída. Não houve alteração do produto nem de configuração logind para satisfazer o teste.

O kernel registrou perdas de audit (audit_lost=1,2,3); os resultados vêm de eventos específicos do worker/PAM, pidfds, estado de unidades e leases, sem afirmar inventário AVC completo.
