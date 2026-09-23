"""Детерминированное извлечение DOCX и предварительные выводы по тексту."""

import hashlib
import io
import re
import zipfile
from collections import Counter
from difflib import SequenceMatcher
from xml.etree import ElementTree as ET


MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_UNPACKED_BYTES = 48 * 1024 * 1024
MAX_XML_BYTES = 12 * 1024 * 1024
MAX_ENTRIES = 2048
MAX_PARAGRAPHS = 12000
MAX_ANALYSIS_PARAGRAPHS = 1500
MAX_SEQUENCE_CHARS = 2000
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _normal(text):
    return " ".join(re.findall(r"[\w]+", text.casefold().replace("ё", "е")))


def _xml(raw):
    # Also catches ASCII declarations encoded as UTF-16/UTF-32.
    probe = raw.replace(b"\x00", b"").upper()
    if b"<!DOCTYPE" in probe or b"<!ENTITY" in probe:
        raise ValueError("Объявления DTD и сущностей в DOCX не поддерживаются.")
    return ET.fromstring(raw)


def _paragraph_text(element):
    parts = []

    def walk(node):
        if node.tag in {W + "del", W + "moveFrom", W + "pPr"}:
            return
        if node.tag == W + "t":
            parts.append(node.text or "")
        elif node.tag == W + "tab":
            parts.append("\t")
        elif node.tag in {W + "br", W + "cr"}:
            parts.append("\n")
        else:
            for child in node:
                walk(child)

    walk(element)
    return "".join(parts).strip()


def _source_parent(stack, paragraph_id, number, level, introduction, default=None):
    """Maintain structural ancestry within one body or table cell, not ownership."""
    for index, anchor in enumerate(stack):
        if number and anchor["number"] and not number.startswith(anchor["number"] + "."):
            del stack[index:]
            break
        if level and ((anchor["level"] and anchor["level"] >= level)
                      or (not anchor["level"] and not (
                          number and anchor["number"] and number.startswith(anchor["number"] + ".")))):
            del stack[index:]
            break
    if introduction and not number and not level:
        for index, anchor in enumerate(stack):
            if anchor["introduction"]:
                del stack[index:]
                break
    parent = stack[-1]["id"] if stack else default
    if number or level or introduction:
        stack.append({"id": paragraph_id, "number": number, "level": level,
                      "introduction": introduction and not number and not level})
    return parent


