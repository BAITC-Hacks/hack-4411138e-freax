import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from analyzer import parse_docx
from document_store import ContextLimitError, DocumentStore
from packets import read_packet
from test_analyzer import docx, para


ROOT = Path(__file__).resolve().parents[1]
LINKS = ('parent_id', 'previous_id', 'next_id', 'table_id', 'row_id')
LINK_LISTS = ('row_fragment_ids', 'header_row_ids', 'header_fragment_ids',
              'first_row_fragment_ids')


def heading(text, level=1):
    return para(text, f'<w:pPr><w:outlineLvl w:val="{level - 1}"/></w:pPr>')


def cell(*texts, properties=''):
    return '<w:tc>' + properties + ''.join(para(text) for text in texts) + '</w:tc>'


def row(*cells, header=None, properties=''):
    if header is not None:
        properties = f'<w:trPr><w:tblHeader w:val="{header}"/></w:trPr>'
    return '<w:tr>' + properties + ''.join(cells) + '</w:tr>'


def table(*rows):
    return '<w:tbl>' + ''.join(rows) + '</w:tbl>'


def packet_for(body, document_id='d-one', role='after', prefix_links=True):
    document = parse_docx(docx(body), 'source.docx')
    document.update(id=document_id, role=role, read_status='read', format='docx')
    for p in document['paragraphs']:
        local_id = p['id']
        p.update(id=document_id + ':' + local_id, local_id=local_id,
                 document_id=document_id, document_name=document['name'], format='docx')
        if prefix_links:
            for key in LINKS:
                if p.get(key) is not None:
                    p[key] = document_id + ':' + p[key]
            for key in LINK_LISTS:
                if key in p:
                    p[key] = [document_id + ':' + value for value in p[key]]
    return {'documents':[document], 'complete_read':True, 'mixed':False, 'warnings':[]}


def pid(number, document_id='d-one'):
    return f'{document_id}:p{number}'


