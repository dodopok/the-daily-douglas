"""Prepare a Gmail delivery request without sending mail from the local package."""
from datetime import date
import hashlib
import json
from pathlib import Path
import re

from pypdf import PdfReader

from .model import EditionError
from .render import format_date_pt_br


class EmailError(EditionError):
    pass


EMAIL_ADDRESS = re.compile(r'^[^@\s,]+@[^@\s,]+\.[^@\s,]+$')


def _load_manifest(manifest_path):
    manifest_path = Path(manifest_path).resolve()
    try:
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        if date.fromisoformat(manifest['date']).isoformat() != manifest['date']:
            raise ValueError()
        if type(manifest['is_demo']) is not bool:
            raise ValueError()
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        raise EmailError('Invalid edition manifest') from None
    return manifest_path, manifest


def _verified_pdf(manifest_path, manifest, kind, expected_pages):
    try:
        relative = Path(manifest['files'][kind]['path'])
        expected = manifest['files'][kind]['sha256']
    except (KeyError, TypeError):
        raise EmailError(f'Manifest has no {kind} PDF') from None
    pdf = (manifest_path.parent / relative).resolve()
    if relative.is_absolute() or not pdf.is_relative_to(manifest_path.parent) or not pdf.is_file():
        raise EmailError(f'The {kind} PDF must be inside the manifest directory')
    if hashlib.sha256(pdf.read_bytes()).hexdigest() != expected:
        raise EmailError('A PDF changed after rendering. Generate and review it again.')
    if len(PdfReader(pdf).pages) != expected_pages:
        raise EmailError(f'Expected {expected_pages} pages in the {kind} PDF')
    return pdf


def prepare_email(manifest_path, recipients, subject=None, body=None):
    """Return a descriptor the Codex Gmail connection can turn into a draft/send."""
    if not isinstance(recipients, str) or not recipients.strip():
        raise EmailError('Provide at least one recipient email address')
    addresses = [address.strip() for address in recipients.split(',') if address.strip()]
    if not addresses or any(not EMAIL_ADDRESS.fullmatch(address) for address in addresses):
        raise EmailError('Recipients must be email addresses separated by commas')
    manifest_path, manifest = _load_manifest(manifest_path)
    reading = _verified_pdf(manifest_path, manifest, 'reading', 4)
    print_pdf = _verified_pdf(manifest_path, manifest, 'print', 2)
    display_date = manifest.get('display_date') or format_date_pt_br(manifest['date'])
    subject = subject.strip() if isinstance(subject, str) and subject.strip() else f'{manifest.get("name", "The Daily Douglas")} - {display_date}'
    body = body.strip() if isinstance(body, str) and body.strip() else (
        f'Segue a edição de {display_date} do {manifest.get("name", "The Daily Douglas")}.\n\n'
        'Os dois PDFs estão anexados: leitura e impressão A4.'
    )
    attachments = [
        {'path': str(reading), 'filename': reading.name, 'mime_type': 'application/pdf',
         'sha256': hashlib.sha256(reading.read_bytes()).hexdigest()},
        {'path': str(print_pdf), 'filename': print_pdf.name, 'mime_type': 'application/pdf',
         'sha256': hashlib.sha256(print_pdf.read_bytes()).hexdigest()},
    ]
    return {
        'status': 'ready_for_gmail',
        'to': ', '.join(addresses),
        'subject': subject,
        'body': body,
        'attachments': attachments,
        'manifest': str(manifest_path),
        'note': 'The local package does not send mail; use the authenticated Codex Gmail connection to create a draft or send this request.',
    }
