"""Offline submission regressions for actions ending in a colon."""
from pathlib import Path
import tempfile
import unittest

from ayqyn.documents.store import DocumentStore
from ayqyn.documents.packets import read_packet
from ayqyn.agent.runner import DEFAULT_BUDGET
from ayqyn.agent.state import ResearchState
from test_packets import upload


class DuplicationColonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def make_case(self, alpha=None, beta=None):
        packet = read_packet([
            upload([
                '1.1. Team Alpha reviews supplier contracts before signature for delivery deadlines.',
            ], name='before.docx', role='before'),
            upload(alpha if alpha is not None else [
                '1.1. Team Alpha:',
                '1.1.1. Reviews supplier contracts before signature for:',
                'a. delivery deadlines.',
            ], name='alpha.docx', role='after'),
            upload(beta if beta is not None else [
                '1.2. Team Beta:',
                '1.2.1. Reviews supplier contracts before signature for delivery deadlines.',
            ], name='beta.docx', role='after'),
        ], mode='manual')
        self.assertTrue(packet['ready'], packet['warnings'])
        self.state = ResearchState(Path(self.temp.name) / 'run', packet,
                                   'Compare two explicit after assignments', DEFAULT_BUDGET)
        self.state.data['research_policy'] = 4
        self.store = DocumentStore(packet)
        self.old, self.alpha_doc, self.beta_doc = packet['documents']
        self.alpha = self.alpha_doc['paragraphs']
        self.beta = self.beta_doc['paragraphs']

    @staticmethod
    def evidence(paragraph):
        return {'fragment_id': paragraph['id'], 'quote': paragraph['text']}

    def finding(self):
        return {
            'group': 'risk', 'category': 'duplication', 'assertion_type': 'observation',
            'function': 'Review supplier contracts before signature for delivery deadlines',
            'owner_before': None, 'owner_after': 'Team Alpha',
            'before_evidence': [],
            'after_evidence': [self.evidence(p) for p in self.alpha + self.beta],
            'explanation': 'Team Alpha and Team Beta both review the same contracts '
                           'at the same stage for the same delivery deadlines.',
            'limitations': ['Two explicit assignments are a candidate risk, not proof of redundant work.'],
            # Cite the operative clauses here; the dependent continuation is in after_evidence.
            'claim_checks': [
                {'kind': 'duplication_assignment',
                 'evidence': [self.evidence(p) for p in self.alpha[:2]],
                 'result': 'Team Alpha reviews supplier contracts before signature for delivery deadlines.'},
                {'kind': 'duplication_assignment',
                 'evidence': [self.evidence(p) for p in self.beta[:2]],
                 'result': 'Team Beta reviews supplier contracts before signature for delivery deadlines.'},
            ],
        }

    def read_all(self):
        for doc in self.store.documents.values():
            self.store.read_context(doc['paragraphs'][0]['id'], 'document')

    def submit(self, finding):
        # Incomplete overall coverage must not mask a finding-level evidence failure.
        return self.state.submit(self.store, [finding], 'insufficient_data', [],
                                 'Assess only the two cited assignments.')

    def assert_rejected_for_assignments(self, result):
        self.assertFalse(result['accepted'], result)
        self.assertIn('two duplication_assignment checks', str(result['errors']))
        self.assertEqual(self.state.data['findings'], [])

    def test_two_plain_action_assignments_are_accepted(self):
        self.make_case(alpha=[
            '1.1. Team Alpha:',
            '1.1.1. Reviews supplier contracts before signature for delivery deadlines.',
        ])
        self.read_all()
        result = self.submit(self.finding())
        self.assertTrue(result['accepted'], result)
        self.assertEqual(result['count'], 1)

    def test_colon_action_with_read_child_continuation_is_accepted(self):
        self.make_case()
        owner, action, continuation = self.alpha
        self.assertEqual(action['block_type'], 'clause')
        self.assertTrue(action['text'].endswith(':'))
        self.assertEqual(continuation['parent_id'], action['id'])
        context = self.store.read_context(action['id'])
        self.assertIn(owner['id'], context['parent_fragment_ids'])
        self.assertIn(continuation['id'], context['section_fragment_ids'])
        self.read_all()
        finding = self.finding()
        for evidence in finding['after_evidence']:
            checked = self.store.check_evidence(**evidence)
            self.assertTrue(checked['exists'], evidence)
            self.assertTrue(checked['was_read'], evidence)
            self.assertEqual(self.store.documents[checked['document_id']]['role'], 'after')
        for owner_name, check in zip(('Team Alpha', 'Team Beta'), finding['claim_checks']):
            self.assertEqual(check['kind'], 'duplication_assignment')
            self.assertTrue(any(owner_name in e['quote'] for e in check['evidence']))
        result = self.submit(finding)
        self.assertTrue(result['accepted'], result)
        self.assertEqual(result['count'], 1)
        saved = self.state.data['findings'][0]
        self.assertEqual(saved['after_evidence'], finding['after_evidence'])
        self.assertEqual(saved['claim_checks'], finding['claim_checks'])

    def test_bare_owner_heading_is_not_an_action_assignment(self):
        self.make_case(alpha=['1.1. Team Alpha:'])
        # A numbered nominal heading can be parsed as a clause, not a Word heading.
        self.assertEqual(self.alpha[0]['block_type'], 'clause')
        self.read_all()
        self.assert_rejected_for_assignments(self.submit(self.finding()))

    def test_duty_to_detect_duplication_is_not_two_assignments(self):
        self.make_case(alpha=[
            '1.1. Team Alpha:',
            '1.1.1. Identifies insufficient or duplicate assurance coverage.',
        ], beta=['1.2. Team Beta:'])
        self.read_all()
        finding = self.finding()
        finding.update(function='Duplicate assurance coverage',
                       explanation='The duty to identify duplication allegedly establishes duplicate coverage.')
        duty = self.evidence(self.alpha[1])
        finding['claim_checks'][0]['result'] = 'Team Alpha identifies duplicate assurance coverage.'
        finding['claim_checks'][1].update(
            evidence=[self.evidence(self.beta[0]), duty],
            result='The same detection duty allegedly establishes a second assignment to Team Beta.')
        self.assert_rejected_for_assignments(self.submit(finding))

    def test_unread_continuation_cannot_support_a_dependent_claim(self):
        self.make_case()
        owner, action, continuation = self.alpha
        page = self.store.read_context_page(owner['id'], 'document', limit_chars=1500)
        self.assertEqual([p['id'] for p in page['fragments']], [owner['id'], action['id']])
        self.assertEqual(page['next_offset'], 2)
        self.store.read_context(self.old['paragraphs'][0]['id'], 'document')
        self.store.read_context(self.beta[0]['id'], 'document')
        self.assertEqual(self.store.read_ids, set(self.store.fragments) - {continuation['id']})
        checked = self.store.check_evidence(**self.evidence(continuation))
        self.assertTrue(checked['exists'])
        self.assertFalse(checked['was_read'])
        for cite_continuation in (True, False):
            with self.subTest(cite_continuation=cite_continuation):
                finding = self.finding()
                if not cite_continuation:
                    finding['after_evidence'].remove(self.evidence(continuation))
                result = self.submit(finding)
                self.assertFalse(result['accepted'], result)
                self.assertEqual(self.state.data['findings'], [])
                if cite_continuation:
                    self.assertTrue(any(continuation['id'] in message
                                        for error in result['errors'] if error['finding'] == 1
                                        for message in error['errors']), result)


if __name__ == '__main__':
    unittest.main()
