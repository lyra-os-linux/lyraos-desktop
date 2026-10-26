# Frente 1, dia 1 (26/10/2026): resultados

VM: VM descartável (cópia do gate build #5, RC 2; run.sh; SSH local;
snapshots de disco "base" (antes do malcontent-control) e "dia1" (configurada, com
ovmf-vars.dia1.bin)). Contas: lyragate (wheel), crianca (comum).

- malcontent 0.12.0 já na imagem; malcontent-control + typelib-1_0-MalcontentUi-1 vêm do repo-oss.
- Gravação: malcontent-control grava no AccountsService (/var/lib/AccountsService/users/crianca, root 0600).
  Navegadores = blocklist de content type x-scheme-handler/http; instalação = AllowUser/SystemInstallation=false.
- Persistência: mantida após reboot.
- Criança não remove a política: malcontent-client, D-Bus Set e escrita no arquivo negados (ChangeOwn = auth_admin_keep).
  Também na sessão gráfica ativa (seat0): polkit pede senha de "Administrador", a senha da criança falha e,
  ao cancelar, "Error setting app filter"; política inalterada.
- "Restringir aplicativos" lista só Flatpak; sem Flatpak instalado a lista fica vazia (lacuna RPM confirmada).
- Shell: Firefox some do dock (favoritos) e da busca do overview.
- LACUNA Sheliak: menu Aplicativos > Internet mostra o Firefox e o abre (Firefox rodou como crianca).
  startMenu.ts, panelMenus.ts e search/indicator.ts listam via get_installed()/AppInfo.get_all() sem
  ParentalControlsManager.shouldShowApp(). Precisa de correção no sheliak (nova frente/PR).
- flatpak 1.16.6 não linka libmalcontent (#102 confirmado por ldd).
- gnome-software não está na imagem: item "GNOME Software respeita restrição" não se aplica.
- pam_malcontent.so existe, mas não está em nenhuma pilha PAM (limites de sessão não aplicados).
- i18n: "Unlock", "Unrestricted" e a descrição de "Adequação do aplicativo" sem tradução pt_BR.
- O mouse do monitor QEMU não funciona; navegação por teclado (Tab/espaço, ctrl+alt+tab no painel) funciona.

Dia 2: Settings 48 Usuários; RPM/navegador/terminal como criança (firefox pelo terminal, busca do Sheliak);
flatpak install --user como criança; su/pkexec/Vega; mecanismo pam_access no TTY.

## Desvio do plano

A VM não é Leap 16.1 puro: é a ISO do Lyra 16.1 RC 2 (build #5) instalada, com repo-oss do Leap 16.1.
Motivo: o alvo é o produto (Sheliak, Vega, polkit e repositórios do Lyra), e foi essa base que revelou a
lacuna do Sheliak. Pacotes do malcontent, AccountsService, flatpak e Settings são os do Leap 16.1, sem
alteração. Registrar na matriz da qualificação.
