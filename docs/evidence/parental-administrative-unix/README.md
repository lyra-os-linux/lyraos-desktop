# Efeito Unix real do adaptador administrativo selado

Resultado: **13 controles PASS**, com três comandos Unix reais e duas operações
sem efeito numa conta fictícia da VM. Arquivos de contas/backups restaurados por
hash, identidade e conta vizinha preservadas, limpeza confirmada e VM OFF/QEMU 0.
Backing raw manteve hash, tamanho, inode e mtime antes/depois.

[guest.py](guest.py) conecta [parâmetros selados](../parental-administrative-parameters/README.md)
ao [guard](../parental-administrative-guard/README.md) e executa os argv fixos em
ordinaryuser/UID1002 já existente. Fontes históricos permanecem inalterados.
Catálogo/inventário/ledger/locks são reais e root-owned; grupo é resolvido por
NSS da VM. Não cria/remove contas ou modifica a estação.

## Resultado do ensaio

| Operação | Efeito demonstrado |
|---|---|
| UpdateUser | Nome literal `Lyra fixture $(literal)` e grupo suplementar users aplicados; alteração da entrada após o plano não mudou efeito autorizado |
| SetAdmin true | Adicionou wheel e preservou users; identidade primária permaneceu exata |
| Repetir true | Adaptador observou que wheel já estava aplicado; nenhum comando/alteração adicional |
| SetAdmin false | Removeu wheel e preservou users; identidade primária permaneceu exata |
| Repetir false | Adaptador observou wheel ausente; nenhum comando/alteração adicional |
| Autorização negada | Nenhum comando nem escrita nos arquivos de contas |
| Nova barreira durante autorização | Guard recusou despacho; nenhum comando nem escrita nos arquivos de contas |

A adaptação no guest trata explicitamente o estado já aplicado de SetAdmin;
não chama gpasswd -d quando o usuário já está fora de wheel. Isso é comportamento
do **adaptador do ensaio**, não correção já integrada ao UsersService publicado.
Os parâmetros/GIDs continuam revalidados pelo envelope antes do adaptador.

Antes de cada comando, probes EX nos três locks falham, comprovando que a
conferência e o despacho mantêm as leases: catálogo/inventário/withdrawal.
Autorização nova usa callback que adquire EX nos mesmos locks fora das leases.
Perfil é argumento literal de subprocess.run sem shell. O usuário-alvo provém
do Account selado pelo serviço, não de outro argumento da GUI.

A identidade (nome/UID/GID/grupo primário) ficou igual depois de cada efeito.
A conta vizinha installeduser/UID1000 conservou identidade/perfil/grupos.
Linhas passwd dos demais usuários ficaram iguais durante o ensaio e shadow
não mudou. Estado final de contas/PAM/SELinux e arquivos passwd/group/gshadow/
shadow, inclusive backups com sufixo -, voltou aos hashes iniciais.

## Risco, restauração e escopo

Este teste concede administração temporária à conta fictícia: foi executado
somente após confirmar marcadores/serial da VM e disco qcow2 descartável. O
backing raw foi conferido antes/depois. A conta-alvo não tinha processos no início.
Conteúdo original dos arquivos foi guardado em memória e em backup root-only
0700/0600 dentro da VM, sem publicar senhas/hashes de senha como conteúdo.
O ensaio restaura esses arquivos no final e remove backup e fixtures.

Restauração integral desses poucos arquivos é **procedimento do laboratório
exclusivo**, não recuperação de produto nem receita para a estação. Produto
precisa coordenar mutações concorrentes e recuperar transações sem sobrepor
alterações administrativas alheias. Reversão de produção não está qualificada.
Não há crash/reboot ou falha I/O entre os efeitos e a restauração neste ensaio.

Autorização/remetente ainda são callbacks do controlador; esta etapa não repete
[o ensaio D-Bus/Polkit](../parental-service-auth/README.md) nem qualifica sua
composição com os efeitos Unix. Identidades são locais e fictícias, prova
positiva é JSON sintético, sem login/PAM real. SELinux permaneceu Permissive.
Não demonstra política MAC, quiescência, grupo com geração estável, antirollback,
criação/remoção de contas, senha/foto, supervisão ou enforcement de aplicativos.

## Evidências e próximo componente

[result.json](result.json) guarda controles, argv/retorno, no-ops e hashes de
restauração; [execution.json](execution.json) tem retorno 0.
[source-hashes.json](source-hashes.json) confere onze módulos enviados à VM.
[cleanup-check.json](cleanup-check.json), [poweroff.json](poweroff.json),
[vm-off.json](vm-off.json) e [disk.json](disk.json) identificam limpeza e discos.
[manifest.json](manifest.json) sela artefatos/fontes.

```sh
python3 docs/evidence/parental-administrative-unix/verify-evidence.py
```

[fixture.py](fixture.py) adapta a preparação anterior para pasta exclusiva;
[host-run.py](host-run.py), [vm.py](vm.py) e [host.py](host.py) arquivam o driver de
analysis/2026-10-05/parental-administrative-unix. Usa runtime exclusivo
/tmp/lyra-parental-administrative-unix-20261005/system.qcow2. Não são instaladores.
Não repetir a suíte 805 ou cortes históricos por esta evidência independente;
os modelos/testes estão inalterados por hashes.

Próximo: conectar o guard/parâmetros/efeito real ao transporte e autorização
reais numa fixture integrada, verificando identidade do chamador, negação,
revisão e recuperação. Depois, integrar o serviço de produto exige os gates
#2/#5, lifecycle/persistência/rollback/papéis, #6/#102 e UX/ISO. Produto NO-GO.
Instalação local após conclusão continua autorizada pelo mantenedor, que criará
nova conta local de criança/adolescente; preservar a conta principal e concluir
criação/migração/recuperação/pacote antes de instalar.
