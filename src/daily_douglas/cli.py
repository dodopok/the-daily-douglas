import argparse
import json
from pathlib import Path
import sys

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
        else:
            result = print_edition(args.manifest, args.printer or config['printer'],
                                   args.mode or config['print_mode'], submit=args.submit,
                                   reviewed=args.reviewed, state_dir=args.state_dir)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (EditionError, OSError, json.JSONDecodeError) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
