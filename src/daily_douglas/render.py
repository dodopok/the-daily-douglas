"""Portable composition with overflow detection and booklet imposition."""
import hashlib
from datetime import date
from html import escape
import json
import math
from pathlib import Path
import tempfile
from urllib.parse import urlsplit

from pypdf import PdfReader, PdfWriter, Transformation
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph

from .model import EditionError, validate_edition

W, H = A4[1] / 2, A4[0]
M, GAP = 27, 16
WIDTH = W - M * 2
COL = (WIDTH - GAP) / 2
FONT_DIR = Path(__file__).parent / 'assets' / 'fonts'
BODY_SIZE, BODY_LEADING = 8.6, 11.2
ARTICLE_HEADING_SIZE, ARTICLE_HEADING_LEADING = 15.5, 17.4
SOURCE_SIZE, SOURCE_LEADING = 6.8, 8.4
PT_BR_MONTHS = (
    'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
    'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro',
)


class LayoutError(EditionError):
    pass


def format_date_pt_br(value):
    """Format an ISO civil date for the newspaper's Brazilian Portuguese UI."""
    parsed = date.fromisoformat(value)
    return f'{parsed.day} de {PT_BR_MONTHS[parsed.month - 1]} de {parsed.year}'


def fonts():
    for name, file in [('DD-Body', 'NotoSerif-Regular.ttf'), ('DD-Bold', 'NotoSerif-Bold.ttf'),
                       ('DD-Italic', 'NotoSerif-Italic.ttf'), ('DD-Name', 'UnifrakturMaguntia-Book.ttf')]:
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(FONT_DIR / file)))


def safe(text):
    # Content is plain text, never ReportLab markup supplied by a feed or model.
    supported = pdfmetrics.getFont('DD-Body').face.charToGlyph
    unsupported = {ch for ch in text if ord(ch) not in supported and not ch.isspace()}
    if unsupported:
        raise EditionError('Unsupported characters; replace emoji or use plain text: ' + repr(''.join(sorted(unsupported))))
    return escape(text).replace('\n', '<br/>')


def paragraph(text, size=BODY_SIZE, leading=BODY_LEADING, font='DD-Body', align=TA_JUSTIFY, markup=False):
    return Paragraph(text if markup else safe(text), ParagraphStyle(
        'newspaper', fontName=font, fontSize=size, leading=leading,
        alignment=align, textColor='#111111', splitLongWords=True))


def rule(c, x1, y, x2, weight=.45, gray=0):
    c.saveState(); c.setLineWidth(weight); c.setStrokeGray(gray)
    c.line(x1, y, x2, y); c.restoreState()


def label(c, text, x, y, size=7, font='DD-Bold', right=False, center=False, max_width=None):
    safe(text)
    if max_width:
        while pdfmetrics.stringWidth(text, font, size) > max_width and size > 5:
            size -= .25
        if pdfmetrics.stringWidth(text, font, size) > max_width:
            raise LayoutError('Shorten a running header or label')
    c.setFillGray(0); c.setFont(font, size)
    if right: c.drawRightString(x, y, text)
    elif center: c.drawCentredString(x, y, text)
    else: c.drawString(x, y, text)


def draw_paragraph(c, p, x, y, width):
    _, height = p.wrap(width, H)
    c.setFillGray(0)
    p.drawOn(c, x, y - height)
    return y - height


def morning(c, y, name):
    """Original vector artwork. No downloaded images or proprietary fonts."""
    c.saveState(); c.translate(M + 24, y - 103); c.scale(.8, .8)
    c.setLineWidth(.65); c.setStrokeGray(0)
    c.saveState(); c.translate(10, 8); c.rotate(6)
    c.rect(0, 0, 170, 98)
    label(c, name, 85, 77, 16, 'DD-Name', center=True, max_width=150)
    rule(c, 9, 70, 161, .8)
    for col in range(3):
        for row in range(11):
            rule(c, 10 + col * 51, 60 - row * 4.6, 51 + col * 51 - (8 if row == 10 else 0), .35)
    c.restoreState()
    for i in range(13):
        angle = math.pi * i / 12
        c.line(260 + 29 * math.cos(angle), 26 + 29 * math.sin(angle),
               260 + 44 * math.cos(angle), 26 + 44 * math.sin(angle))
    c.arc(239, 5, 281, 47, 0, 180)
    c.ellipse(236, 2, 324, 17)
    c.setFillGray(1); c.roundRect(253, 10, 51, 47, 8, fill=1)
    c.ellipse(253, 50, 304, 64, fill=1)
    c.ellipse(258, 54, 299, 60)
    c.bezier(304, 48, 331, 49, 331, 19, 304, 24)
    for i in range(3):
        x = 266 + 12 * i
        c.bezier(x, 72, x - 9, 86, x + 9, 94, x, 106)
    c.restoreState()
    return y - 116


