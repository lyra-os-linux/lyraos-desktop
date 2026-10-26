# Frente 1, dia 2 (26/10/2026): resultados

Base: snapshot "dia1" + lyra-release 16.1-lp161.2.1 do release (correção do sudo).

## Achado de segurança (fora do escopo, já corrigido)
- Qualquer conta comum virava root com a própria senha (10-installer com !targetpw global).
  Corrigido em lyraos-desktop#191/#192; lyra-release lp161.2.1 e lyra-installer lp161.38.1 publicados.

## Privilégios da criança (depois da correção)
- su root: falha (root bloqueado). pkexec, zypper, PackageKit (pkcon install) e ações do Vega
  (org.lyraos.vega.*: auth_admin): todos exigem administrador.
- PackageKit system-update é "yes" implícito: a criança pode aplicar atualizações do sistema (não é risco parental).

## Flatpak (#102) confirmado na prática
- Calculator bloqueado (app/org.gnome.Calculator/x86_64/stable no AppFilter; check-app-filter diz "not allowed"):
  `flatpak run org.gnome.Calculator` como criança ABRE o app.
- AllowUser/SystemInstallation=false: a criança faz `flatpak remote-add --user flathub` e instala
  org.gnome.Chess na própria conta sem nenhuma autenticação.
- Logo, sem flatpak com -Dmalcontent=enabled, nem bloqueio de app nem restrição de instalação valem para Flatpak.

## Navegador e terminal
- Firefox (bloqueado por x-scheme-handler/http) abre pelo terminal e por xdg-open: o malcontent só oculta.
- A criança tem terminal (Console) na sessão gráfica.

## Settings 48 (complemento)
- Desbloqueado, o painel continua "Desabilitado": ReadAny = auth_admin_keep e o Settings lê sem interação.
  Correção possível: regra polkit dando ReadAny (só leitura) a wheel em sessão local ativa.
- A linha abre `malcontent-control --user crianca` e pede a senha de novo (2 autenticações seguidas).
- A lista "Restringir aplicativos" mostra só Flatpak do sistema (Calculadora); o Chess instalado pela
  criança na conta dela não aparece para o administrador.
- Ajuda do Controle Parental (help:malcontent) falha: yelp e gnome-user-docs não estão na imagem.

## RPM por caminho e Sheliak
- Bloqueio por caminho funciona no Shell via CLI (malcontent-client ... /usr/bin/kgx): Console some da
  busca do Shell; a interface não oferece isso.
- Há dois terminais na imagem: Console (kgx) e gnome-terminal ("Terminal").
- Busca do Sheliak mostra Calculadora (Flatpak bloqueado) e Console (RPM bloqueado): lacuna confirmada
  também na busca, além dos menus.

## TTY (frente 3)
- Leap 16.1 não tem /etc/pam.d/login; o serviço usa /usr/lib/pam.d/login (fornecedor).
- pam-config --access (pilha comum) com regra por origem tty1..tty12 BLOQUEIA o GDM:
  gdm-password usa PAM_TTY=tty7 → "access denied for user crianca from tty7". Revertido.
- Única forma restante: copiar /usr/lib/pam.d/login para /etc/pam.d/login (perde atualizações do fornecedor).
  TESTADA: login com `account required pam_access.so accessfile=...` e regra `-:(lyra-supervised):ALL`:
  criança negada na tty3, administrador entra na tty3, criança entra pelo GDM normalmente.
  Essa cópia ficou ativa no snapshot dia2 e foi removida depois (snapshot dia2-final sem ela).
- Valor baixo: a criança já tem terminal na sessão gráfica; TTY/SSH não dão nada além disso.
  Recomendação: não bloquear TTY; registrar como fora do escopo. SSH: sshd não vem habilitado; DenyGroups
  só faz sentido se o administrador ligar o SSH (avaliar manter por ser barato e sem efeito colateral).

## GNOME Settings 48
- Página da criança em Sistema → Usuários tem a linha "Controle parental — Abre o aplicativo Controle
  parental". Mostra "Desabilitado" com o painel bloqueado, mesmo com restrições ativas (provável falta de
  permissão de leitura antes de "Desbloquear"). Integração existe; o rótulo engana.

## GNOME Software (instalado na VM só para o teste: gnome-software 48.4+backports, com libgs_plugin_malcontent)
- Não está na imagem do Lyra.
- Como criança, com instalação proibida: Mahjongg mostra "Install" habilitado. Origem Flathub do sistema →
  pede senha de administrador (polkit, não malcontent). Origem Flathub USER (remoto da própria criança) →
  INSTALOU sem senha. O plugin do malcontent não segura a instalação; a regra só valeria com flatpak+malcontent.
- Seletor de origem lista "Lyra OS — Unknown source" para RPM; abas em inglês (sem gnome-software-lang).

## Vega como criança
- vega-gtk abre e mostra Painel, Software, Serviços, Usuários etc. (leitura).
- D-Bus como criança: CreateSnapshot → "Not authorized"; ListUsers legível (nomes e grupos, como /etc/passwd);
  ListSnapshots → "Not authorized" fora da sessão ativa (o contrato diz "polkit: none"; investigar à parte).

## Estado da VM
Snapshot "dia2" (+ ovmf-vars.dia2.bin): grupo lyra-supervised com a criança, /etc/pam.d/login sombreado,
filtro: http, Calculator, /usr/bin/kgx, instalação proibida; Calculator no sistema; Chess na conta da criança.
Snapshot "dia2-final" (+ ovmf-vars.dia2-final.bin): sem a cópia do login; gnome-software instalado;
Mahjongg e Chess na conta da criança.
