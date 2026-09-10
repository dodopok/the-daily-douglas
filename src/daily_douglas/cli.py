import argparse
import json
from pathlib import Path
import sys

from .emailing import prepare_email
from .model import EditionError, load_config, load_edition
from .printing import print_edition
from .render import render_edition


def main(argv=None):
    parser = argparse.ArgumentParser(description='Create a newspaper PDF from a local edition JSON file.')
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ['validate', 'render']:
        command = commands.add_parser(name)
        command.add_argument('edition', type=Path)
        command.add_argument('--config', type=Path)
        if name == 'render':
            command.add_argument('--output-dir', type=Path, default=Path('outputs'))
    command = commands.add_parser('print', help='Preview printing; add --submit --reviewed to send to CUPS.')
    command.add_argument('manifest', type=Path)
    command.add_argument('--config', type=Path)
    command.add_argument('--printer')
    command.add_argument('--mode', choices=['simplex', 'duplex'])
    command.add_argument('--submit', action='store_true')
    command.add_argument('--reviewed', action='store_true')
    command.add_argument('--state-dir', type=Path, default=Path('state'))
    command = commands.add_parser('email', help='Prepare a Gmail delivery request for the Codex connection.')
    command.add_argument('manifest', type=Path)
    command.add_argument('--config', type=Path)
    command.add_argument('--to', required=True, help='Recipient email address or comma-separated addresses.')
    command.add_argument('--subject')
    command.add_argument('--body')
    command.add_argument('--request', type=Path, help='Optional path for the JSON request descriptor.')
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        if args.command in ['validate', 'render']:
            edition = load_edition(args.edition)
            if args.command == 'validate':
                result = {'status': 'valid', 'date': edition['date'], 'pages': 4,
                          'note': 'Content validated; run render to check layout.'}
            else:
                manifest = render_edition(edition, config, args.output_dir, args.edition.parent)
                result = {'status': 'rendered', 'manifest': str(manifest)}
        elif args.command == 'print':
            result = print_edition(args.manifest, args.printer or config['printer'],
                                   args.mode or config['print_mode'], submit=args.submit,
                                   reviewed=args.reviewed, state_dir=args.state_dir)
        else:
            result = prepare_email(args.manifest, args.to, args.subject, args.body)
            if args.request:
                request_path = args.request.resolve()
                request_path.parent.mkdir(parents=True, exist_ok=True)
                request_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
                result['request'] = str(request_path)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (EditionError, OSError, json.JSONDecodeError) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