class SourceMetadataTests(unittest.TestCase):
    def parse(self, body):
        return parse_docx(docx(body), 'source.docx')['paragraphs']

    def test_text_order_neighbor_links_and_cell_addresses(self):
        ps = self.parse(heading('1. Duties') + table(
            row(cell('Owner'), cell('Duty'), header='true'),
            row(cell('Audit'), cell('Prepare report', 'Keep records')))
            + para('After table'))
        self.assertEqual([p['text'] for p in ps],
                         ['1. Duties', 'Owner', 'Duty', 'Audit', 'Prepare report', 'Keep records', 'After table'])
        self.assertEqual([p['id'] for p in ps], [f'p{i}' for i in range(1, 8)])
        self.assertEqual([p['previous_id'] for p in ps], [None] + [f'p{i}' for i in range(1, 7)])
        self.assertEqual([p['next_id'] for p in ps], [f'p{i}' for i in range(2, 8)] + [None])
        self.assertEqual([p['block_type'] for p in ps], ['heading'] + ['table_cell'] * 5 + ['paragraph'])
        self.assertEqual([p['parent_id'] for p in ps], [None] + ['p1'] * 6)
        self.assertEqual([(p['row_index'], p['column_index']) for p in ps[1:6]],
                         [(0, 0), (0, 1), (1, 0), (1, 1), (1, 1)])
        for p in ps[1:6]:
            self.assertEqual(p['table_id'], 't1')
            self.assertEqual(p['row_id'], f't1:r{p["row_index"]}')
            self.assertEqual(p['header_row_ids'], ['t1:r0'])
            self.assertEqual(p['header_fragment_ids'], ['p2', 'p3'])
            self.assertEqual(p['first_row_fragment_ids'], ['p2', 'p3'])
        self.assertEqual(ps[4]['row_fragment_ids'], ['p4', 'p5', 'p6'])
        self.assertTrue(ps[1]['is_header'])
        self.assertFalse(ps[3]['is_header'])

    def test_first_row_is_context_not_a_guessed_header(self):
        for header in (None, 'false', '0', 'off'):
            with self.subTest(header=header):
                ps = self.parse(table(row(cell('Owner'), cell('Duty'), header=header),
                                      row(cell('Audit'), cell('Prepare report'))))
                self.assertTrue(all(not p['is_header'] for p in ps))
                self.assertEqual(ps[-1]['header_row_ids'], [])
                self.assertEqual(ps[-1]['header_fragment_ids'], [])
                self.assertEqual(ps[-1]['first_row_fragment_ids'], ['p1', 'p2'])

    def test_multiple_explicit_headers_and_empty_first_row(self):
        ps = self.parse(table(row(cell('')), row(cell('Title'), header='1'),
                              row(cell('Owner'), header='on'), row(cell('Audit'))))
        self.assertEqual(ps[-1]['row_index'], 3)
        self.assertEqual(ps[-1]['first_row_fragment_ids'], [])
        self.assertEqual(ps[-1]['header_row_ids'], ['t1:r1', 't1:r2'])
        self.assertEqual(ps[-1]['header_fragment_ids'], ['p1', 'p2'])

    def test_empty_header_element_explicitly_enables_header(self):
        ps = self.parse(table(row(cell('Header'), properties='<w:trPr><w:tblHeader/></w:trPr>'),
                              row(cell('Value'))))
        self.assertTrue(ps[0]['is_header'])
        self.assertEqual(ps[1]['header_fragment_ids'], ['p1'])

    def test_empty_and_deleted_content_do_not_create_paragraph_ids(self):
        body = para('') + '<w:del>' + para('Deleted') + '</w:del>'
        body += table(row(cell(''), cell('Visible')),
                      '<w:moveFrom>' + row(cell('Moved away')) + '</w:moveFrom>',
                      row(cell('Other')))
        ps = self.parse(body)
        self.assertEqual([p['id'] for p in ps], ['p1', 'p2'])
        self.assertEqual([(p['row_index'], p['column_index']) for p in ps], [(0, 1), (1, 0)])
        self.assertEqual(ps[-1]['first_row_fragment_ids'], ['p1'])

    def test_merge_markup_warns_without_inventing_grid_coordinates(self):
        parsed = parse_docx(docx(table(
            row(cell('Wide', properties='<w:tcPr><w:gridSpan w:val="3"/></w:tcPr>'), cell('Next')),
            row(cell('Continued', properties='<w:tcPr><w:vMerge/></w:tcPr>'), cell('Other'),
                properties='<w:trPr><w:gridBefore w:val="2"/></w:trPr>'))), 'merge.docx')
        self.assertEqual([p['column_index'] for p in parsed['paragraphs']], [0, 1, 0, 1])
        self.assertTrue(parsed['layout_warnings'])
        for p in parsed['paragraphs']:
            self.assertTrue(p['layout_warnings'])
            self.assertNotIn('row_span', p)
            self.assertNotIn('column_span', p)

    def test_nested_tables_and_cells_keep_independent_ancestry(self):
        nested = table(row(cell('Nested header'), header='true'), row(cell('Nested value')))
        ps = self.parse(heading('1. Duties') + table(row(
            '<w:tc>' + heading('Cell heading', 2) + nested + para('Cell tail') + '</w:tc>',
            cell('Other cell')))
            + table(row(cell('Other table'))) + para('Body tail'))
        self.assertEqual([p.get('table_id') for p in ps], [None, 't1', 't2', 't2', 't1', 't1', 't3', None])
        self.assertEqual(ps[1]['row_fragment_ids'], ['p2', 'p5', 'p6'])
        self.assertEqual(ps[2]['row_fragment_ids'], ['p3'])
        self.assertEqual(ps[3]['header_fragment_ids'], ['p3'])
        self.assertEqual(ps[3]['parent_id'], 'p2')
        self.assertEqual(ps[4]['parent_id'], 'p2')
        self.assertEqual(ps[5]['parent_id'], 'p1')
        self.assertEqual(ps[-1]['parent_id'], 'p1')

    def test_parent_chain_resets_at_peer_headings_and_numbered_branches(self):
        ps = self.parse(heading('1. Duties') + heading('Audit:', 2)
                        + para('1.1. Prepare:') + para('1.1.1. Check sources') + para('Continuation')
                        + heading('Operations:', 2) + para('1.2. Operate:') + para('1.2.1. Deliver')
                        + heading('2. Other') + para('2.1. Other duty'))
        self.assertEqual([p['parent_id'] for p in ps],
                         [None, 'p1', 'p2', 'p3', 'p4', 'p1', 'p6', 'p7', None, 'p9'])

    def test_plain_colon_introduction_stops_at_new_clause(self):
        ps = self.parse(para('1.1. Scope') + para('Local introduction:') + para('a. First')
                        + para('1.2. Next') + para('b. Second'))
        self.assertEqual([p['parent_id'] for p in ps], [None, 'p1', 'p2', None, 'p4'])

    def test_r8_r9_evidence_sequences_are_unchanged(self):
        gold = {8:(491, '447d90d39b054510d0240f2c6245fe35fffe3c6a23c922ef7a3350df3e57edd2'),
                9:(490, '6636cc4f60b119e04f2f375dfce2a06a244edb956d2a77d0130adaf54ec4f9a9')}
        for version, (count, digest) in gold.items():
            paths = list((ROOT / 'sources').glob(f'*_{version}_*.docx'))
            if not paths:
                self.skipTest('Local R8/R9 sources are not present')
            self.assertEqual(len(paths), 1)
            ps = parse_docx(paths[0].read_bytes(), paths[0].name)['paragraphs']
            value = json.dumps([(p['id'], p['text'], p['section']) for p in ps],
                               ensure_ascii=True, separators=(',', ':')).encode()
            self.assertEqual((len(ps), hashlib.sha256(value).hexdigest()), (count, digest))


