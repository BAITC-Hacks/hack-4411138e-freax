import hashlib
import io
import unittest
import zipfile
from unittest.mock import patch
from xml.sax.saxutils import escape

from ayqyn.documents import analyzer as analyzer
NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def docx(body, styles=None):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml",
                         '<w:document xmlns:w="' + NS + '"><w:body>'
                         + body + '</w:body></w:document>')
        if styles:
            archive.writestr("word/styles.xml", styles)
    return stream.getvalue()


def para(text, properties=""):
    return '<w:p>' + properties + '<w:r><w:t>' + escape(text) + '</w:t></w:r></w:p>'


def document(*texts):
    return analyzer.parse_docx(docx("".join(para(t) for t in texts)), "пример.docx")


class ParseTests(unittest.TestCase):
    def test_sections_tables_and_evidence(self):
        raw = docx(para("3.4. Структура") + para("1. Отдел анализа")
                   + '<w:tbl><w:tr><w:tc>' + para("Управление образования")
                   + '</w:tc></w:tr></w:tbl>' + para("3.5. Полномочия")
                   + para("Иной текст") + para("4. Ответственность")
                   + para("Последний абзац"))
        result = analyzer.parse_docx(raw, "акт.docx")
        self.assertEqual(result["name"], "акт.docx")
        self.assertEqual(result["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual([p["section"] for p in result["paragraphs"]],
                         ["3.4", "3.4", "3.4", "3.5", "3.5", "4", "4"])
        self.assertEqual(result["paragraphs"][2]["id"], "p3")
        self.assertEqual(result["paragraphs"][1]["text"], "1. Отдел анализа")

    def test_heading_style_inheritance_resets_section(self):
        styles = ('<w:styles xmlns:w="' + NS + '">'
                  '<w:style w:styleId="Base"><w:name w:val="heading 1"/></w:style>'
                  '<w:style w:styleId="Custom"><w:basedOn w:val="Base"/></w:style>'
                  '</w:styles>')
        result = analyzer.parse_docx(docx(
            para("3.4") + para("Отдел анализа")
            + para("Полномочия", '<w:pPr><w:pStyle w:val="Custom"/></w:pPr>')
            + para("Остальной текст"), styles), "акт.docx")
        self.assertEqual(result["paragraphs"][-1]["section"], "Полномочия")

    def test_runs_breaks_and_deleted_revisions(self):
        body = ('<w:p><w:r><w:t>Первый</w:t><w:tab/><w:t>текст</w:t>'
                '<w:br/><w:t>строка</w:t></w:r>'
                '<w:del><w:r><w:delText>Удалено</w:delText></w:r></w:del></w:p>'
                '<w:del>' + para("Удаленный абзац") + '</w:del>')
        result = analyzer.parse_docx(docx(body), "акт.docx")
        self.assertEqual(len(result["paragraphs"]), 1)
        self.assertEqual(result["paragraphs"][0]["text"], "Первый\tтекст\nстрока")

    def test_invalid_empty_and_oversized(self):
        for data in (b"", b"invalid", docx("")):
            with self.assertRaises(ValueError):
                analyzer.parse_docx(data, "акт.docx")
        raw = docx(para("Текст"))
        for bound in ("MAX_UPLOAD_BYTES", "MAX_UNPACKED_BYTES", "MAX_XML_BYTES"):
            with patch.object(analyzer, bound, 1), self.assertRaises(ValueError):
                analyzer.parse_docx(raw, "акт.docx")

    def test_dtd_rejected(self):
        for raw in (b'<!DOCTYPE x [<!ENTITY y "z">]><x/>',
                    '<!DOCTYPE x><x/>'.encode("utf-16")):
            with self.assertRaises(ValueError):
                analyzer._xml(raw)

    def test_missing_document(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            archive.writestr("other.xml", "<x/>")
        with self.assertRaises(ValueError):
            analyzer.parse_docx(stream.getvalue(), "акт.docx")


class RuleTests(unittest.TestCase):
    def test_department_changes_do_not_establish_transfer(self):
        before = document("3.4. Структура", "Отдел анализа; Управление образования")
        after = document("3.4. Структура", "Отдел анализа; Управление культуры")
        result = analyzer.analyze_rules(before, after)
        self.assertEqual({f["type"] for f in result},
                         {"department_added", "department_removed", "department_retained"})
        self.assertTrue(all(f["status"] == "unknown" for f in result))
        names = {"department_retained": "Отдел анализа",
                 "department_added": "Управление культуры",
                 "department_removed": "Управление образования"}
        for finding in result:
            self.assertIn(names[finding["type"]], finding["title"])

    def test_function_disappearance_is_only_risk(self):
        result = analyzer.analyze_rules(document(
            "Отдел осуществляет мониторинг исполнения государственных программ."),
            document("Общие положения"))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["type"], "function_loss")
        self.assertEqual(result[0]["status"], "risk")
        self.assertEqual(result[0]["before_ids"], ["p1"])
        self.assertEqual(result[0]["after_ids"], [])
        self.assertIn("не доказательство", result[0]["explanation"])

    def test_department_names_can_contain_function_nouns(self):
        before = document("3.4. Структура",
                          "а. Департамент непрерывного мониторинга системы внутреннего контроля (ДНМ).",
                          "б. Департамент контроля качества аудита и методологии (ДККМ).",
                          "6.3. Комитетом по аудиту и Советом директоров Общества – по вопросам:")
        after = document("3.4. Структура", "а. Департамент ИТ-аудита и анализа данных (ДИТААД).",
                         "б. Департамент операционного аудита (ДОА).",
                         before["paragraphs"][1]["text"], before["paragraphs"][2]["text"])
        kinds = [f["type"] for f in analyzer.analyze_rules(before, after)]
        self.assertEqual(kinds.count("department_retained"), 2)
        self.assertEqual(kinds.count("department_added"), 2)
        self.assertEqual(kinds.count("department_removed"), 0)

    def test_retained_function_and_rephrasing(self):
        before = document("Отдел осуществляет мониторинг исполнения государственных программ.")
        after = document("Отдел осуществляет регулярный мониторинг исполнения государственных программ.")
        self.assertNotIn("function_loss", [f["type"] for f in analyzer.analyze_rules(before, after)])

    def test_shared_function_candidate(self):
        after = document("Отдел анализа",
                         "Отдел обеспечивает подготовку ежегодных отчетов о выполнении программ.",
                         "Отдел контроля",
                         "Отдел обеспечивает подготовку ежегодных отчетов о выполнении программ.")
        found = [f for f in analyzer.analyze_rules(document("Общие положения"), after)
                 if f["type"] == "duplication"]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["after_ids"], ["p2", "p4"])
        self.assertEqual(found[0]["status"], "risk")

    def test_contradiction_is_internal_and_not_conflict_of_interest(self):
        after = document("Отдел вправе утверждать планы проведения ежегодных проверок учреждений.",
                         "Отдел не вправе утверждать планы проведения ежегодных проверок учреждений.")
        found = analyzer.analyze_rules(document("Общие положения"), after)
        self.assertEqual([f["type"] for f in found], ["contradiction"])
        self.assertEqual(found[0]["status"], "risk")
        self.assertEqual(found[0]["after_ids"], ["p1", "p2"])
        # A changed permission across versions alone is not an internal conflict.
        found = analyzer.analyze_rules(document(after["paragraphs"][0]["text"]),
                                       document(after["paragraphs"][1]["text"]))
        self.assertNotIn("conflict", [f["type"] for f in found])
        self.assertNotIn("contradiction", [f["type"] for f in found])

    def test_long_paragraph_preserved_and_analysis_bounded(self):
        text = "Отдел осуществляет мониторинг исполнения государственных программ. " * 300
        before = document(text)
        after = document(text + " Дополнительное определение.")
        self.assertGreater(len(before["paragraphs"][0]["text"]), 12000)
        self.assertEqual(before["paragraphs"][0]["text"], text.strip())
        with patch.object(analyzer, "SequenceMatcher", side_effect=AssertionError(
                "Длинные абзацы не должны сравниваться посимвольно")):
            found = analyzer.analyze_rules(before, after)
            self.assertEqual(found, [])
            self.assertLess(analyzer._similar(analyzer._normal(text),
                                             analyzer._normal(text[:100])), 0.1)
            tail_change = analyzer._similar("начало " * 2000 + "аудит " * 2000,
                                             "начало " * 2000 + "закупки " * 2000)
            self.assertEqual(tail_change, 0.5)

    def test_all_evidence_references_exist_and_output_is_deterministic(self):
        before = document("3.4. Структура", "Отдел анализа")
        after = document("3.4. Структура", "Отдел учета")
        result = analyzer.analyze_rules(before, after)
        self.assertEqual(result, analyzer.analyze_rules(before, after))
        for finding in result:
            self.assertEqual(set(finding), {"id", "type", "title", "before_ids", "after_ids",
                                           "status", "explanation"})
            for side, source in (("before_ids", before), ("after_ids", after)):
                self.assertTrue(set(finding[side]) <= {p["id"] for p in source["paragraphs"]})


if __name__ == "__main__":
    unittest.main()