class Columns:
    def __init__(self, c, top, bottom, page_number):
        self.c, self.top, self.bottom = c, top, bottom
        self.column, self.y, self.page_number = 0, top, page_number

    @property
    def x(self):
        return M + self.column * (COL + GAP)

    def next(self):
        if self.column == 1:
            raise LayoutError(f'Page {self.page_number} is full. Shorten its articles; no text was discarded.')
        self.column, self.y = 1, self.top

    def add(self, p, inset=0, gap=6):
        while True:
            available = self.y - self.bottom
            _, height = p.wrap(COL - inset, H * 20)
            if height <= available:
                self.y = draw_paragraph(self.c, p, self.x + inset, self.y, COL - inset) - gap
                return
            parts = p.split(COL - inset, max(0, available))
            if len(parts) > 1:
                self.y = draw_paragraph(self.c, parts[0], self.x + inset, self.y, COL - inset)
                p = parts[1]
            self.next()

    def article(self, article, first=False):
        # Keep a heading with the beginning of its article when possible. A
        # whole article may be taller than the remaining space, so the body is
        # allowed to continue in the next column instead of forcing overflow.
        if not first and self.column == 0 and article_start_height(article) > self.y - self.bottom:
            self.next()
        heading = paragraph(article['title'], ARTICLE_HEADING_SIZE, ARTICLE_HEADING_LEADING, 'DD-Bold', TA_LEFT)
        _, height = heading.wrap(COL, H)
        if self.y - self.bottom < height + 38:
            self.next()
        if not first and self.y < self.top - 2:
            rule(self.c, self.x, self.y, self.x + COL, .45, .35)
            self.y -= 12
        self.add(heading, gap=8)
        for body in article['paragraphs']:
            self.add(paragraph(body), gap=8)
        for item in article.get('items', []):
            p = paragraph(item, align=TA_LEFT)
            _, height = p.wrap(COL - 14, H)
            if height > self.y - self.bottom:
                self.next()
            if height > self.y - self.bottom:
                raise LayoutError('A checklist item is too long for a column')
            self.c.setLineWidth(.55); self.c.rect(self.x, self.y - 10, 6, 6)
            self.add(p, inset=14, gap=10)
        for source in article_sources(article):
            domain = urlsplit(source['url']).netloc.removeprefix('www.')
            source_label = f'{source["label"]} / {domain}'
            text = f'<link href="{escape(source["url"], quote=True)}">{safe(source_label)}</link>'
            self.add(paragraph(text, SOURCE_SIZE, SOURCE_LEADING, 'DD-Italic', TA_LEFT, markup=True), gap=6)
        self.y -= 5


def article_sources(article):
    """Return one or more clickable references while keeping the old `source` field."""
    if 'sources' in article:
        return article['sources']
    return [article['source']] if 'source' in article else []


def article_start_height(article):
    """Height needed to place a heading and the first piece of its content."""
    _, total = paragraph(article['title'], ARTICLE_HEADING_SIZE, ARTICLE_HEADING_LEADING, 'DD-Bold', TA_LEFT).wrap(COL, H * 20)
    total += 8
    if article.get('paragraphs'):
        total += paragraph(article['paragraphs'][0]).wrap(COL, H * 20)[1] + 8
    else:
        first_item = paragraph(article['items'][0], align=TA_LEFT)
        total += first_item.wrap(COL - 14, H * 20)[1] + 10
    return total


