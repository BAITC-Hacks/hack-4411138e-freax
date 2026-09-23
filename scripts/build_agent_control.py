"""Generate the explicitly synthetic source files used by the live revision check."""
import json
from pathlib import Path
import zipfile
from xml.sax.saxutils import escape

ROOT=Path(__file__).resolve().parents[1]


def build():
    fixture=json.loads((ROOT/'tests/fixtures/agent_revision.json').read_text(encoding='utf-8'))
    folder=ROOT/'output'/'agent-control'
    folder.mkdir(parents=True,exist_ok=True)
    for doc in fixture['documents']:
        body=''.join('<w:p><w:r><w:t>'+escape(text)+'</w:t></w:r></w:p>' for text in doc['paragraphs'])
        with zipfile.ZipFile(folder/doc['name'],'w',zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
            archive.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
            archive.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'+body+'</w:body></w:document>')
    return folder


if __name__=='__main__': print(build())
