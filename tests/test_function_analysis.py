import copy
import unittest
from function_analysis import validate_functions, sections, text_signature, focus_batches, focus_validator

BEFORE={'name':'before.docx','paragraphs':[
    {'id':'p1','section':'5','text':'5. Обязанности'},
    {'id':'p2','section':'5.1','text':'5.1. Директор отдела контроля:'},
    {'id':'p3','section':'5.1.1','text':'5.1.1. готовит предложения в план проверок;'}]}
AFTER={'name':'after.docx','paragraphs':[
    {'id':'p1','section':'5','text':'5. Обязанности'},
    {'id':'p2','section':'5.2','text':'5.2. Директоры отделов контроля и анализа:'},
    {'id':'p3','section':'5.2.1','text':'5.2.1. готовят предложения в план проверок;'}]}


def candidate():
    return {'function':'Подготовка предложений в план проверок','category':'содержательно изменена',
            'owner_before':'Директор отдела контроля','owner_after':'Директоры отделов контроля и анализа',
            'owner_before_ids':['p2'],'owner_after_ids':['p2'],
            'before_evidence':[{'id':'p3','quote':'готовит предложения в план проверок;'}],
            'after_evidence':[{'id':'p3','quote':'готовят предложения в план проверок;'}],
            'explanation':'Изменилось явное закрепление обязанности.',
            'limitation':'Исключительная передача не установлена.'}


class FunctionTests(unittest.TestCase):
    def validate(self,value):
        return validate_functions({'findings':[value]},BEFORE,AFTER)

    def test_exact_owners_and_quotes_are_kept(self):
        rows,rejected=self.validate(candidate())
        self.assertEqual(rejected,0)
        self.assertEqual(rows[0]['before_ids'],['p2','p3'])
        self.assertEqual(rows[0]['status'],'unknown')
        self.assertFalse(rows[0]['reviewed'])

    def test_invented_quote_is_rejected_even_with_existing_id(self):
        row=candidate();row['after_evidence'][0]['quote']='утверждают окончательный план проверок;'
        self.assertEqual(self.validate(row),([],1))

    def test_wrong_version_quote_is_rejected(self):
        row=candidate();row['after_evidence']=copy.deepcopy(row['before_evidence'])
        self.assertEqual(self.validate(row),([],1))

    def test_invented_owner_is_rejected(self):
        row=candidate();row['owner_after']='Директор департамента ИТ'
        self.assertEqual(self.validate(row),([],1))

    def test_unknown_owner_is_explicit(self):
        row=candidate();row['owner_after']=None;row['owner_after_ids']=[]
        rows,rejected=self.validate(row)
        self.assertEqual(rejected,0)
        self.assertIsNone(rows[0]['owner_after'])

    def test_matched_function_needs_both_sides(self):
        row=candidate();row['after_evidence']=[]
        self.assertEqual(self.validate(row),([],1))

    def test_unmatched_is_not_loss(self):
        row=candidate();row.update(category='соответствие не установлено',after_evidence=[],owner_after=None,owner_after_ids=[])
        rows,rejected=self.validate(row)
        self.assertEqual(rejected,0)
        self.assertEqual(rows[0]['type'],'function_comparison')

    def test_owner_heading_stays_with_current_numbered_section(self):
        doc={'paragraphs':[{'id':'p1','section':'5','text':'5. Права'},
                           {'id':'p2','section':'Главный аудитор:','text':'Главный аудитор:'},
                           {'id':'p3','section':'5.1','text':'5.1. Обязанности'}]}
        self.assertEqual(len(sections(doc)['5']),3)

    def test_section_signature_never_discards_owner_change(self):
        self.assertNotEqual(text_signature(BEFORE['paragraphs']), text_signature(AFTER['paragraphs']))

    def test_batches_preserve_continuations_and_every_paragraph(self):
        paragraphs = BEFORE['paragraphs'] + [
            {'id':'p4','section':'5.1.1','text':'а. учитывая установленный срок'},
            {'id':'p5','section':'5.1.2','text':'5.1.2. проверяет результат'}]
        batches = focus_batches(paragraphs, budget=30)
        self.assertEqual([p for batch in batches for p in batch], paragraphs)
        self.assertTrue(any([p['id'] for p in batch] == ['p3','p4'] for batch in batches))

    def test_context_only_findings_are_rejected(self):
        self.assertEqual(focus_validator({'p1'})({'findings':[candidate()]},BEFORE,AFTER), ([],1))
        rows, rejected = focus_validator({'p3'})({'findings':[candidate()]},BEFORE,AFTER)
        self.assertEqual((len(rows),rejected),(1,0))
