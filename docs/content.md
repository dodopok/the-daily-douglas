# Contrato de uma edição

`examples/edition.json` é um exemplo completo validado pelo gerador. Todo conteúdo
é texto simples: `<b>` e outros trechos parecidos com HTML são impressos literalmente.

## Edição

| Campo | Conteúdo |
|---|---|
| `schema_version` | `1` |
| `date` | Data civil `YYYY-MM-DD`, no fuso do leitor |
| `issue` | Identificador curto da edição, como `001` |
| `is_demo` | `true` para exemplos; `false` somente para uma edição real |
| `pages` | Exatamente quatro objetos, em ordem de leitura |

## Página

Cada página tem `section`, `headline`, `intro` e `articles`.
O título pode conter `\n` para uma quebra de linha intencional.
Na capa, `illustration: "morning"` inclui a ilustração vetorial de jornal e café;
omita o campo para ganhar espaço para texto.

Cada artigo tem um `title` e uma lista de `paragraphs`. Pode incluir uma lista de
`items` para quadradinhos de tarefas e `source: {"label": "Fonte", "url": "https://..."}`
para um link clicável no PDF. Quando o texto cruza mais de uma página ou serviço,
use `sources` com até quatro objetos no mesmo formato; `source` continua aceito
para manter edições antigas compatíveis. Artigos precisam de pelo menos um
parágrafo ou item.

O gerador distribui o conteúdo em duas colunas, seguindo a ordem dos artigos. Um
parágrafo longo pode continuar na coluna seguinte, e o título é mantido junto do
início do artigo sempre que houver espaço. O corpo usa uma composição compacta
de 8,6 pt para caber mais informação em meia A4; as fontes ficam menores e
clicáveis, com o domínio visível. Se a página ficar cheia, `render` falha,
preservando os PDFs anteriores. Revise ou encurte os artigos; o gerador não
elimina conteúdo nem reduz a fonte abaixo dessa composição.

Como ponto de partida, use cerca de 100-150 palavras na capa ilustrada, 200-300
em cada página interna e 100-150 na página com a tirinha. São estimativas; títulos,
listas e palavras longas alteram o espaço. `validate` confere a estrutura; `render`
confere o encaixe. Depois, confira visualmente as quatro páginas.

## Tirinha

Somente a quarta página aceita `comic`:

```json
{
  "title": "A vida em três quadros",
  "panels": ["Primeira fala.", "Segunda fala.", "Conclusão."]
}
```

Esse formato usa o desenho recorrente de uma pessoa e uma impressora. As falas
devem ser breves e combinar com a cena. Para arte própria, acrescente
`"image": "images/tirinha.png"`; a imagem substitui a tira inteira. Os três textos
continuam no arquivo como descrição do conteúdo. Use imagem larga, em preto e
branco, com texto legível. O caminho deve ficar dentro do diretório do JSON.

## Resultado

- `DATA-reading.pdf`: quatro páginas de meia A4 (148,5 × 210 mm).
- `DATA-a4.pdf`: duas páginas A4 em paisagem, já montadas para dobrar.
- `DATA-manifest.json`: data ISO, data visível em português, nomes de arquivos e
  hashes usados na impressão ou no pedido de e-mail.

Edições de demonstração têm `-demo` no nome. Os PDFs não têm um limite de acesso;
guarde as edições pessoais em um diretório privado e fora do Git.

Caracteres sem glifo nas fontes, como alguns emojis, produzem erro explícito.
Substitua-os por palavras ou use uma imagem. A interface e os exemplos estão em
português; o conteúdo pode ser escrito em outros idiomas cobertos pelas fontes.
