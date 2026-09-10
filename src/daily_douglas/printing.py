"""Opt-in CUPS submission with a durable record before any side effect."""
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from pypdf import PdfReader
from reportlab.lib.pagesizes import A4
from .model import EditionError


class PrintError(EditionError):
    pass


def prepare(manifest_path, printer, mode='simplex'):
    if not isinstance(printer, str) or not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,126}', printer):
        raise PrintError('Provide a valid CUPS printer queue name')
    if mode not in ('simplex', 'duplex'):
        raise PrintError('Print mode must be simplex or duplex')
    manifest_path = Path(manifest_path).resolve()
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    try:
        if date.fromisoformat(manifest['date']).isoformat() != manifest['date']:
            raise ValueError()
        if type(manifest['is_demo']) is not bool:
            raise ValueError()
        relative = Path(manifest['files']['print']['path'])
        expected = manifest['files']['print']['sha256']
    except (KeyError, TypeError, ValueError):
        raise PrintError('Invalid edition manifest') from None
    pdf = (manifest_path.parent / relative).resolve()
    if relative.is_absolute() or not pdf.is_relative_to(manifest_path.parent) or not pdf.is_file():
        raise PrintError('The print PDF must be inside the manifest directory')
    if hashlib.sha256(pdf.read_bytes()).hexdigest() != expected:
        raise PrintError('The PDF changed after rendering. Generate and review it again.')
    pages = PdfReader(pdf).pages
    if len(pages) != 2 or any(abs(float(p.mediabox.width)-A4[1]) > 1 or abs(float(p.mediabox.height)-A4[0]) > 1 for p in pages):
        raise PrintError('Expected two A4 landscape pages, already imposed for folding')
    sides = 'one-sided' if mode == 'simplex' else 'two-sided-short-edge'
    command = ['lp', '-d', printer, '-n', '1', '-o', 'media=A4', '-o', f'sides={sides}',
               '-o', 'number-up=1', '-o', 'print-color-mode=monochrome',
               '-o', 'print-scaling=none', '-o', 'job-sheets=none', str(pdf)]
    return manifest, command


def print_edition(manifest_path, printer, mode='simplex', *, submit=False,
                  reviewed=False, state_dir=Path('state')):
    manifest, command = prepare(manifest_path, printer, mode)
    if not submit:
        return {'status': 'dry_run', 'command': command, 'sheets': 2 if mode == 'simplex' else 1}
    if not reviewed:
        raise PrintError('Render and visually review the PDFs, then add --reviewed to submit.')
    if shutil.which('lp') is None:
        raise PrintError('CUPS lp is unavailable. Print the A4 PDF from your PDF application.')
    state_dir = Path(state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    key = f'{manifest.get("name", "newspaper")}:{manifest["date"]}:{manifest["is_demo"]}'
    digest = hashlib.sha256(key.encode()).hexdigest()[:16]
    record_path = state_dir / f'{manifest["date"]}-{digest}.json'
    record = {'status': 'submitting', 'date': manifest['date'], 'printer': printer,
              'manifest': str(Path(manifest_path).resolve()),
              'started_at': datetime.now(timezone.utc).isoformat()}
    try:
        # An interrupted/uncertain attempt blocks retries, including concurrent runs.
        fd = os.open(record_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise PrintError(f'An attempt already exists for this edition. Inspect its record and the printer queue: {record_path}') from None
    with os.fdopen(fd, 'w', encoding='utf-8') as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
        stream.flush(); os.fsync(stream.fileno())
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=30,
                                env={**os.environ, 'LC_ALL': 'C'})
        record['response'] = (result.stdout + result.stderr).strip()
        if result.returncode:
            record['status'] = 'uncertain'
            record['returncode'] = result.returncode
        else:
            record['status'] = 'submitted'
            match = re.search(r'request id is (\S+)', result.stdout)
            record['job_id'] = match.group(1) if match else None
    except (subprocess.TimeoutExpired, OSError) as error:
        record['status'] = 'uncertain'
        record['error'] = type(error).__name__
    temporary = record_path.with_suffix('.tmp')
    with temporary.open('w', encoding='utf-8') as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
        stream.flush(); os.fsync(stream.fileno())
    temporary.replace(record_path)
    if record['status'] != 'submitted':
        raise PrintError(f'Printing is unconfirmed. Do not resubmit before checking the queue and {record_path}')
    # CUPS acceptance is not evidence that paper physically came out.
    return record
