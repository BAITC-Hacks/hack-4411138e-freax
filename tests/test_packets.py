import base64
from pathlib import Path
import unittest
from unittest.mock import patch
from packets import read_packet
from document_store import DocumentStore
from test_analyzer import docx, para

ROOT=Path(__file__).resolve().parents[1]


def upload(text, name='file.docx', role=None):
    result={'name':name,'data':base64.b64encode(docx(''.join(para(t) for t in text))).decode()}
    if role: result['role']=role
    return result


def pdfs(case):
    return [{'name':p.name,'data':base64.b64encode(p.read_bytes()).decode()}
            for p in sorted((ROOT/'osnovanie_dataset_v1'/'inputs'/case).rglob('*.pdf'))]


class PacketTests(unittest.TestCase):
    def test_pdf_cases_read_real_bytes_and_roles_ignore_filenames(self):
        for number in range(1,11):
            with self.subTest(case=number):
                values=pdfs(f'C{number:03d}')
                self.assertEqual(len(values),4)
                first=read_packet(values)
                shuffled=[{**v,'name':f'renamed-{i}.pdf'} for i,v in enumerate(reversed(values))]
                second=read_packet(shuffled)
                self.assertTrue(first['ready'],first['warnings'])
                self.assertEqual(len(first['documents']),4)
                self.assertEqual(sorted(d['role'] for d in first['documents']),['after','after','before','before'])
                self.assertEqual({d['id']:d['role'] for d in first['documents']},{d['id']:d['role'] for d in second['documents']})
                ids=[p['id'] for d in first['documents'] for p in d['paragraphs']]
                self.assertEqual(len(ids),len(set(ids)))
                self.assertTrue(all(p['page']==1 for d in first['documents'] for p in d['paragraphs']))

    def test_mixed_cases_are_not_silently_merged(self):
        packet=read_packet(pdfs('C001')+pdfs('C002'))
        self.assertTrue(packet['mixed'])
        self.assertFalse(packet['ready'])

    def test_duplicate_does_not_add_a_source(self):
        values=pdfs('C010')
        packet=read_packet(values+[values[0]])
        self.assertEqual((packet['input_count'],packet['unique_count'],len(packet['duplicates'])),(5,4,1))

    def test_manual_role_preserved_with_conflict_warning(self):
        packet=read_packet([upload(['Редакция 2, после изменений','2.1. Отдел ведёт реестр.'],role='before')],'manual')
        doc=packet['documents'][0]
        self.assertEqual((doc['role'],doc['inferred_role']),('before','after'))
        self.assertTrue(doc['warnings'])

    def test_ambiguous_dates_do_not_create_roles(self):
        packet=read_packet([upload(['Подписано 01.03.2026','Вступает в силу 01.04.2026','2.1. Отдел ведёт реестр.'])])
        self.assertEqual(packet['documents'][0]['role'],'unknown')
        self.assertFalse(packet['ready'])

    def test_common_document_applies_to_both_without_duplicate_identity(self):
        packet=read_packet([upload(['Общий действующий документ','2.1. Отдел ведёт реестр.'])])
        self.assertEqual(packet['before']['paragraphs'][0]['id'],packet['after']['paragraphs'][0]['id'])
        self.assertEqual(packet['unique_count'],1)

    def test_error_and_unsupported_file_remain_in_registry(self):
        packet=read_packet(pdfs('C010')+[{'name':'bad.pdf','data':'???'}, {'name':'table.xlsx','data':base64.b64encode(b'table').decode()}])
        self.assertEqual(len(packet['documents']),6)
        self.assertEqual(sum(d['read_status']=='error' for d in packet['documents']),2)
        self.assertFalse(packet['complete_read'])
        self.assertFalse(packet['ready'])

    def test_explicit_unknown_override_is_respected(self):
        values=pdfs('C010');initial=read_packet(values)
        sha=initial['documents'][0]['sha256']
        packet=read_packet(values,overrides={sha:'unknown'})
        self.assertEqual(packet['documents'][0]['role'],'unknown')
        self.assertFalse(packet['ready'])

    def test_partially_unread_pdf_does_not_count_as_complete(self):
        from pdf_input import parse_pdf
        values=pdfs('C010')
        def incomplete(raw,name):
            doc=parse_pdf(raw,name)
            doc['unread_pages']=[2]
            return doc
        with patch('pdf_input.parse_pdf',side_effect=incomplete):
            packet=read_packet(values)
        self.assertFalse(packet['complete_read'])
        self.assertTrue(all(d['read_status']=='partial' for d in packet['documents']))
        self.assertTrue(all(d['paragraphs'] for d in packet['documents']))

    def test_duplicate_unread_files_keep_visible_error_without_identity_collision(self):
        invalid={'name':'bad.pdf','data':base64.b64encode(b'not a pdf').decode()}
        packet=read_packet([invalid,invalid])
        self.assertEqual((len(packet['documents']),len(packet['duplicates'])),(1,1))
        self.assertFalse(packet['complete_read'])


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.store=DocumentStore(read_packet(pdfs('C010')))

    def test_search_is_not_reading_or_evidence_of_absence(self):
        hits=self.store.search_fragments('реестр аварий',role='after')
        self.assertTrue(hits['hits'])
        self.assertFalse(self.store.get_coverage()['after_fully_read'])
        self.assertEqual(sum(d['read_fragments'] for d in self.store.get_coverage()['documents']),0)
        self.assertEqual(self.store.search_fragments('zzzznothing')['hits'],[])

    def test_read_context_and_exact_evidence(self):
        hit=self.store.search_fragments('выбирает поставщиков',role='after')['hits'][0]
        result=self.store.read_section(hit['id'])
        self.assertIn(hit['id'],[p['id'] for p in result['fragments']])
        self.assertEqual(result['document_id'],hit['document_id'])
        p=self.store.fragments[hit['id']]
        self.assertTrue(self.store.check_evidence(hit['id'],p['text'])['exists'])
        self.assertTrue(self.store.check_evidence(hit['id'],p['text'])['was_read'])
        self.assertFalse(self.store.check_evidence(hit['id'],'Вымышленная обязанность')['exists'])

    def test_read_page_coverage_is_scoped_to_input(self):
        for d in self.store.documents.values():
            if d['role']=='after': self.store.read_page(d['id'],1)
        self.assertTrue(self.store.get_coverage()['after_fully_read'])
        self.assertFalse(all(d['fully_read'] for d in self.store.get_coverage()['documents']))

    def test_unknown_versions_included_in_search_but_block_full_coverage(self):
        packet=read_packet([upload(['2.1. Отдел ведет реестр аварий сети.'])])
        store=DocumentStore(packet)
        hit=store.search_fragments('реестр',role='after')['hits'][0]
        self.assertEqual(hit['role'],'unknown')
        store.read_section(hit['id'])
        self.assertFalse(store.get_coverage()['after_fully_read'])


if __name__=='__main__': unittest.main()
