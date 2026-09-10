# Conexões e rotina diária

O projeto separa duas partes: o assistente coleta e escreve; o gerador local
diagrama e prepara a impressão. Cada instalação usa suas próprias contas.

| Fonte | Como alimentar o jornal |
|---|---|
| Gmail | Conecte o Gmail ao assistente e escolha conta, marcadores e critérios de importância. Para entregar o jornal, o Codex pode criar um rascunho ou enviar os PDFs pela conexão autenticada quando você escolher essa opção. |
| Todoist | Conecte o app ou MCP oficial; selecione tarefas com prazo e prioridades. |
| Google Agenda | Conecte a conta desejada e identifique o calendário. Uma conta pessoal não dá acesso automático à corporativa. |
| Estêvão | Conecte o [Estêvão MCP](https://estevao.caminhoanglicano.com.br/mcp) e escolha livro, ofício e tradução. A disponibilidade depende da conta e do livro. |
| Hacker News | Consulte a [API oficial](https://github.com/HackerNews/API) ou as ferramentas de navegação do assistente. |
| TabNews | Consulte os conteúdos públicos no [endpoint da API](https://www.tabnews.com.br/api/v1/contents) e, quando necessário, abra a [página do projeto](https://github.com/filipedeschamps/tabnews.com.br) para conferir o contexto. |
| Reddit | Use um acesso autorizado disponível. A [API exige aprovação](https://support.reddithelp.com/hc/en-us/articles/14945211791892-Developer-Platform-Accessing-Reddit-Data); não presuma que um endpoint público será sempre acessível. |

Nenhum desses adaptadores é embutido no pacote Python 0.1.0. A skill usa as
ferramentas que o assistente tiver disponíveis; também é possível escrever um
adaptador próprio que produza o contrato de `docs/content.md`.

## Preparação inicial

1. Instale o projeto e confira a demonstração.
2. Crie `config.local.json`, escolha fontes e conecte suas contas ao assistente.
3. Peça uma primeira edição real, usando `$daily-newspaper`.
4. Revise os PDFs e imprima uma prova. Escolha o nome da fila e simplex/duplex.
5. Configure a tarefa recorrente no seu aplicativo, com o projeto acessível.

Exemplo de pedido ao aplicativo:

> Todos os dias, comece às 8h e prepare o jornal até 8h30 no meu fuso, usando
> a skill daily-newspaper deste projeto e config.local.json. Gere e confira os
> PDFs. Depois envie uma cópia à impressora configurada. Não repita a impressão
> de uma edição já enviada. Entregue o PDF e o resultado real da impressão.

O aplicativo, as permissões e o ambiente determinam se a tarefa poderá executar
sem intervenção. Teste uma edição completa antes de depender do horário.
Para uma rotina local, mantenha o computador acordado e o aplicativo aberto.
Veja [tarefas agendadas](https://learn.chatgpt.com/docs/automations) e
[skills no projeto](https://learn.chatgpt.com/docs/build-skills).

## Regras editoriais sugeridas

- Use a data civil do leitor para a liturgia e os compromissos.
- Liste as fontes indisponíveis; não invente dados para preencher espaços.
- Reduza duplicação entre edições consultando o último JSON local.
- Resuma e-mails como remetente, assunto, ação esperada e prazo.
- Use as ferramentas de contas para leitura, salvo autorização para outra ação.
- Identifique opiniões, horários das notícias e traduções relevantes.
- Use textos litúrgicos da fonte; identifique o ofício ou celebração.
- Mantenha o nome do livro como configuração, sem fixá-lo no gerador.
- Gere humor original ou use material que você possa reproduzir.

## Nuvem e GitHub Actions

O workflow incluído no GitHub apenas executa testes com o exemplo. Ele não gera
sua edição privada nem imprime. Uma tarefa na nuvem não alcança automaticamente
uma impressora da rede da sua casa: seria necessário um agente local ou outro
canal de impressão configurado. Conexões do aplicativo também não se tornam
credenciais de um processo Python ou de um runner do GitHub.

## Se algo falhar

Preserve o PDF e registre a fonte ausente. Uma falha opcional não precisa impedir
o restante do jornal. Se a seção for essencial para você, configure a rotina para
aguardar a correção em vez de imprimir uma edição incompleta.

Se o envio à impressora terminar com estado incerto, confira a fila e o registro
em `state/`. O projeto mantém a trava porque o papel pode ter sido enviado antes
da falha da conexão. Repetir sem conferir pode imprimir duas cópias.

O comando solicita A4, escala real, preto e branco e uma cópia. A impressora e
seu driver precisam aceitar as opções. Confira também a [documentação do CUPS](https://www.cups.org/doc/options.html).
