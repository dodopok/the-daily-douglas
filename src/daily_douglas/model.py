"""Validate the deliberately small, provider-independent edition contract."""
from datetime import date
import json
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class EditionError(ValueError):
    pass


DEFAULT_CONFIG = {
    "name": "The Daily Douglas",
    "motto": "Um jornal para começar o dia.",
    "timezone": "America/Sao_Paulo",
    "language": "pt-BR",
    "printer": None,
    "print_mode": "simplex",
    "ready_by": "08:30",
    "prepare_at": "08:00",
    "sources": {},
}


def text(value, path, maximum=12000):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise EditionError(f"{path}: expected non-empty text, up to {maximum} characters")
    if any(ord(ch) < 32 and ch not in '\n\t' for ch in value):
        raise EditionError(f"{path}: control characters are not supported")


def obj(value, path, required, optional=()):
    if not isinstance(value, dict):
        raise EditionError(f"{path}: expected an object")
    missing = set(required) - value.keys()
    extra = value.keys() - set(required) - set(optional)
    if missing or extra:
        raise EditionError(f"{path}: missing {sorted(missing)}, unknown {sorted(extra)}")


def validate_edition(data):
    obj(data, 'edition', ['schema_version', 'date', 'issue', 'is_demo', 'pages'])
    if type(data['schema_version']) is not int or data['schema_version'] != 1:
        raise EditionError('schema_version must be 1')
    try:
        parsed = date.fromisoformat(data['date'])
        if parsed.isoformat() != data['date']:
            raise ValueError()
    except (ValueError, TypeError):
        raise EditionError('date must use YYYY-MM-DD') from None
    text(data['issue'], 'issue', 20)
    if type(data['is_demo']) is not bool:
        raise EditionError('is_demo must be true or false')
    if not isinstance(data['pages'], list) or len(data['pages']) != 4:
        raise EditionError('pages must contain exactly four pages in reading order')
    for i, page in enumerate(data['pages']):
        at = f'pages[{i}]'
        obj(page, at, ['section', 'headline', 'intro', 'articles'], ['illustration', 'comic'])
        for key, limit in [('section', 40), ('headline', 120), ('intro', 400)]:
            text(page[key], f'{at}.{key}', limit)
        if page.get('illustration') not in (None, 'morning'):
            raise EditionError(f'{at}.illustration must be morning or omitted')
        if page.get('illustration') and i != 0:
            raise EditionError('The morning illustration is available on the cover only')
        if not isinstance(page['articles'], list) or not 1 <= len(page['articles']) <= 10:
            raise EditionError(f'{at}.articles: expected one to ten articles')
        for j, article in enumerate(page['articles']):
            a = f'{at}.articles[{j}]'
            obj(article, a, ['title', 'paragraphs'], ['items', 'source', 'sources'])
            text(article['title'], f'{a}.title', 100)
            paragraphs = article['paragraphs']
            if not isinstance(paragraphs, list) or len(paragraphs) > 20:
                raise EditionError(f'{a}.paragraphs: expected a list of up to 20 paragraphs')
            for paragraph in paragraphs:
                text(paragraph, f'{a}.paragraphs')
            items = article.get('items', [])
            if not isinstance(items, list) or len(items) > 10:
                raise EditionError(f'{a}.items: expected up to ten checklist items')
            for item in items:
                text(item, f'{a}.items', 300)
            if not paragraphs and not items:
                raise EditionError(f'{a}: provide paragraphs or checklist items')
            if 'source' in article and 'sources' in article:
                raise EditionError(f'{a}: use source or sources, not both')
            source_entries = [article['source']] if 'source' in article else article.get('sources', [])
            if not isinstance(source_entries, list) or ('sources' in article and not 1 <= len(source_entries) <= 4):
                raise EditionError(f'{a}.sources: expected up to four references')
            for source_index, source in enumerate(source_entries):
                source_path = f'{a}.source' if 'source' in article else f'{a}.sources[{source_index}]'
                obj(source, source_path, ['label', 'url'])
                text(source['label'], f'{source_path}.label', 100)
                text(source['url'], f'{source_path}.url', 2000)
                try:
                    url = urlsplit(source['url'])
                except ValueError:
                    raise EditionError(f'{source_path}.url: invalid URL') from None
                if url.scheme not in ('https', 'http') or not url.netloc or url.username or url.password:
                    raise EditionError(f'{source_path}.url: expected an HTTP(S) URL without credentials')
        if 'comic' in page:
            if i != 3:
                raise EditionError('comic is supported on the fourth page only')
            comic = page['comic']
            obj(comic, f'{at}.comic', ['title', 'panels'], ['image'])
            text(comic['title'], f'{at}.comic.title', 80)
            if not isinstance(comic['panels'], list) or len(comic['panels']) != 3:
                raise EditionError('comic.panels must contain exactly three captions')
            for caption in comic['panels']:
                text(caption, 'comic.panels', 150)
            if 'image' in comic:
                text(comic['image'], 'comic.image', 300)
    return data


def load_edition(path):
    return validate_edition(json.loads(Path(path).read_text(encoding='utf-8')))


def load_config(path=None):
    result = DEFAULT_CONFIG.copy()
    if path:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        obj(data, 'config', [], DEFAULT_CONFIG.keys())
        result.update(data)
    text(result['name'], 'config.name', 60)
    text(result['motto'], 'config.motto', 100)
    text(result['language'], 'config.language', 20)
    if result['print_mode'] not in ('simplex', 'duplex'):
        raise EditionError('config.print_mode must be simplex or duplex')
    try:
        ZoneInfo(result['timezone'])
    except (ZoneInfoNotFoundError, TypeError, ValueError):
        raise EditionError('config.timezone must be an IANA timezone') from None
    if not isinstance(result['sources'], dict):
        raise EditionError('config.sources must be an object')
    for key in ['prepare_at', 'ready_by']:
        value = result[key]
        if not isinstance(value, str) or len(value) != 5:
            raise EditionError(f'config.{key} must use HH:MM')
        try:
            hour, minute = [int(x) for x in value.split(':')]
            if not 0 <= hour <= 23 or not 0 <= minute <= 59:
                raise ValueError()
        except ValueError:
            raise EditionError(f'config.{key} must use HH:MM') from None
    return result
