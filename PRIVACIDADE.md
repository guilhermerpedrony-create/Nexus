# Privacidade do Nexus

O Pestinha roda só no seu computador. Ele não envia nada para a internet.

## Chamada pelo microfone

A opção **Ouvir quando eu chamar Nexus** é desligada por padrão. Quando ativada,
o microfone padrão é processado continuamente em memória por um modelo Vosk local,
para detectar o nome Nexus. Depois da chamada, um modelo em português transcreve
a pergunta durante uma janela de até 15 segundos. O áudio não é gravado nem enviado à internet.
A pergunta e a resposta aparecem na janela de conversa e ficam somente na memória da sessão,
com contexto limitado. Não há identificação de quem falou;
outras pessoas, vídeos e áudio dos alto-falantes também podem ativar a chamada.

A escuta para ao desativar a opção, pausar, esconder, usar o pânico ou fechar o aplicativo.
Também para enquanto o pet estiver oculto por tela cheia. O menu da bandeja mostra
o estado do microfone. As respostas são somente escritas.

O modelo é baixado uma vez pelo comando explícito `setup/Preparar-Voz.py`,
do site do Vosk. O aplicativo não baixa nada automaticamente durante a escuta.

## Conversa e tarefas

As perguntas são enviadas apenas ao servidor local Ollama em `127.0.0.1:11434`,
usando o modelo Qwen instalado no PC, sem API de nuvem. O Nexus não envia tela,
rotina, arquivos nem histórico de programas ao modelo. O contexto da conversa fica
somente na memória da sessão. O Ollama é iniciado em modo local, com nuvem desligada.

Pedidos explícitos de anotações salvam o texto em `memory/notes/`. Abrir o navegador
acessa a página inicial configurada no comando (Google), usando o navegador padrão.
O modelo de conversa e o runtime são baixados explicitamente na preparação, dos
servidores oficiais do Ollama. Esses downloads não incluem as suas conversas.

## O que ele lê

- O **nome** do programa em primeiro plano (por exemplo `code.exe`). Nunca o título nem o conteúdo da janela.
- Quanto tempo você está sem usar teclado ou mouse, e se o teclado ou o mouse foram usados agora.
- A posição do cursor, para saber se ele encostou na bolinha, se você está em cima do pet (carinho,
  cutucar) ou perto dele no cantinho do castigo.
- Se uma janela cobre a tela inteira (para não aparecer em jogos ou apresentações).
- A posição e o tamanho das janelas abertas, para ele poder pousar nas barras de título.

Ele **não** lê o conteúdo nem o título de nenhuma janela, página, documento ou conversa.

## O que ele grava (tudo em `memory/`)

Do app e seu, direto em `memory/`:

| Arquivo | Conteúdo |
|---|---|
| `permissions.json` | As opções que você escolheu |
| `timeline.csv` | Uma linha por minuto: hora, categoria de programa, trocas de janela, ocioso. Só com "Aprender minha rotina" ligado |
| `panels.json` | Posição dos painéis, do notebook e da placa |
| `logs/pestinha.log` | Mensagens do programa (sem conteúdo de janelas) |

De cada personagem, em `memory/pets/<pet>/` (um personagem não lê a memória do outro):

| Arquivo | Conteúdo |
|---|---|
| `nervous.json` | Estado da rede neural (habituação e aprendizado) |
| `episodes.jsonl`, `preferences.json` | Resultado de cada travessura e preferências aprendidas |
| `conditioning.json` | O que ele aprendeu a antecipar |
| `drives.json` | Energia, estimulação e carência |
| `protest.json`, `sad_protest.json` | Insatisfação e tristeza |
| `castigo.json` | Fugas do cantinho, rancor e receio |
| `.migrado` | Só existe se a memória veio da versão antiga: quando migrou e o hash de cada arquivo |

Quem usou uma versão antiga (arquivos soltos em `memory/`) tem a memória migrada sozinha na primeira
abertura. Os originais não são apagados: ficam em `memory/legado/<pet>/`. Se a migração não puder ser
concluída (por exemplo, um arquivo já existe com outro conteúdo), nada é sobrescrito, ele continua usando
os arquivos antigos e avisa no ícone da bandeja.

## Como apagar

- Na tela de configurações, **Apagar histórico** apaga a rotina (`timeline.csv`), inclusive o minuto que
  ainda estava na memória.
- **Apagar todos os dados do Pestinha** apaga a pasta `memory/` inteira, com a memória de todos os personagens (pede confirmação e fecha o programa).
- Você também pode apagar a pasta `memory/` manualmente, com o programa fechado.

## Controle

- Cada permissão pode ser desligada na tela de configurações; desligar uma permissão também recolhe o que
  já estava na tela.
- O atalho **Ctrl + Alt + Shift + B** desliga tudo na hora, e ele continua desligado até você religar.
