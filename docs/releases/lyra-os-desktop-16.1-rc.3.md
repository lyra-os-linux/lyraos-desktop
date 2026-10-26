# Lyra OS 16.1 RC 3 “Odisseia” — notas de lançamento (rascunho)

Terceira candidata de lançamento do Lyra OS Desktop 16.1 sobre **openSUSE Leap
16.1**. Em 25/10/2026 o mantenedor decidiu adiar a versão estável para incluir
o controle parental básico ([plano](../parental-controls-plan.md)). A RC 3
traz esse recurso e repete o gate completo. Build previsto para 16/11/2026;
lançamento realista em **26 de novembro de 2026**.

A identidade técnica será `16.1-rc.3`, tag `v16.1-rc.3`, arquivo
`LyraOS-Desktop-16.1-rc.3-x86_64.iso`. Estas notas são preenchidas à medida
que as frentes do plano entram na imagem.

## Exceção ao congelamento

O controle parental básico é uma funcionalidade nova depois da RC 1. Ele entra
por decisão explícita do mantenedor (25/10/2026), com qualificação em VM,
gate próprio e plano de reversão por frente. Detalhes e limites:
[qualificação 16.1](../parental-controls-upstream-qualification.md).

## Mudanças desde a RC 2

- Segurança: só o grupo `wheel` usa `sudo` com a própria senha. O instalador
  deixava qualquer conta virar root com a própria senha. A imagem passa a usar
  a política `sudo-policy-wheel-auth-self` do openSUSE, e o `lyra-release`
  corrige instalações existentes pelo zypper
  ([#191](https://github.com/lyra-os-linux/lyraos-desktop/pull/191),
  [#192](https://github.com/lyra-os-linux/lyraos-desktop/pull/192)).
- Controle parental: a imagem traz o aplicativo "Controle parental"
  (`malcontent-control`), aberto em Configurações → Sistema → Usuários. Uma
  regra polkit do próprio malcontent permite que o administrador veja o estado
  das restrições sem senha; alterá-las continua exigindo autenticação.
- Flatpak deixa de vir instalado (exceção ao congelamento, 26/10/2026). O
  Flatpak do Leap não aplica o controle parental; ele é habilitado na página
  Software do Vega, com aviso para contas supervisionadas, e o Flathub aparece
  junto. Instalações existentes mantêm o Flatpak.
- LinuxToys deixa de vir instalado. Continua disponível no repositório do
  Lyra para quem quiser instalar (decisão do mantenedor, 26/10/2026).