class ReadContextTests(unittest.TestCase):
    def assert_exact(self, store, result):
        ids = [p['id'] for p in result['fragments']]
        self.assertEqual(result['fragment_ids'], ids)
        self.assertEqual(result['read_ids'], ids)
        self.assertEqual(store.read_ids, set(ids))
        for key in ('section_fragment_ids', 'parent_fragment_ids', 'neighbor_fragment_ids',
                    'table_row_fragment_ids', 'table_header_fragment_ids', 'table_first_row_fragment_ids'):
            self.assertLessEqual(set(result[key]), set(ids))
        self.assertFalse(result['truncated'])

    def test_table_context_returns_headers_entire_row_and_addresses(self):
        body = heading('1. Duties') + table(
            row(cell('Owner'), cell('Duty'), header='true'),
            row(cell('Audit'), cell('Prepare report', 'Keep records')),
            row(cell('Other owner'), cell('Other duty')),
            row(cell('Far owner'), cell('Far duty')))
        store = DocumentStore(packet_for(body))
        result = store.read_context(pid(5))
        self.assertEqual(result['section_fragment_ids'], [pid(4), pid(5), pid(6)])
        self.assertEqual(result['parent_fragment_ids'], [pid(1)])
        self.assertEqual(result['table_row_fragment_ids'], [pid(4), pid(5), pid(6)])
        self.assertEqual(result['table_header_fragment_ids'], [pid(2), pid(3)])
        self.assertEqual(result['table_first_row_fragment_ids'], [pid(2), pid(3)])
        self.assertEqual(result['fragment_ids'], [pid(i) for i in range(1, 8)])
        selected = next(p for p in result['fragments'] if p['id'] == pid(5))
        self.assertEqual((selected['table_id'], selected['row_id'], selected['column_index']),
                         ('d-one:t1', 'd-one:t1:r1', 1))
        self.assert_exact(store, result)

    def test_unmarked_first_row_remains_distinct_in_context(self):
        body = table(row(cell('Candidate labels')), row(cell('A')), row(cell('B')), row(cell('Selected')))
        store = DocumentStore(packet_for(body))
        result = store.read_context(pid(4))
        self.assertEqual(result['table_header_fragment_ids'], [])
        self.assertEqual(result['table_first_row_fragment_ids'], [pid(1)])
        self.assertEqual(result['fragment_ids'], [pid(1), pid(3), pid(4)])
        self.assert_exact(store, result)

    def test_other_table_headers_are_not_included(self):
        body = table(row(cell('Old header'), header='true'), row(cell('Old value')))
        body += para('Break') + table(row(cell('New header'), header='true'),
                                    row(cell('Near')), row(cell('Selected')))
        store = DocumentStore(packet_for(body))
        result = store.read_context(pid(6))
        self.assertEqual(result['table_header_fragment_ids'], [pid(4)])
        self.assertNotIn(pid(1), result['fragment_ids'])
        self.assert_exact(store, result)

    def test_parent_headings_subclauses_and_neighbors_without_stale_owner(self):
        body = heading('1. Duties') + heading('Former owner:', 2) + para('1.1. Old duty')
        body += heading('Current owner:', 2) + para('1.2. Duties:') + para('1.2.1. First')
        body += para('Continuation') + para('1.2.2. Second') + heading('2. Next') + para('2.1. Outside')
        store = DocumentStore(packet_for(body))
        result = store.read_context(pid(5))
        self.assertEqual(result['section_fragment_ids'], [pid(i) for i in range(5, 9)])
        self.assertEqual(result['parent_fragment_ids'], [pid(1), pid(4)])
        self.assertEqual(result['neighbor_fragment_ids'], [pid(4), pid(9)])
        self.assertEqual(result['fragment_ids'], [pid(1)] + [pid(i) for i in range(4, 10)])
        self.assertNotIn(pid(2), result['fragment_ids'])
        self.assert_exact(store, result)

    def test_deep_ancestry_has_no_four_parent_cap(self):
        body = ''.join(heading(f'Heading {level}', level) for level in range(1, 8)) + para('Evidence')
        store = DocumentStore(packet_for(body))
        result = store.read_context(pid(8))
        self.assertEqual(result['parent_fragment_ids'], [pid(i) for i in range(1, 7)])
        self.assertEqual(result['fragment_ids'], [pid(i) for i in range(1, 9)])
        self.assert_exact(store, result)

    def test_repeated_heading_text_does_not_merge_sections(self):
        body = heading('Owner', 1) + para('Old duty') + heading('Owner', 1) + para('New duty')
        store = DocumentStore(packet_for(body))
        result = store.read_context(pid(4))
        self.assertEqual(result['section_fragment_ids'], [pid(3), pid(4)])
        self.assertEqual(result['parent_fragment_ids'], [])
        self.assertNotIn(pid(1), result['fragment_ids'])
        self.assert_exact(store, result)

    def test_legacy_numbered_parents_do_not_collect_unrelated_colons(self):
        packet = packet_for(heading('1. Duties') + para('Old owner:') + para('1.1. Old')
                            + heading('2. Duties') + para('2.1. New') + para('Continuation'))
        for p in packet['documents'][0]['paragraphs']:
            for key in ('parent_id', 'block_type', 'heading_level'):
                p.pop(key)
        store = DocumentStore(packet)
        result = store.read_context(pid(5))
        self.assertEqual(result['parent_fragment_ids'], [pid(4)])
        self.assertNotIn(pid(2), result['fragment_ids'])
        self.assert_exact(store, result)

    def test_uncertain_pdf_layout_does_not_infer_numbered_parentage(self):
        packet = packet_for(para('1.1. Left column') + para('1.1.1. Right column'))
        document = packet['documents'][0]
        document.update(format='pdf', layout_warning_pages=[1])
        for p in document['paragraphs']:
            p.pop('parent_id')
            p.update(page=1, format='pdf')
        store = DocumentStore(packet)
        result = store.read_context(pid(2))
        self.assertEqual(result['parent_fragment_ids'], [])
        self.assertEqual(result['section_fragment_ids'], [pid(2)])
        self.assertEqual(result['neighbor_fragment_ids'], [pid(1)])
        self.assert_exact(store, result)

    def test_local_and_prefixed_links_resolve_only_within_current_document(self):
        body = heading('1. Duties') + para('1.1. Duty') + para('Continuation')
        for prefix_links in (False, True):
            with self.subTest(prefix_links=prefix_links):
                packet = packet_for(body, prefix_links=prefix_links)
                packet['documents'] += packet_for(body, 'd-other')['documents']
                store = DocumentStore(packet)
                result = store.read_context(pid(2))
                self.assertEqual(result['parent_fragment_ids'], [pid(1)])
                self.assertTrue(all(p['document_id'] == 'd-one' for p in result['fragments']))
                self.assert_exact(store, result)

    def test_cross_document_parent_link_is_not_followed(self):
        packet = packet_for(para('Evidence'))
        packet['documents'] += packet_for(heading('Wrong owner:'), 'd-other')['documents']
        packet['documents'][0]['paragraphs'][0]['parent_id'] = pid(1, 'd-other')
        store = DocumentStore(packet)
        result = store.read_context(pid(1))
        self.assertEqual(result['parent_fragment_ids'], [])
        self.assert_exact(store, result)

    def test_document_scope_returns_every_whole_fragment_without_search_limit(self):
        packet = packet_for(''.join(para(f'1.{i}. Duty {i}') for i in range(1, 81)))
        packet['documents'] += packet_for(para('Other document'), 'd-other')['documents']
        store = DocumentStore(packet)
        hits = store.search_fragments('Duty', limit=1)
        self.assertTrue(hits['truncated'])
        result = store.read_context(hits['hits'][0]['id'], scope='document')
        self.assertEqual(result['fragments'], packet['documents'][0]['paragraphs'])
        self.assertEqual(len(result['fragments']), 80)
        self.assert_exact(store, result)
        self.assertEqual(store.get_coverage()['unread_document_ids'], ['d-other'])

    def test_read_section_alias_logs_one_compatible_action(self):
        store = DocumentStore(packet_for(para('1.1. Evidence')))
        result = store.read_section(pid(1))
        self.assertEqual(result['scope'], 'section')
        self.assertEqual(len(store.actions), 1)
        self.assertEqual(store.actions[0]['tool'], 'read_section')
        self.assert_exact(store, result)

    def test_explicit_response_limit_is_atomic_for_whole_fragments(self):
        packet = packet_for(para('1.1. ' + 'Exact text. ' * 2000))
        store = DocumentStore(packet, max_response_chars=300)
        for scope in ('section', 'document'):
            with self.subTest(scope=scope), self.assertRaises(ContextLimitError) as raised:
                store.read_context(pid(1), scope)
            self.assertGreater(raised.exception.required_chars, 300)
            self.assertEqual(raised.exception.response_limit_chars, 300)
            self.assertEqual(store.read_ids, set())
        coverage = store.get_coverage()
        self.assertFalse(coverage['after_fully_read'])
        self.assertEqual(len(coverage['read_errors']), 2)
        self.assertEqual(coverage['unread_section_ids'], [pid(1)])
        store = DocumentStore(packet, max_response_chars=100_000)
        result = store.read_context(pid(1), 'document')
        self.assertEqual(result['fragments'][0]['text'], packet['documents'][0]['paragraphs'][0]['text'])
        self.assert_exact(store, result)

    def test_limit_boundary_counts_the_complete_serialized_response(self):
        packet = packet_for(para('Evidence'))
        store = DocumentStore(packet, max_response_chars=1)
        with self.assertRaises(ContextLimitError) as raised:
            store.read_context(pid(1))
        size = raised.exception.required_chars
        store.max_response_chars = size
        with self.assertRaises(ContextLimitError) as raised:
            store.read_context(pid(1))
        size = raised.exception.required_chars
        store.max_response_chars = size
        result = store.read_context(pid(1))
        self.assertEqual(len(json.dumps(result, ensure_ascii=False)), size)
        self.assert_exact(store, result)

    def test_failed_read_preserves_prior_coverage(self):
        store = DocumentStore(packet_for(''.join(para(f'1.{i}. Evidence') for i in range(1, 10))))
        store.read_context(pid(1))
        before = set(store.read_ids)
        store.max_response_chars = 1
        with self.assertRaises(ContextLimitError):
            store.read_context(pid(9), 'document')
        self.assertEqual(store.read_ids, before)

    def test_read_page_uses_the_same_atomic_limit(self):
        packet = packet_for(para('Page evidence'))
        document = packet['documents'][0]
        document.update(format='pdf', page_count=1)
        document['paragraphs'][0]['page'] = 1
        store = DocumentStore(packet, max_response_chars=1)
        with self.assertRaises(ContextLimitError):
            store.read_page('d-one', 1)
        self.assertEqual(store.read_ids, set())

    def test_returned_context_cannot_mutate_sources_or_action_history(self):
        store = DocumentStore(packet_for(para('Exact evidence')))
        result = store.read_context(pid(1))
        result['fragments'][0]['text'] = 'Invented'
        result['read_ids'].clear()
        self.assertEqual(store.fragments[pid(1)]['text'], 'Exact evidence')
        self.assertEqual(store.actions[0]['result']['fragments'][0]['text'], 'Exact evidence')
        self.assertEqual(store.actions[0]['result']['read_ids'], [pid(1)])

    def test_invalid_scope_fragment_and_limit_do_not_claim_reads(self):
        store = DocumentStore(packet_for(para('Evidence')))
        for fragment_id, scope in ((pid(1), 'packet'), ('missing', 'section'), (pid(1), [])):
            with self.assertRaises(ValueError):
                store.read_context(fragment_id, scope)
        self.assertEqual(store.read_ids, set())
        self.assertEqual(store.actions, [])
        for limit in (0, -1, True, '10'):
            with self.assertRaises(ValueError):
                DocumentStore(store.packet, max_response_chars=limit)


