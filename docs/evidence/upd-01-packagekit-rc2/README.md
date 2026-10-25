# UPD-01: coexistência offline com PackageKit na RC 2

Ensaio de 25/10/2026 sobre a ISO `LyraOS-Desktop-16.1-rc.2-x86_64.iso`,
sha256 `af42e088991863e170dbf6d411fb3ea9ad41a097e0e9ed5ab3945a8a093e10a3`.
O sistema foi instalado pelo Lyra Installer numa VM UEFI (`kiwi/test/build-and-run-vm.sh --skip-build`),
com `lyra-upgrade-0.2.5-lp161.1.2` e `PackageKit-1.3.6-160100.2.1`.

`kiwi/test/guest/packagekit-gate.sh prepare --reboot` instalou a fixture inerte
`lyra-offline-fixture` 1, baixou a versão 2 por `pkcon --only-download update`
e preparou o pedido por `pkcon offline-trigger` (`/system-update` →
`/var/lib/PackageKit/prepared-update`). No boot offline, `lyra-upgrade-offline.service`
iniciou e terminou com sucesso, sem criar `/var/lib/lyra-upgrade/operations`.
O PackageKit aplicou a versão 2 (`Success=true`), removeu o marcador e reiniciou.
`verify` não encontrou units em falha e removeu a fixture e o repositório.

A saída completa das duas fases, copiada da porta virtio `org.lyraos.UpgradeEvidence`,
está em [guest-output.txt](guest-output.txt).
