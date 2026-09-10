# Aparência nativa do GNOME — 2026-09-05

Solicitação do mantenedor: usar GTK e GNOME Shell padrão, acompanhar a cor de
destaque do GNOME nos ícones Lyra e manter somente Dawn e Voyage no pacote de
wallpapers. KDE e XFCE preservam sua personalização nativa.

Benefício: eliminar os overrides GTK/Shell e delegar aparência, papel de parede
e ajustes aos componentes nativos do GNOME. Novos perfis não recebem mais o
import de CSS Lyra. O padrão da imagem aponta para o arquivo realmente
empacotado, `2702-dawn.png`.

Risco principal: configurações antigas podem manter um tema removido ou
sobrescrever CSS pessoal. A migração só reconhece nomes/CSS legados do Lyra,
restaura o backup anterior quando disponível e preserva personalização
independente. O sincronizador de ícones verifica a sessão GNOME e a presença da
variante instalada antes de alterar a preferência.

Validações locais:

- 45 testes de composição da imagem aprovados.
- 13 testes de migração/aparência aprovados, incluindo proteção de KDE/XFCE,
  CSS pessoal, backup, preferências bloqueadas e recursos ausentes.
- Nove cores verificadas com o backend de memória real de `Gio.Settings`.
- Build dos três pacotes visuais e inspeção dos RPMs aprovados: nenhuma árvore
  GTK/Shell Lyra, nove variantes de ícones e apenas Dawn/Voyage em PNG/JPEG XL.
- Vega GTK: 26 testes Rust e 10 testes Python aprovados; fmt, clippy e build
  aprovados. Não foi produzida nem qualificada uma nova ISO nesta alteração.

Reversão: reverter os commits de composição e pacotes em conjunto e publicar
novas revisões dos RPMs anteriores. Preservar os backups de CSS do usuário;
não restaurar estilos globalmente sem distinguir configurações pessoais.

Planejamento da Alpha 8 (seis ISOs com/sem NVIDIA):
https://github.com/lyra-os-linux/lyraos-desktop/issues/62.
