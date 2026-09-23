import copy
import unittest
from unittest.mock import patch
from batch import classify_documents, combine_documents
from llm import classify_with_model


def document(name, text='Функция отдела: подготовка отчета.'):
    return {'name':name,'sha256':'hash','paragraphs':[{'id':'p1','text':text,'section':'1.1'}]}


class PacketTests(unittest.TestCase):
    def test_mixed_order_multiple_families(self):
        names=['Аудит_редакция_9.docx','План_2021.docx','Аудит_редакция_8.docx','План_2022.docx']
        docs=classify_documents([document(name) for name in names],[{}]*4)
        self.assertEqual([d['side'] for d in docs],['after','before','before','after'])
        before=combine_documents(docs,'before');after=combine_documents(docs,'after')
        self.assertEqual([p['id'] for p in before['paragraphs']],['d2:p1','d3:p1'])
        self.assertEqual(after['paragraphs'][0]['document_name'],names[0])
        self.assertEqual(docs[0]['paragraphs'][0]['id'],'d1:p1')

    def test_unknown_and_three_revisions_not_guessed(self):
        names=['a.docx','b.docx','Аудит_v1.docx','Аудит_v2.docx','Аудит_v3.docx']
        docs=classify_documents([document(name,'Закон 2021 года') for name in names],[{}]*5)
        self.assertTrue(all(d['side'] is None for d in docs))

    def test_labels_manual_and_duplicate_names(self):
        docs=classify_documents([document('отчет_до.docx'),document('отчет_до.docx'),document('отчет_после.docx')],[{}, {'side':'after'}, {}])
        self.assertEqual([d['side'] for d in docs],['before','after','after'])
        self.assertEqual(docs[1]['classification'],'manual')
        self.assertEqual(len({p['id'] for p in combine_documents(docs,'after')['paragraphs']}),2)

    def test_model_assignment_requires_real_quote_and_unique_assignment(self):
        docs=classify_documents([document('one.docx','Редакция до реорганизации'),document('two.docx','Редакция после реорганизации')],[{},{}])
        payload={'assignments':[{'id':'d1','side':'before','quote':'Редакция до реорганизации','reason':'Явно указано до.'}, {'id':'d2','side':'after','quote':'придуманная цитата','reason':'test'}]}
        with patch('llm.request_json',return_value=(payload,{})): classify_with_model(docs,{})
        self.assertEqual(docs[0]['side'],'before');self.assertIsNone(docs[1]['side'])
        self.assertEqual(docs[0]['classification_quote'],'Редакция до реорганизации')
        payload['assignments']=[{'id':'d2','side':side,'quote':'Редакция после реорганизации','reason':'test'} for side in ['before','after']]
        with patch('llm.request_json',return_value=(payload,{})): classify_with_model(docs,{})
        self.assertIsNone(docs[1]['side'])

    def test_model_cannot_override_existing_assignment(self):
        docs=classify_documents([document('до.docx')],[{}]);before=copy.deepcopy(docs)
        with patch('llm.request_json',return_value=({'assignments':[{'id':'d1','side':'after','quote':'до.docx','reason':'bad'}]},{})):classify_with_model(docs,{})
        self.assertEqual(docs,before)
