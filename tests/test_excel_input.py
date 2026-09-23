"""XLSX source-contract checks; fixtures are tiny OOXML, no model/network calls."""
import base64
import hashlib
import io
import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape
from zipfile import ZipFile, ZIP_DEFLATED

from ayqyn.api.server import Handler
from ayqyn.documents.excel import parse_xlsx
from ayqyn.documents.packets import read_packet
from ayqyn.documents.store import DocumentStore


def cell(address, text):
    return f'<c r="{address}" t="inlineStr"><is><t>{escape(text)}</t></is></c>'


def xlsx(sheets=None, *, merge='', table=False, drawing=False):
    sheets = sheets or [('Функции', '<row r="1">'+cell('A1','Владелец')+cell('B1','Обязанность')+'</row>'
                        '<row r="2">'+cell('A2','БВА')+cell('B2','Контролирует устранение нарушений')+'</row>')]
    buffer=io.BytesIO()
    ns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    rel='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    with ZipFile(buffer,'w',ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="xml" ContentType="application/xml"/>'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                   '</Types>')
        z.writestr('xl/workbook.xml',f'<workbook xmlns="{ns}" xmlns:r="{rel}"><sheets>'+''.join(
            f'<sheet name="{escape(name)}" sheetId="{i}" r:id="rId{i}"/>' for i,(name,_) in enumerate(sheets,1))+'</sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'+''.join(
            f'<Relationship Id="rId{i}" Type="{rel}/worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1,len(sheets)+1))+'</Relationships>')
        for i,(_,rows) in enumerate(sheets,1):
            extra=(f'<mergeCells><mergeCell ref="{merge}"/></mergeCells>' if merge and i==1 else '')
            if table and i==1:
                extra+='<tableParts count="1"><tablePart r:id="table1"/></tableParts>'
            z.writestr(f'xl/worksheets/sheet{i}.xml',f'<worksheet xmlns="{ns}" xmlns:r="{rel}"><sheetData>{rows}</sheetData>{extra}</worksheet>')
        if table:
            z.writestr('xl/worksheets/_rels/sheet1.xml.rels',f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="table1" Type="{rel}/table" Target="../tables/table1.xml"/></Relationships>')
            z.writestr('xl/tables/table1.xml',f'<table xmlns="{ns}" id="1" name="Duties" displayName="Duties" ref="A1:B2" headerRowCount="1"><tableColumns count="2"><tableColumn id="1" name="Владелец"/><tableColumn id="2" name="Обязанность"/></tableColumns></table>')
        if drawing:
            z.writestr('xl/drawings/drawing1.xml','<drawing/>')
    return buffer.getvalue()


def upload(raw,role,name=None):
    return {'name':name or role+'.xlsx','role':role,'data':base64.b64encode(raw).decode()}


class ExcelInputTests(unittest.TestCase):
    def test_sheets_and_cells_keep_exact_text_and_independent_ids(self):
        raw=xlsx([('Первый', '<row r="1">'+cell('A1','БВА  сохраняет\nреестр')+'</row>'),
                  ('Второй', '<row r="1">'+cell('A1','Другая обязанность')+'</row>')])
        doc=parse_xlsx(raw,'source.xlsx')
        self.assertEqual(doc['sha256'],hashlib.sha256(raw).hexdigest())
        self.assertEqual([p['id'] for p in doc['paragraphs']],['s1!A1','s2!A1'])
        self.assertEqual(doc['paragraphs'][0]['text'],'БВА  сохраняет\nреестр')
        self.assertEqual(doc['paragraphs'][1]['section'],"'Второй'!A1")

    def test_real_table_headers_and_row_context_are_available(self):
        raw=xlsx(table=True)
        packet=read_packet([upload(raw,'before')],'manual')
        store=DocumentStore(packet)
        target=next(p for p in store.fragments.values() if p['cell']=='B2')
        result=store.read_context(target['id'])
        self.assertEqual({p['cell'] for p in result['fragments']},{'A1','B1','A2','B2'})
        self.assertEqual(len(result['table_header_fragment_ids']),2)
        self.assertTrue(store.check_evidence(target['id'],target['text'])['exists'])
        self.assertTrue(store.check_evidence(target['id'],target['text'])['was_read'])
        hits=store.search_fragments('устранение нарушений')['hits']
        self.assertEqual(hits[0]['id'],target['id'])

    def test_merge_anchor_is_context_not_invented_owner(self):
        rows='<row r="1">'+cell('A1','Список')+'</row><row r="2">'+cell('A2','БВА')+cell('B2','Первая функция')+'</row><row r="3">'+cell('B3','Вторая функция')+'</row>'
        packet=read_packet([upload(xlsx([('Функции',rows)],merge='A2:A3'),'after')],'manual')
        store=DocumentStore(packet)
        target=next(p for p in store.fragments.values() if p['cell']=='B3')
        self.assertIsNone(target['parent_id'])
        self.assertNotIn('owner',target)
        result=store.read_context(target['id'])
        anchor=next(p for p in result['fragments'] if p['cell']=='A2')
        self.assertEqual(anchor['cell_range'],'A2:A3')
        self.assertIn(anchor['id'],result['related_fragment_ids'])
        page=store.read_context_page(target['id'])
        native_anchor=next(p for p in page['fragments'] if p['cell']=='A2')
        self.assertEqual(native_anchor['sheet'],'Функции')
        self.assertEqual(native_anchor['cell_range'],'A2:A3')
        self.assertIn('related',native_anchor['context_roles'])

    def test_formula_cache_is_not_calculated_and_missing_cache_is_partial(self):
        rows='<row r="1"><c r="A1"><f>2+3</f><v>999</v></c><c r="B1"><f>3+4</f></c></row>'
        doc=parse_xlsx(xlsx([('Лист',rows)]),'formulas.xlsx')
        self.assertEqual(doc['paragraphs'][0]['text'],'999')
        self.assertEqual(doc['paragraphs'][0]['formula'],'=2+3')
        self.assertEqual(doc['paragraphs'][1]['text'],'=3+4')
        self.assertFalse(doc['paragraphs'][1]['formula_cached'])
        error_rows='<row r="1"><c r="A1" t="e"><f>1/0</f><v>#DIV/0!</v></c></row>'
        error_doc=parse_xlsx(xlsx([('Лист',error_rows)]),'error.xlsx')
        self.assertTrue(error_doc['extraction_incomplete'])
        self.assertEqual(error_doc['unread_cells'],["'Лист'!A1"])
        packet=read_packet([upload(xlsx([('Лист',rows)]),'before')],'manual')
        self.assertEqual(packet['documents'][0]['read_status'],'partial')
        self.assertFalse(packet['complete_read'])
        self.assertFalse(packet['ready'])

    def test_drawings_are_explicitly_unread(self):
        doc=parse_xlsx(xlsx(drawing=True),'drawing.xlsx')
        self.assertTrue(doc['unread_objects'])
        self.assertTrue(doc['extraction_incomplete'])

    def test_two_excel_versions_keep_provenance_and_roles(self):
        before=xlsx();after=xlsx([('Функции','<row r="1">'+cell('A1','Департамент')+cell('B1','Ведёт реестр')+'</row>')])
        packet=read_packet([upload(before,'before'),upload(after,'after')],'manual')
        self.assertTrue(packet['ready'],packet['warnings'])
        self.assertEqual(len({p['id'] for d in packet['documents'] for p in d['paragraphs']}),6)
        self.assertTrue(all(p['format']=='xlsx' for d in packet['documents'] for p in d['paragraphs']))

    def test_unsupported_and_oversized_inputs_reject_without_truncation(self):
        for raw,name in [(b'not a zip','bad.xlsx'),(xlsx(),'old.xls'),
                         (xlsx(merge='A1:XFD1048576'),'huge.xlsx')]:
            with self.subTest(name=name),self.assertRaises(ValueError):parse_xlsx(raw,name)
        with patch('ayqyn.documents.excel.MAX_TEXT_CHARS',2),self.assertRaisesRegex(ValueError,'limit'):
            parse_xlsx(xlsx(),'large.xlsx')


class ExcelHttpTests(unittest.TestCase):
    def test_prepare_workspace_and_original_excel_download_without_provider(self):
        from ayqyn.agent.state import ResearchState
        raw=xlsx()
        with tempfile.TemporaryDirectory() as tmp, \
             patch('ayqyn.agent.runner.ROOT',Path(tmp)), \
             patch('ayqyn.api.server.RESEARCH_ROOT',Path(tmp)/'output/research'), \
             patch('ayqyn.retrieval.hybrid.HybridIndex',return_value=Mock(metadata={'ready':True})), \
             patch('ayqyn.providers.llm.request_json_api',side_effect=AssertionError('No API')):
            http=ThreadingHTTPServer(('127.0.0.1',0),Handler)
            thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
            base=f'http://127.0.0.1:{http.server_port}'
            try:
                body={'documents':[upload(raw,'common')],'mode':'manual','task':'Проверить источники','config':{}}
                request=Request(base+'/api/research/prepare',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
                with urlopen(request) as response:result=json.load(response)
                state=ResearchState(Path(tmp)/'output/research'/result['id'])
                identifier=state.packet['documents'][0]['id']
                with urlopen(base+'/api/research/'+result['id']+'?view=original&document='+identifier) as response:
                    self.assertEqual(response.read(),raw)
                with urlopen(base+'/api/research/'+result['id']+'?view=workspace') as response:
                    workspace=json.load(response)
                self.assertEqual(workspace['documents'][0]['format'],'xlsx')
                self.assertEqual(workspace['documents'][0]['paragraphs'][0]['cell'],'A1')
            finally:
                http.shutdown();http.server_close();thread.join()
