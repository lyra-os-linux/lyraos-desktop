# OBS limitado ao Leap 16.1 — 28/09/2026

Por instrução do mantenedor, novas compilações e publicações em staging e
release ficam limitadas ao openSUSE Leap 16.1. Os projetos Lyra já tinham esse
único alvo. Vega/Fina mantinham Tumbleweed habilitado; foram alterados os quatro
metadados de projeto para desabilitar build e publish nesse repositório.

Os 20 metadados de projeto/pacote foram examinados. Não havia override de pacote
que exigisse alteração; nenhum pacote-fonte, prioridade, arquitetura, caminho de
base, repositório ou histórico foi removido. Os XMLs anteriores e candidatos,
com hashes em plan.json, permitem comparar ou reverter a mudança. applied.json
registra leitura autenticada após cada gravação, evitando a visão anterior da
API pública logo após o PUT.

O manifesto conserva os alvos históricos com enabled=false. O gate rejeita outro
alvo ativo, base substituída, falta de disable em build/publish e overrides que
reativem o alvo. As verificações de artefatos exigem apenas alvos habilitados.
A suíte local passou 235 testes; a qualificação de pacotes/ISO segue separada.