def article_height(article):
    """Estimate a complete article to balance columns at article boundaries."""
    _, total = paragraph(article['title'], ARTICLE_HEADING_SIZE, ARTICLE_HEADING_LEADING, 'DD-Bold', TA_LEFT).wrap(COL, H * 20)
    total += 8 + 5
    for body in article['paragraphs']:
        total += paragraph(body).wrap(COL, H * 20)[1] + 8
    for item in article.get('items', []):
        total += paragraph(item, align=TA_LEFT).wrap(COL - 14, H * 20)[1] + 10
    for source in article_sources(article):
        domain = urlsplit(source['url']).netloc.removeprefix('www.')
        source_label = f'{source["label"]} / {domain}'
        total += paragraph(source_label, SOURCE_SIZE, SOURCE_LEADING, 'DD-Italic', TA_LEFT).wrap(COL, H * 20)[1] + 6
    return total


def column_break(articles, capacity):
    heights = [article_height(article) for article in articles]
    candidates = []
    for cut in range(1, len(articles)):
        left = sum(heights[:cut]) + 12 * (cut - 1)
        right = sum(heights[cut:]) + 12 * (len(articles) - cut - 1)
        if max(left, right) <= capacity:
            candidates.append((abs(left - right), cut))
    return min(candidates)[1] if candidates else None


def comic(c, data, asset_root):
    rule(c, M, 205, W - M, .8)
    label(c, data['title'].upper(), M, 191, 7, max_width=WIDTH)
    y, height = 57, 121
    if data.get('image'):
        path = (asset_root / data['image']).resolve()
        if not path.is_relative_to(asset_root.resolve()) or not path.is_file():
            raise EditionError('comic.image must be an existing file within the edition input directory')
        c.drawImage(str(path), M, y, WIDTH, height, preserveAspectRatio=True, anchor='c', mask='auto')
        return
    panel_width = (WIDTH - 14) / 3
    for i, text in enumerate(data['panels']):
        x = M + i * (panel_width + 7)
        c.setStrokeGray(0); c.setLineWidth(.6); c.rect(x, y, panel_width, height)
        p = paragraph(text, 8.2, 10.7, align=TA_CENTER)
        _, ph = p.wrap(panel_width - 12, height)
        if ph > 42:
            raise LayoutError('Shorten the comic captions to at most three lines')
        draw_paragraph(c, p, x + 6, y + height - 8, panel_width - 12)
        hx, hy = x + 26, y + 48
        c.circle(hx, hy, 11); c.circle(hx - 4, hy + 1, 3.7); c.circle(hx + 4, hy + 1, 3.7)
        c.line(hx - 1, hy + 1, hx + 1, hy + 1)
        c.arc(hx - 6, hy - 8, hx + 6, hy + 2, 200, 135)
        c.line(hx - 6, hy - 10, hx - 12, y + 14)
        c.line(hx + 6, hy - 10, hx + 12, y + 14)
        c.line(hx - 12, y + 14, hx + 12, y + 14)
        px = x + panel_width - 39
        c.roundRect(px, y + 12, 28, 21, 2)
        c.rect(px + 5, y + 28, 18, 12)
        for j in range([1, 4, 12][i]):
            rule(c, px - 3, y + 43 + j * 2.1, px + 30, .4)


