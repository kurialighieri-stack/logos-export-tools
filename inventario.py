"""Lee un catálogo local de Logos en modo solo lectura y filtra por libro bíblico."""
import argparse
import json
import re
import sqlite3
from pathlib import Path


def covers(spans, book):
    for span in (spans or '').split('\t'):
        match = re.fullmatch(r'bible[^.]*\.(\d+)(?:\.\d+)*(?:-(\d+)(?:\.\d+)*)?', span)
        if match and int(match[1]) <= book <= int(match[2] or match[1]):
            return True
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', type=Path, required=True)
    parser.add_argument('--book', type=int, required=True, help='Número Logos: Isaías=23; Romanos=66')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    with sqlite3.connect(args.catalog.resolve().as_uri() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT ResourceId,Title,Authors,Languages,ReferenceSupersets FROM Records WHERE Type='text.monograph.commentary.bible'")
        result = [dict(row) for row in rows if covers(row['ReferenceSupersets'], args.book)]
    result.sort(key=lambda row: row['Title'])
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'{len(result)} candidatos en {args.output}. La cobertura del capítulo se comprueba al extraer.')


if __name__ == '__main__':
    main()
