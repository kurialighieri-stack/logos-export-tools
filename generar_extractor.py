"""Genera JavaScript para ejecutar dentro de la sesión propia de Logos Web."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--resources', type=Path, required=True)
    parser.add_argument('--reference', required=True, help='Ej.: bible.66.1-66.3')
    parser.add_argument('--output', type=Path, default=Path('extractor.local.js'))
    args = parser.parse_args()
    resources = json.loads(args.resources.read_text(encoding='utf-8-sig'))
    if not isinstance(resources, list) or not resources:
        parser.error('El inventario debe ser una lista JSON no vacía.')
    for item in resources:
        if not isinstance(item.get('ResourceId'), str):
            parser.error('Cada recurso necesita ResourceId.')
    template = Path(__file__).with_name('extractor.template.js').read_text(encoding='utf-8')
    result = template.replace('__REFERENCE_JSON__', json.dumps(args.reference))
    result = result.replace('__RESOURCES_JSON__', json.dumps(resources, ensure_ascii=False))
    args.output.write_text(result, encoding='utf-8')
    print(f'Generado {args.output}: {len(resources)} recursos; {args.reference}')


if __name__ == '__main__':
    main()