class CoverageTests(unittest.TestCase):
    def test_unread_document_section_and_fragment_addresses_are_exact(self):
        packet = packet_for(''.join(para(f'1.{i}. Evidence') for i in range(1, 9)))
        store = DocumentStore(packet)
        result = store.read_context(pid(3))
        coverage = store.get_coverage()
        document = coverage['documents'][0]
        unread = [pid(i) for i in range(1, 9) if pid(i) not in result['fragment_ids']]
        self.assertEqual(document['unread_fragment_ids'], unread)
        self.assertEqual(document['unread_section_ids'], unread)
        self.assertEqual(coverage['unread_section_ids'], unread)
        self.assertEqual(coverage['unread_document_ids'], ['d-one'])
        for section_id in list(coverage['unread_section_ids']):
            store.read_context(section_id)
        self.assertTrue(store.get_coverage()['after_fully_read'])
        self.assertEqual(store.get_coverage()['unread_document_ids'], [])

    def test_search_scopes_are_actual_actions_including_empty_and_limited_results(self):
        packet = packet_for(para('1.1. Needle') + para('1.2. Needle'))
        for document_id, role in (('d-before', 'before'), ('d-common', 'common'), ('d-unknown', 'unknown')):
            packet['documents'] += packet_for(para('Needle'), document_id, role)['documents']
        store = DocumentStore(packet)
        self.assertEqual(store.get_coverage()['search_scopes'], [])
        first = store.search_fragments('Needle', role='after', limit=1)
        second = store.search_fragments('Absent', document_id='d-before')
        third = store.search_fragments('Needle', role='after', document_id='d-before')
        before = deepcopy(store.actions)
        coverage = store.get_coverage()
        self.assertEqual(store.actions, before)
        self.assertEqual(store.read_ids, set())
        self.assertEqual(len(coverage['search_scopes']), 3)
        for index, (scope, result) in enumerate(zip(coverage['search_scopes'], (first, second, third))):
            self.assertEqual(scope['action_index'], index + 1)
            self.assertEqual(scope['arguments'], before[index]['arguments'])
            self.assertEqual(scope['searched_document_ids'], result['searched_document_ids'])
            self.assertEqual(scope['returned_fragment_ids'], [h['id'] for h in result['hits']])
            self.assertEqual(scope['matched_count'], result['matched_count'])
            self.assertEqual(scope['truncated'], result['truncated'])
        self.assertEqual(first['searched_document_ids'], ['d-one', 'd-common', 'd-unknown'])
        self.assertEqual(second['searched_document_ids'], ['d-before'])
        self.assertEqual(third['searched_document_ids'], [])

    def test_returned_search_cannot_rewrite_recorded_scope(self):
        store = DocumentStore(packet_for(para('Evidence')))
        result = store.search_fragments('Evidence')
        result['searched_document_ids'].append('invented-document')
        result['hits'].clear()
        coverage = store.get_coverage()
        self.assertEqual(coverage['search_scopes'][0]['searched_document_ids'], ['d-one'])
        self.assertEqual(coverage['search_scopes'][0]['returned_fragment_ids'], [pid(1)])
        self.assertEqual(store.read_ids, set())

    def test_errors_partial_pages_and_layout_warnings_remain_visible(self):
        packet = packet_for(para('Readable but uncertain'))
        document = packet['documents'][0]
        document.update(format='pdf', read_status='partial', error='Unread page', unread_pages=[2],
                        layout_warning_pages=[1], warnings=['Uncertain table layout'])
        packet['documents'].append({'id':'unread-2', 'name':'bad.docx', 'role':'unknown',
                                    'read_status':'error', 'error':'Corrupt file', 'paragraphs':[]})
        packet['complete_read'] = False
        store = DocumentStore(packet)
        result = store.read_context(pid(1), 'document')
        self.assertEqual(result['unread_pages'], [2])
        self.assertEqual(result['layout_warning_pages'], [1])
        coverage = store.get_coverage()
        self.assertFalse(coverage['after_fully_read'])
        self.assertEqual(coverage['unread_document_ids'], ['d-one', 'unread-2'])
        self.assertEqual([e['document_id'] for e in coverage['errors']], ['d-one', 'unread-2'])
        self.assertEqual(coverage['layout_warnings'][0]['pages'], [1])
        self.assertEqual(coverage['layout_warnings'][0]['warnings'], ['Uncertain table layout'])
        self.assertEqual(coverage['search_scopes'], [])

    def test_packet_integration_preserves_local_or_prefixed_context(self):
        body = heading('1. Duties') + table(row(cell('Header'), header='true'), row(cell('Evidence')))
        value = {'name':'source.docx', 'data':base64.b64encode(docx(body)).decode(), 'role':'after'}
        packet = read_packet([value], mode='manual')
        document = packet['documents'][0]
        target = document['paragraphs'][-1]['id']
        store = DocumentStore(packet)
        result = store.read_context(target)
        self.assertEqual(result['parent_fragment_ids'], [document['paragraphs'][0]['id']])
        self.assertEqual(result['table_header_fragment_ids'], [document['paragraphs'][1]['id']])


if __name__ == '__main__':
    unittest.main()