def reading_pdf(edition, config, destination, asset_root):
    fonts()
    c = Canvas(str(destination), pagesize=(W, H), pageCompression=1)
    display_date = format_date_pt_br(edition['date'])
    c.setTitle(f'{config["name"]} | {display_date}')
    c.setAuthor(config['name'])
    c.setSubject('DEMO - fictional sample content' if edition['is_demo'] else 'Personal daily newspaper')
    for i, page in enumerate(edition['pages']):
        footer = 'DEMO / CONTEÚDO DE EXEMPLO' if edition['is_demo'] else display_date
        rule(c, M, 31, W - M)
        label(c, footer, M, 20, 6.2)
        label(c, f'{page["section"].upper()} / {i + 1}', W - M, 20, 6.2, right=True, max_width=WIDTH * .43)
        if i == 0:
            label(c, config['motto'].upper(), W / 2, H - 30, 6.6, center=True, max_width=WIDTH)
            label(c, config['name'], W / 2, H - 79, 39, 'DD-Name', center=True, max_width=WIDTH)
            rule(c, M, H - 90, W - M, 1.2); rule(c, M, H - 94, W - M)
            label(c, display_date, M, H - 107, 6.5, max_width=WIDTH * .5)
            label(c, f'Nº {edition["issue"]}' + (' / DEMO' if edition['is_demo'] else ''), W - M, H - 107, 6.5, right=True, max_width=WIDTH / 2)
            rule(c, M, H - 117, W - M)
            y = H - 132
        else:
            label(c, config['name'], M, H - 34, 19, 'DD-Name', max_width=WIDTH * .7)
            label(c, display_date, W - M, H - 31, 6.5, right=True, max_width=WIDTH * .5)
            rule(c, M, H - 44, W - M, 1)
            label(c, page['section'].upper(), M, H - 59, 7.2)
            y = H - 78
        size = 29 if i == 0 else 26
        head = paragraph(page['headline'], size, size * 1.1, 'DD-Bold', TA_LEFT)
        _, head_height = head.wrap(WIDTH, H)
        if head_height > 108:
            raise LayoutError(f'Page {i + 1}: shorten the main headline')
        y = draw_paragraph(c, head, M, y, WIDTH) - 10
        intro = paragraph(page['intro'], 10, 14, 'DD-Italic', TA_LEFT)
        y = draw_paragraph(c, intro, M, y, WIDTH) - 15
        if page.get('illustration'):
            y = morning(c, y, config['name'])
        rule(c, M, y, W - M, .7); y -= 16
        bottom = 218 if 'comic' in page else 49
        if y - bottom < 60:
            raise LayoutError(f'Page {i + 1}: shorten the headline or introduction')
        c.saveState(); c.setStrokeGray(.65); c.setLineWidth(.35)
        c.line(W / 2, y, W / 2, bottom); c.restoreState()
        columns = Columns(c, y, bottom, i + 1)
        split_at = column_break(page['articles'], y - bottom)
        for j, article in enumerate(page['articles']):
            if j == split_at:
                columns.next()
            columns.article(article, first=j == 0)
        if 'comic' in page:
            comic(c, page['comic'], asset_root)
        c.showPage()
    c.save()


def impose(reading, target):
    reader = PdfReader(reading)
    if len(reader.pages) != 4:
        raise EditionError('Booklet imposition requires four pages')
    writer = PdfWriter()
    for left, right in [(3, 0), (1, 2)]:
        page = writer.add_blank_page(width=A4[1], height=A4[0])
        page.merge_transformed_page(reader.pages[left], Transformation())
        page.merge_transformed_page(reader.pages[right], Transformation().translate(W, 0))
    writer.add_metadata({'/Title': 'Newspaper | A4 booklet [4|1] [2|3]'})
    with open(target, 'wb') as stream:
        writer.write(stream)


def render_edition(edition, config, output_dir, asset_root=Path('.')):
    validate_edition(edition)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = edition['date'] + ('-demo' if edition['is_demo'] else '')
    names = {'reading': stem + '-reading.pdf', 'print': stem + '-a4.pdf'}
    # No final files are replaced when composition fails.
    with tempfile.TemporaryDirectory(prefix='daily-douglas-') as temporary:
        work = Path(temporary)
        reading_pdf(edition, config, work / names['reading'], Path(asset_root))
        impose(work / names['reading'], work / names['print'])
        manifest = {'schema_version': 1, 'date': edition['date'], 'display_date': format_date_pt_br(edition['date']),
                    'is_demo': edition['is_demo'],
                    'name': config['name'], 'imposition': [[4, 1], [2, 3]], 'files': {}}
        for kind, name in names.items():
            data = (work / name).read_bytes()
            manifest['files'][kind] = {'path': name, 'sha256': hashlib.sha256(data).hexdigest()}
        for name in names.values():
            (output_dir / name).write_bytes((work / name).read_bytes())
        target = output_dir / (stem + '-manifest.json')
        target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return target
