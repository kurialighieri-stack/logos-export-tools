"""Convierte respuestas JSON de Logos a TXT, opcionalmente DOCX y PDF con calibre."""
import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path
from xml.etree import ElementTree as ET


def tag(node):
    return node.tag.rsplit('}', 1)[-1]


def paragraphs(node):
    if tag(node) == 'Paragraph':
        yield node
    else:
        for child in node:
            yield from paragraphs(child)


def plain(node):
    extra = '\t' if tag(node) == 'Tab' else '\n' if tag(node) in ('Break', 'LineBreak') else ''
    return node.attrib.get('Text', '') + extra + ''.join(plain(c) for c in node)


def runs(node, inherited=None):
    state = dict(inherited or {})
    state.update(node.attrib)
    if 'Text' in node.attrib:
        yield node.attrib['Text'], state
    if tag(node) in ('Tab', 'Break', 'LineBreak'):
        yield ('\t' if tag(node) == 'Tab' else '\n'), state
    for child in node:
        yield from runs(child, state)


def normalize(text):
    return re.sub(r'\s+', '', text)


def safe_name(value):
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', value).strip(' .')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input', type=Path, help='Carpeta json/ del ZIP extraído')
    p.add_argument('output', type=Path)
    p.add_argument('--label', required=True, help='Ej.: Romanos 1–3')
    p.add_argument('--docx', action='store_true')
    p.add_argument('--pdf', action='store_true', help='Implica --docx; necesita ebook-convert')
    p.add_argument('--calibre', default='ebook-convert', help='Nombre o ruta del ejecutable')
    args = p.parse_args()
    files = sorted(args.input.glob('*.json'))
    if not files:
        p.error('No hay respuestas JSON en la carpeta de entrada.')
    if args.pdf and not shutil.which(args.calibre):
        p.error('No se encuentra ebook-convert. Instala calibre o usa --calibre RUTA.')
    if args.docx or args.pdf:
        from docx import Document
        from docx.shared import Inches, Pt
    args.output.mkdir(parents=True, exist_ok=True)
    report = []
    for source in files:
        data = json.loads(source.read_text(encoding='utf-8-sig'))
        meta = data.get('resource', {})
        rid = meta.get('ResourceId', data.get('resolvedResourceId', source.stem))
        if not data.get('richText'):
            report.append({'resource_id': rid, 'status': 'sin contenido'})
            continue
        root = ET.fromstring('<Root>' + data['richText'] + '</Root>')
        nodes = list(paragraphs(root))
        values = [plain(n) for n in nodes]
        text = '\n\n'.join(values)
        original = ''.join(n.attrib.get('Text', '') for n in root.iter())
        if not text.strip() or '\ufffd' in text or normalize(text) != normalize(original):
            raise ValueError(f'Texto vacío, inválido o fuera de párrafos: {rid}')
        title = meta.get('Title', rid)
        author = meta.get('Authors', '').replace('\t', '; ')
        stem = safe_name(title)[:100] + ' [' + safe_name(rid) + ']'
        txt = args.output / (stem + '.txt')
        content = f'{args.label}\n{title}\n{author}\nFuente: Logos · {rid}\n\n{text}\n'
        # No sustituir archivos preexistentes: se puede repetir con otra carpeta.
        with txt.open('x', encoding='utf-8-sig') as out:
            out.write(content)
        if txt.read_text(encoding='utf-8-sig') != content:
            raise ValueError(f'Falló verificación TXT: {rid}')
        item = {'resource_id': rid, 'title': title, 'txt': txt.name, 'characters': len(text), 'text_verified': True}
        if args.docx or args.pdf:
            docx = args.output / (stem + '.docx')
            if docx.exists():
                raise FileExistsError(docx)
            doc = Document()
            sec = doc.sections[0]
            sec.page_width, sec.page_height = Inches(8.5), Inches(11)
            sec.top_margin = sec.bottom_margin = Inches(.85)
            sec.left_margin = sec.right_margin = Inches(.9)
            doc.styles['Normal'].font.name = 'Times New Roman'
            doc.styles['Normal'].font.size = Pt(11)
            doc.add_paragraph(title, 'Title')
            doc.add_paragraph(args.label + (' · ' + author if author else ''), 'Subtitle')
            doc.add_paragraph('Fuente: Logos · ' + rid, 'Subtitle')
            for node in nodes:
                paragraph = doc.add_paragraph()
                for value, attrs in runs(node):
                    run = paragraph.add_run(value)
                    run.bold = attrs.get('FontBold') == 'True'
                    run.italic = attrs.get('FontItalic') == 'True'
            doc.core_properties.title = title + ' — ' + args.label
            doc.core_properties.author = author
            doc.save(docx)
            recovered = ''.join(p.text for p in Document(docx).paragraphs[3:])
            if normalize(recovered) != normalize(original):
                raise ValueError(f'Falló verificación DOCX: {rid}')
            item['docx'] = docx.name
            if args.pdf:
                pdfdir = args.output / 'PDF'
                pdfdir.mkdir(exist_ok=True)
                pdf = pdfdir / (stem + '.pdf')
                if pdf.exists():
                    raise FileExistsError(pdf)
                logdir = args.output / 'logs'
                logdir.mkdir(exist_ok=True)
                with (logdir / (stem + '.log')).open('w', encoding='utf-8') as log:
                    subprocess.run([args.calibre, str(docx.resolve()), str(pdf.resolve()), '--paper-size', 'letter', '--pdf-default-font-size', '11'], stdout=log, stderr=subprocess.STDOUT, check=True)
                from pypdf import PdfReader
                reader = PdfReader(pdf)
                if reader.is_encrypted or not reader.pages:
                    raise ValueError(f'PDF inválido: {rid}')
                item['pdf'] = str(Path('PDF') / pdf.name)
                item['pages'] = len(reader.pages)
        report.append(item)
        print(f'OK: {title} ({len(text)} caracteres)', flush=True)
    with (args.output / 'manifest.json').open('x', encoding='utf-8') as out:
        json.dump({'label': args.label, 'results': report}, out, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
