# The Daily Douglas

**Seu jornal pessoal. Quatro páginas. Uma pausa antes do primeiro clique.**

Um gerador local de jornais em PDF, com visual clássico, nome personalizável,
duas colunas, tirinha e montagem pronta para dobrar. Inspirado no
[The Morning Newspaper, de Karen X. Cheng](https://newspaper.karenx.com/).

![Capa de demonstração](docs/preview.png)

## O que funciona nesta versão

- Geração de quatro páginas em meia folha A4, em ordem de leitura.
- PDF de impressão com duas páginas A4 em paisagem: `[4 | 1]` e `[2 | 3]`.
- Duas folhas impressas de um lado, ou uma folha frente e verso.
- Conteúdo fornecido por um arquivo JSON: seções, artigos, referências e listas.
- Composição interna mais compacta (corpo de 8,6 pt) para trazer mais contexto,
  com títulos preservados junto do texto e até quatro referências clicáveis por artigo.
- Tirinha vetorial com legendas personalizáveis, ou imagem local própria.
- Fontes abertas incluídas; não depende de fontes instaladas no Mac.
- Detecção de excesso de texto: a edição falha com uma mensagem em vez de cortar conteúdo.
- Impressão opcional pelo CUPS, com prévia e registro para evitar envios duplicados.
- Entrega por e-mail preparada para a conexão Gmail do Codex, com os dois PDFs anexados.
- Uma skill do Codex para buscar conteúdo nas conexões do próprio usuário.

**O pacote Python não acessa suas contas nem escreve notícias por conta própria.**
Ele transforma conteúdo em PDF. A coleta e a redação ficam com o assistente e suas
ferramentas conectadas, ou com uma integração que você escreva para produzir o JSON.
Clonar este projeto não copia contas conectadas, autorizações ou tarefas agendadas.

## Comece aqui, sem conhecimento técnico

Você pode testar o jornal de exemplo sem conectar Gmail, calendário ou qualquer
outra conta. O programa roda no seu próprio computador; os comandos abaixo são
digitados no **Terminal** (macOS/Linux) ou no **PowerShell** (Windows).

### 1. Instale os dois programas necessários

Instale o [Python 3.11 ou mais recente](https://www.python.org/downloads/).
Para baixar o projeto pelo comando `git clone`, instale também o [Git](https://git-scm.com/downloads).
Se preferir, no GitHub use **Code > Download ZIP**, descompacte o arquivo e pule
o primeiro comando abaixo.

### 2. Baixe e instale o jornal

No macOS ou Linux:

```sh
git clone https://github.com/dodopok/the-daily-douglas.git
cd the-daily-douglas
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
```

No Windows, abra o PowerShell na pasta em que quer guardar o projeto:

```powershell
git clone https://github.com/dodopok/the-daily-douglas.git
cd the-daily-douglas
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install .
```

O ambiente virtual (`.venv`) deixa as dependências deste jornal separadas dos
outros programas do computador. Sempre que abrir um novo Terminal para trabalhar
no projeto, entre na pasta e ative-o novamente (`source .venv/bin/activate` no
macOS/Linux ou `.venv\Scripts\Activate.ps1` no Windows).

### 3. Gere o exemplo

```sh
daily-douglas validate examples/edition.json
daily-douglas render examples/edition.json --output-dir outputs/demo
```

Se aparecer `status: valid` e depois `status: rendered`, deu certo. Abra estes
arquivos na pasta `outputs/demo`:

- `2026-01-01-demo-reading.pdf`: quatro páginas para ler na tela.
- `2026-01-01-demo-a4.pdf`: duas páginas A4 já montadas para imprimir e dobrar.
- `2026-01-01-demo-manifest.json`: ficha técnica usada pelos comandos de entrega.

O exemplo é explicitamente demonstrativo, não uma edição factual daquela data.

## Crie seu jornal pessoal

Copie `config.example.json` para `config.local.json` e troque apenas o que quiser:
nome do jornal, lema, fuso horário e preferências de impressão. Esse arquivo é
local e fica fora do Git; não coloque senhas nele.

```sh
cp config.example.json config.local.json
daily-douglas render examples/edition.json --config config.local.json
```

O conteúdo do jornal fica em um arquivo JSON. Você pode ter um jornal de
tecnologia, um boletim de família, notícias locais ou qualquer combinação que
caiba nas quatro páginas. A seção litúrgica é opcional. O formato está explicado
em [docs/content.md](docs/content.md), com um exemplo completo em
`examples/edition.json`.

O gerador não busca notícias sozinho. Para uma edição diária, alguém precisa
fornecer o JSON: você pode escrever esse arquivo ou pedir ao Codex para coletar
as fontes e montá-lo. O programa valida as referências, diagrama o texto e
recusa uma edição cheia demais em vez de esconder conteúdo.

Os campos `prepare_at` e `ready_by` documentam sua preferência. **Eles não criam um
agendamento**: configure a rotina no seu aplicativo ou agendador.

Veja o [contrato do conteúdo](docs/content.md) e as
[conexões e automação](docs/connections.md).

## Forma mais simples: usar com o Codex

Se você não quer editar JSON, abra este repositório como um projeto no Codex e
escreva algo parecido com:

```text
Use $daily-newspaper para montar a edição de hoje, seguindo config.local.json.
Leia as fontes que estão conectadas ao Codex, gere os PDFs e me mostre o resultado.
Depois, pergunte se devo imprimir ou enviar por e-mail.
```

Para receber por e-mail, conecte o Gmail ao Codex, informe o endereço do destinatário
e peça explicitamente **criar um rascunho** ou **enviar**. Para imprimir, informe a
impressora e peça explicitamente a impressão. A conexão do Gmail pede as
autorizações da sua conta; elas não são copiadas para este repositório. Consulte a
[documentação oficial de plugins do Codex](https://learn.chatgpt.com/docs/plugins)
se o Gmail ainda não aparecer entre as conexões.

A skill que orienta esse fluxo está em `.agents/skills/daily-newspaper/SKILL.md`.
Ela coleta e redige usando as fontes disponíveis, mas não inventa acesso a contas
que você não conectou.

## Escolha: imprimir ou enviar por e-mail

Depois de gerar e revisar os PDFs, escolha um dos caminhos abaixo. O arquivo
`*-reading.pdf` é para leitura na tela; o `*-a4.pdf` é o arquivo já montado para
impressão.

### Imprimir

O PDF A4 já contém duas páginas do jornal por folha. No diálogo de impressão,
use **A4, paisagem, tamanho real (100%), uma página do PDF por folha**.

Para apenas conferir o que seria enviado à impressora:

```sh
daily-douglas print outputs/demo/2026-01-01-demo-manifest.json --printer NOME_DA_FILA
```

No macOS/Linux, descubra o nome da fila com `lpstat -p -d`. Para enviar de fato,
revise o PDF e acrescente `--submit --reviewed`:

```sh
daily-douglas print outputs/demo/2026-01-01-demo-manifest.json \
  --printer NOME_DA_FILA --submit --reviewed
```

Com uma impressora duplex, acrescente `--mode duplex`. No Windows, abra o PDF A4
no aplicativo de impressão do sistema. Para duas folhas, use impressão simples;
para uma folha frente e verso, use a borda curta e faça uma prova antes.

### Enviar por e-mail

No Codex, a maneira mais fácil é pedir no chat: “envie a edição por Gmail para
`voce@example.com`” e escolher entre rascunho e envio quando o Codex mostrar a
mensagem.

Quem usa o Terminal pode preparar o pedido assim:

```sh
daily-douglas email outputs/demo/2026-01-01-demo-manifest.json \
  --to voce@example.com --request outputs/demo/email-request.json
```

Esse comando confere os hashes e cria um pedido com os dois PDFs anexados. Ele não
guarda sua senha, não acessa o Gmail e não envia sozinho. No Codex, entregue esse
pedido (`outputs/demo/email-request.json`) à conexão Gmail autenticada para criar o
rascunho ou enviar a mensagem quando você tiver escolhido essa ação.

Por exemplo, no chat do Codex: “leia `outputs/demo/email-request.json`, crie um
rascunho no Gmail para mim e mostre a mensagem antes de enviar”.

Se um comando mostrar `Error:`, copie a mensagem inteira. Erros de conteúdo ou de
espaço significam que é preciso corrigir o JSON; o gerador não corta texto para
fazer o arquivo caber.

## Desenvolvimento

```sh
python -m pip install -e .
python -m unittest discover -s tests -v
```

O fluxo de testes do GitHub usa apenas conteúdo de demonstração. Os testes de
impressão simulam o CUPS e nunca enviam papel à impressora.

## Dados pessoais e publicação

Versione código, exemplos e documentação. Guarde conteúdo real em `private/`,
`work/` ou `outputs/`, e registros em `state/`; esses diretórios são ignorados.
Credenciais pertencem ao aplicativo conectado ou ao armazenamento privado de sua
integração. O projeto não precisa de uma chave de API para executar a demonstração.

As fontes externas e os textos que você inserir mantêm seus próprios termos e
licenças. A licença do código não concede direitos sobre artigos, traduções
bíblicas, e-mails ou conteúdo de terceiros. Os exemplos incluídos são originais.

## Licença e créditos

Código e exemplos: [MIT](LICENSE). Fontes: SIL Open Font License, com os avisos
originais incluídos; veja [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
O projeto tem identidade própria e não é afiliado ao The New York Times.

Versão inicial: gerador e fluxo com assistente. Adaptadores autônomos de contas,
um painel de configuração e um serviço de agendamento próprio ficam para versões futuras.
