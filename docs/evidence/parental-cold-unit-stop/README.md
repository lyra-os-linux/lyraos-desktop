# Serviços inativos — evidências fechadas em 05/10/2026

676 testes Python (18 novos) e 20 verificações VM passaram. Fontes, resultados, falhas
e restaurações estão vinculados em provenance.json e verify-evidence.py. Não foi
necessário repetir a suíte ou a matriz para fechar os registros já qualificados.

cold.py complementa GuardedExecution sem inventar PID. MixedExecution reutiliza
os pins originais para serviços ativos e confere serviços inativos antes de cada
efeito: referências anteriores às máscaras, owner/inibições históricos, boot,
MainPID0, inactive/dead ou failed/failed, Job zero, cgroup canônico vazio e
propriedades tipadas. Serviço inativo não recebe IPC nem row fictícia de job
concluído. Novo lote autorizado observa novamente após saída.

InvocationID pode ser limpo depois de saída/GC: NÃO garante ausência de execuções
no intervalo nem identidade imutável do objeto systemd. Apenas mudança observável
invalida o snapshot; a segurança deste escopo usa inibição e estado atual, não
histórico. Root continua autoridade confiável. A primeira matriz tentou afirmar
detecção de um ciclo completo start/stop e falhou; fonte, resultado e saída foram
preservados em failed-native-1. A matriz final recusa unidade ainda ativa e exige
novo lote após saída, sem alegar detectar toda execução transitória.

PAMName=systemd-user funciona na fixture antes da retirada e recusa novas entradas
após a retirada (status224), mas a referência original continua recusando PAM.
Processos de um serviço PAM já ativo ainda não estão qualificados para revogação.
A matriz não faz promoção nem dá cobertura global.

Uma falha da suíte completa por interferência de sys.modules foi arquivada em
failed-python-1; o loader dos novos testes passou a restaurar os módulos globais.
Depois, todos os 676 testes passaram. Uma exportação de hashes tentou incluir
verify-evidence.py, arquivo host não instalado na VM; failed-source-export-1 guarda
a falha read-only. Mapa corrigido, todos os hashes exportados conferem com as
fontes locais. A VM foi reaberta apenas para completar a coleta/conferir novamente
a restauração; duas sessões QEMU terminaram com código0, VM OFF.

native-cold.py reutiliza helpers imutáveis da etapa anterior em /root/unit-stop-jobs;
native.py original não foi sobrescrito. Fonte-map/guest-source-hashes vinculam
as dependências. Restauração-before-reopen e os leitores finais foram preservados.
O ensaio move/recoloca o mesmo inode de máscara SOMENTE como manutenção root da
fixture. Não há unmask/repair automático na API. Flags global/PAM-runtime/produção/
power-loss continuam falsas. Produto/host/RPM/OBS/ISO intactos; #6/#102 abertas.
