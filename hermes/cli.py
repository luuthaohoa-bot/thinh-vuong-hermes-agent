import argparse
import json
from pathlib import Path
from .intake import intake, SidecarOCR
from .store import Store
from .export import export_review
from .model import amount, required


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(path, value):
    # Explicit local file creation. Do not silently replace an earlier review.
    with Path(path).open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)


def main(argv=None):
    p = argparse.ArgumentParser(description='Hermes local review workflow (mock website only)')
    p.add_argument('--db', default='data/hermes.sqlite')
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('demo')
    s = sub.add_parser('master'); s.add_argument('--out', required=True)
    s = sub.add_parser('intake'); s.add_argument('pdf'); s.add_argument('--out', required=True); s.add_argument('--ocr-pages')
    s = sub.add_parser('bhx'); s.add_argument('pdf'); s.add_argument('--date', required=True); s.add_argument('--out', required=True)
    s = sub.add_parser('excel'); s.add_argument('xlsx'); s.add_argument('--ledger-id', required=True); s.add_argument('--out', required=True); s.add_argument('--routes')
    s = sub.add_parser('route'); s.add_argument('id'); s.add_argument('--rules', required=True); s.add_argument('--hash', required=True)
    s = sub.add_parser('draft'); s.add_argument('json'); s.add_argument('--record', help='Select an order_ref from an intake report')
    s = sub.add_parser('show'); s.add_argument('id')
    s = sub.add_parser('revise'); s.add_argument('id'); s.add_argument('json'); s.add_argument('--hash', required=True)
    s = sub.add_parser('settle'); s.add_argument('id'); s.add_argument('prices'); s.add_argument('--hash', required=True)
    s = sub.add_parser('export'); s.add_argument('id'); s.add_argument('--out', required=True)
    s = sub.add_parser('approve'); s.add_argument('id'); s.add_argument('--hash', required=True); s.add_argument('--by', required=True)
    s = sub.add_parser('publish-mock'); s.add_argument('id')
    args = p.parse_args(argv)
    store = None
    try:
        if args.command == 'demo':
            from .demo import run
            result = run()
        elif args.command == 'intake':
            result = intake(args.pdf, SidecarOCR(read(args.ocr_pages)) if args.ocr_pages else None)
            save(args.out, result)
        elif args.command == 'excel':
            from .excel import candidates
            result = candidates(args.xlsx, args.ledger_id)
            from .routing import route
            config = read(args.routes) if args.routes else {'rules': []}
            route('validate-config', config)
            for record in result['records']:
                record['routing'] = route(record['customer'], config)
            save(args.out, result)
        elif args.command == 'bhx':
            from .bhx import candidates
            result = candidates(args.pdf, args.date)
            save(args.out, result)
        else:
            Path(args.db).parent.mkdir(parents=True, exist_ok=True)
            store = Store(args.db)
            if args.command == 'master':
                from .master import run
                result = run(store)
                save(args.out, result)
            elif args.command == 'draft':
                payload = read(args.json)
                if args.record:
                    matches = [r for r in payload.get('records', []) if r['order_ref'] == args.record]
                    if len(matches) != 1:
                        raise ValueError('Select exactly one available candidate order_ref')
                    payload = matches[0]
                result = store.create(payload)
            elif args.command == 'show':
                result = store.get(args.id)
            elif args.command == 'route':
                from .routing import route
                row = store.get(args.id)
                row['record']['routing'] = route(row['record']['customer'], read(args.rules))
                result = store.revise(args.id, row['record'], args.hash)
            elif args.command == 'revise':
                result = store.revise(args.id, read(args.json), args.hash)
            elif args.command == 'settle':
                row = store.get(args.id)
                prices = read(args.prices)
                if not prices or not isinstance(prices, dict):
                    raise ValueError('Provide a nonempty object keyed by line_id')
                known = {x['line_id'] for x in row['record']['lines']}
                if set(prices) - known:
                    raise ValueError('Unknown settlement line_id')
                for line in row['record']['lines']:
                    if line['line_id'] in prices:
                        value = prices[line['line_id']]
                        line['unit_price_vnd'] = amount(value['unit_price_vnd'])
                        line['price_basis'] = required(value.get('price_basis'), 'price_basis')
                result = store.revise(args.id, row['record'], args.hash)
            elif args.command == 'approve':
                result = store.approve(args.id, args.hash, args.by)
            elif args.command == 'publish-mock':
                result = store.publish_mock(args.id)
            else:
                if Path(args.out).exists():
                    raise ValueError('Export path exists; choose a new filename')
                export_review(store.get(args.id), args.out)
                result = {'exported': args.out}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        p.exit(2, f'Error: {exc}\n')
    finally:
        if store:
            store.close()


if __name__ == '__main__':
    main()