def parse_docx(data: bytes, filename: str) -> dict:
    """Извлекает текущий текст основного документа, включая ячейки таблиц.

    Номера Word, заданные автоматической нумерацией, не выдумываются.
    Колонтитулы, комментарии и удаленные исправления не включаются.

    Source metadata contract (all linked IDs are document-local):
    block_type is heading, clause, paragraph, or table_cell; heading_level is
    the known Word outline level (1-9) or None. parent_id, previous_id, next_id
    reference pN or None. Parents describe structure, not proven ownership.
    Table cells add table_id=tN, row_id=tN:rN, zero-based row_index and
    column_index (XML cell ordinal, NOT a merged-cell grid coordinate),
    is_header (explicit enabled w:tblHeader only), row_fragment_ids,
    header_row_ids, header_fragment_ids, and first_row_fragment_ids.
    The first row is context, never an inferred header. Lists contain only
    emitted paragraphs of the nearest table, excluding nested-table content.
    Packet assembly must prefix all *_id and *_ids links above with its
    document ID, leaving None and empty lists unchanged.
    """
    if not isinstance(data, bytes) or not data:
        raise ValueError("Передайте непустой файл DOCX.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("Размер файла DOCX превышает допустимый предел.")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            names = [entry.filename for entry in entries]
            if len(entries) > MAX_ENTRIES or len(set(names)) != len(names):
                raise ValueError("Недопустимое количество или повторение элементов ZIP.")
            if sum(entry.file_size for entry in entries) > MAX_UNPACKED_BYTES:
                raise ValueError("Распакованный DOCX превышает допустимый размер.")
            for entry in entries:
                if entry.flag_bits & 1:
                    raise ValueError("Зашифрованные файлы DOCX не поддерживаются.")
                if entry.file_size > MAX_XML_BYTES and entry.filename in {
                    "word/document.xml", "word/styles.xml"
                }:
                    raise ValueError("XML документа превышает допустимый размер.")
            if "word/document.xml" not in names:
                raise ValueError("В DOCX отсутствует основной документ.")

            def read_xml(name):
                with archive.open(name) as stream:
                    raw = stream.read(MAX_XML_BYTES + 1)
                if len(raw) > MAX_XML_BYTES:
                    raise ValueError("XML документа превышает допустимый размер.")
                return _xml(raw)

            root = read_xml("word/document.xml")
            styles = {}
            if "word/styles.xml" in names:
                for style in read_xml("word/styles.xml").findall(W + "style"):
                    name = style.find(W + "name")
                    outline = style.find(W + "pPr/" + W + "outlineLvl")
                    base = style.find(W + "basedOn")
                    styles[style.get(W + "styleId")] = (
                        name.get(W + "val", "") if name is not None else "",
                        outline.get(W + "val") if outline is not None else None,
                        base.get(W + "val") if base is not None else None,
                    )
    except (zipfile.BadZipFile, ET.ParseError, RuntimeError, NotImplementedError,
            OSError, EOFError) as exc:
        raise ValueError("Не удалось прочитать DOCX: файл поврежден или не поддерживается.") from exc

    def heading_level(element):
        outline = element.find(W + "pPr/" + W + "outlineLvl")
        if outline is not None:
            value = outline.get(W + "val", "9")
            return int(value) + 1 if value.isdigit() and int(value) < 9 else None
        style = element.find(W + "pPr/" + W + "pStyle")
        current = style.get(W + "val", "") if style is not None else ""
        seen = set()
        while current and current not in seen:
            seen.add(current)
            name, outline, base = styles.get(current, (current, None, None))
            if outline is not None and outline.isdigit():
                return int(outline) + 1 if int(outline) < 9 else None
            match = re.search(r"(?:heading|заголовок)\s*([1-9])", name, re.I)
            if match:
                return int(match.group(1))
            current = base
        return None

    paragraphs = []
    section = ""
    body = root.find(W + "body")
    if body is None:
        raise ValueError("В DOCX отсутствует содержимое документа.")

    tables = []
    body_stack = []

    def visible_paragraphs(node, stack, default=None, table=None, row=None, column=None):
        if node.tag in {W + "del", W + "moveFrom"}:
            return
        if node.tag == W + "tbl":
            table = {"id": "t" + str(len(tables) + 1), "rows": [], "warnings": []}
            tables.append(table)
            default = stack[-1]["id"] if stack else default
            row, column = None, None
        elif node.tag == W + "tr" and table is not None:
            header = node.find(W + "trPr/" + W + "tblHeader")
            row = {"index": len(table["rows"]), "cells": 0, "paragraphs": [],
                   "is_header": header is not None and header.get(W + "val", "true").lower()
                   in {"true", "1", "on"}}
            table["rows"].append(row)
            if any(node.find(W + "trPr/" + W + key) is not None for key in ("gridBefore", "gridAfter")):
                table["warnings"].append("Omitted table grid cells; column_index is only an XML cell ordinal.")
        elif node.tag == W + "tc" and row is not None:
            column = row["cells"]
            row["cells"] += 1
            stack = []
            if any(node.find(W + "tcPr/" + W + key) is not None for key in ("gridSpan", "vMerge", "hMerge")):
                table["warnings"].append("Table merge markup present; merged-cell geometry and ownership are not inferred.")
        if node.tag == W + "p":
            yield node, stack, default, table, row, column
            return
        for child in node:
            yield from visible_paragraphs(child, stack, default, table, row, column)

    for element, stack, default, table, row, column in visible_paragraphs(body, body_stack):
        text = _paragraph_text(element)
        if not text:
            continue
        level = heading_level(element)
        numbered = re.match(r"^\s*(\d+(?:\.\d+)+)\.?[\s\u00a0]+\S", text)
        top = re.match(r"^\s*(\d+)[.)]?\s+\S", text) if level else None
        if top is None:
            top = re.match(
                r"^\s*(\d+)\.\s+(?:общие положения|функции|задачи|права|"
                r"ответственность|структура|организация|заключительные положения)\b",
                text, re.I)
        standalone = re.fullmatch(r"\s*(\d+(?:\.\d+)+)\.?\s*", text)
        chapter = re.match(r"^\s*(?:раздел|глава)\s+(\d+)\b", text, re.I)
        if numbered or standalone:
            section = (numbered or standalone).group(1)
        elif top or chapter:
            section = (top or chapter).group(1)
        elif level:
            section = text
        paragraph_id = "p" + str(len(paragraphs) + 1)
        marker = numbered or standalone or top or chapter
        number = marker.group(1) if marker else None
        block_type = "heading" if level or top or chapter else "clause" if number else "paragraph"
        paragraph = {"id": paragraph_id, "text": text, "section": section,
                     "block_type": block_type, "heading_level": level,
                     "parent_id": _source_parent(stack, paragraph_id, number,
                                                 level or (1 if top or chapter else None),
                                                 text.endswith(":"), default),
                     "previous_id": paragraphs[-1]["id"] if paragraphs else None,
                     "next_id": None}
        if paragraphs:
            paragraphs[-1]["next_id"] = paragraph_id
        if table is not None and row is not None and column is not None:
            paragraph.update(block_type="table_cell", table_id=table["id"],
                             row_id=f'{table["id"]}:r{row["index"]}',
                             row_index=row["index"], column_index=column,
                             is_header=row["is_header"])
            row["paragraphs"].append(paragraph)
        paragraphs.append(paragraph)
        if len(paragraphs) > MAX_PARAGRAPHS:
            raise ValueError("В документе слишком много абзацев.")
    if not paragraphs:
        raise ValueError("В DOCX не найден доступный текст.")
    layout_warnings = []
    for table in tables:
        headers = [row for row in table["rows"] if row["is_header"]]
        header_ids = [p["id"] for row in headers for p in row["paragraphs"]]
        first_ids = [p["id"] for p in table["rows"][0]["paragraphs"]] if table["rows"] else []
        warnings = list(dict.fromkeys(table["warnings"]))
        layout_warnings.extend(f'{table["id"]}: {warning}' for warning in warnings)
        for row in table["rows"]:
            row_ids = [p["id"] for p in row["paragraphs"]]
            for paragraph in row["paragraphs"]:
                paragraph.update(row_fragment_ids=list(row_ids),
                                 header_row_ids=[f'{table["id"]}:r{header["index"]}' for header in headers],
                                 header_fragment_ids=list(header_ids),
                                 first_row_fragment_ids=list(first_ids),
                                 layout_warnings=list(warnings))
    return {"name": str(filename), "paragraphs": paragraphs,
            "sha256": hashlib.sha256(data).hexdigest(),
            "warnings": layout_warnings, "layout_warnings": layout_warnings}


_DEPARTMENT = re.compile(
    r"\b(?:департамент|управление|отдел|комитет|служба|сектор)\s+[^;\n]+", re.I)
_DEPARTMENT_ACTION = re.compile(
    r"\b(?:осуществляет|обеспечивает|организует|координирует|контролирует|"
    r"разрабатывает|утверждает|проводит|отвечает|вед[её]т|формирует|направляет|согласовывает|обязан|вправе)\b", re.I)
_FUNCTION = re.compile(
    r"\b(?:осуществля\w*|обеспечива\w*|организ\w*|координ\w*|"
    r"контрол\w*|разрабатыва\w*|утвержда\w*|провод\w*|вед[её]т|"
    r"формиру\w*|направля\w*|согласовыва\w*|ведение|подготов\w*|рассматрива\w*|мониторинг|отвеча\w*|"
    r"обязан\w*|вправе|запрещ\w*|разреш\w*)", re.I)


def _departments(paragraphs):
    found = {}
    for paragraph in paragraphs:
        text = paragraph["text"]
        section = paragraph.get("section", "")
        in_list = section == "3.4" or section.startswith("3.4.")
        # Outside the designated list, only short nominal headings are names.
        if not in_list and (len(text) > 180 or _DEPARTMENT_ACTION.search(text)):
            continue
        for match in _DEPARTMENT.finditer(text):
            prefix = text[:match.start()].strip(" \t0123456789.()–—-:•")
            if not in_list and prefix:
                continue
            name = match.group(0).strip(" \t.,:–—-")
            if _DEPARTMENT_ACTION.search(name) or len(name) > 180:
                continue
            key = _normal(name)
            found.setdefault(key, {"name": name, "ids": []})["ids"].append(paragraph["id"])
    return found


def _similar(a, b):
    if a == b:
        return 1.0
    # Long paragraphs retain all evidence; avoid quadratic character matching.
    if max(len(a), len(b)) > MAX_SEQUENCE_CHARS:
        aa, bb = Counter(a.split()), Counter(b.split())
        total = max(sum(aa.values()), sum(bb.values()))
        return sum((aa & bb).values()) / total if total else 0.0
    aa, bb = set(a.split()), set(b.split())
    if not aa or not bb:
        return 0.0
    overlap = len(aa & bb) / max(len(aa), len(bb))
    if overlap < 0.35:
        return overlap
    return max(overlap, SequenceMatcher(None, a, b, autojunk=False).ratio())


def _polarity(text):
    value = _normal(text)
    negative = re.search(r"\b(?:не вправе|не обязан[аы]?|не осуществляет|"
                         r"запрещается|запрещено)\b", value)
    positive = re.search(r"\b(?:вправе|обязан[аы]?|осуществляет|"
                         r"разрешается|разрешено)\b", value)
    match = negative or positive
    if not match:
        return None
    token = match.group()
    family = ("право" if "вправе" in token else
              "обязанность" if "обязан" in token else
              "действие" if "осуществляет" in token else "разрешение")
    residual = (value[:match.start()] + value[match.end():]).strip()
    return bool(negative), family, residual


def analyze_rules(before, after) -> list:
    """Возвращает кандидатов с идентификаторами только исходных абзацев.

    Сходство текста не устанавливает передачу полномочий. Сравнение не
    учитывает внешние акты, приложения и юридическую силу документов.
    Противоположные формулировки имеют тип contradiction; конфликт интересов
    (conflict) требует отдельной проверки исполнителя и объекта действий ИИ.
    """
    old, new = before["paragraphs"], after["paragraphs"]
    if max(len(old), len(new)) > MAX_ANALYSIS_PARAGRAPHS:
        raise ValueError("Для анализа по правилам допустимо не более 1500 абзацев на документ.")
    for paragraphs in (old, new):
        if sum(len(p["text"]) for p in paragraphs) > 250000:
            raise ValueError("Объем текста превышает предел анализа по правилам.")
    findings = []

    def add(kind, title, before_ids, after_ids, explanation):
        findings.append({"id": "f" + str(len(findings) + 1), "type": kind,
                         "title": title, "before_ids": list(dict.fromkeys(before_ids)),
                         "after_ids": list(dict.fromkeys(after_ids)),
                         "status": "unknown" if kind.startswith("department_") else "risk",
                         "explanation": "Кандидат: требуется проверка. " + explanation})

    old_depts, new_depts = _departments(old), _departments(new)
    for key in sorted(old_depts.keys() | new_depts.keys()):
        left, right = old_depts.get(key), new_depts.get(key)
        if left and right:
            add("department_retained", "Название встречается в обеих версиях: " + right["name"],
                left["ids"], right["ids"],
                "Совпало название подразделения. Это не доказывает сохранение его функций или правового статуса.")
        elif left:
            add("department_removed", "Название не найдено в новой версии: " + left["name"],
                left["ids"], [],
                "Название найдено только в прежнем тексте. Возможны переименование, реорганизация или неполнота документа; передача функций не установлена.")
        else:
            add("department_added", "Название найдено в новой версии: " + right["name"],
                [], right["ids"],
                "Название найдено только в новом тексте. Создание подразделения и получение им функций требуют отдельного подтверждения.")

    old_functions = [(p, _normal(p["text"])) for p in old
                     if len(p["text"]) >= 40 and _FUNCTION.search(p["text"])]
    new_text = [(p, _normal(p["text"])) for p in new]
    for paragraph, value in old_functions:
        if not any(_similar(value, other) >= 0.65 for _, other in new_text):
            add("function_loss", "Возможное исчезновение формулировки функции",
                [paragraph["id"]], [],
                "В новом тексте не найден достаточно похожий абзац. Это риск утраты функции, а не доказательство: проверьте перефразирование, разделение абзацев и другие документы.")

    functions = [(p, value) for p, value in new_text
                 if len(p["text"]) >= 40 and _FUNCTION.search(p["text"])]
    for index, (left, a) in enumerate(functions):
        pa = _polarity(left["text"])
        for right, b in functions[index + 1:]:
            pb = _polarity(right["text"])
            if (pa and pb and pa[0] != pb[0] and pa[1] == pb[1]
                    and len(pa[2].split()) >= 4 and _similar(pa[2], pb[2]) >= 0.9):
                add("contradiction", "Возможное противоречие формулировок",
                    [], [left["id"], right["id"]],
                    "Найдены похожие положения с противоположными маркерами разрешения, обязанности или действия. Проверьте субъект, условия, исключения и область применения.")
            elif _similar(a, b) >= 0.82:
                add("duplication", "Возможное дублирование формулировок функций",
                    [], [left["id"], right["id"]],
                    "Абзацы содержат совпадающие или близкие формулировки. Это не доказывает дублирование полномочий: проверьте исполнителей, территорию, этапы работы и совместную ответственность.")
    return findings
