"""Reproducible, explicitly fictional eight-document AYQYN demonstration packet."""
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZipFile, ZIP_DEFLATED
import json

ROOT = Path(__file__).resolve().parents[1]
PACKET = {
    'Структура': (
        ['3.4. Структура организации', 'Отдел планирования', 'Отдел аналитики', 'Служба внутреннего аудита'],
        ['3.4. Структура организации', 'Отдел планирования', 'Отдел аналитики', 'Служба внутреннего аудита', 'Отдел цифрового развития']),
    'Планирование': (
        ['4.1. Функции отдела планирования', 'Отдел планирования осуществляет подготовку сводного квартального отчета о реализации программ.', 'Отдел планирования обеспечивает мониторинг исполнения годового плана закупок.', 'Отдел планирования ведет реестр корректирующих мероприятий по замечаниям аудита.'],
        ['4.1. Функции отдела планирования', 'Отдел планирования обеспечивает мониторинг исполнения годового плана закупок.', 'Отдел планирования формирует прогноз загрузки ресурсов.']),
    'Аналитика': (
        ['5.1. Функции отдела аналитики', 'Отдел аналитики осуществляет сбор исходных данных подразделений.', 'Отдел аналитики обеспечивает проверку качества поступающих данных.'],
        ['5.1. Функции отдела аналитики', 'Отдел аналитики осуществляет сбор исходных данных подразделений.', 'Отдел аналитики обеспечивает проверку качества поступающих данных.', '5.3. Отдел аналитики осуществляет подготовку сводного квартального отчета о реализации программ.', 'Отдел аналитики обеспечивает мониторинг исполнения годового плана закупок.']),
    'Аудит': (
        ['6.1. Функции службы внутреннего аудита', 'Служба внутреннего аудита осуществляет независимую проверку исполнения плана закупок.', 'Служба внутреннего аудита направляет рекомендации по выявленным нарушениям.'],
        ['6.1. Функции службы внутреннего аудита', 'Служба внутреннего аудита осуществляет независимую проверку исполнения плана закупок.', 'Служба внутреннего аудита направляет рекомендации по выявленным нарушениям.', 'Служба внутреннего аудита согласовывает решения о выборе поставщиков по проверяемым закупкам.']),
}


def generate():
    sources = []
    for family, versions in PACKET.items():
        for index, paragraphs in enumerate(versions):
            side = 'до' if index == 0 else 'после'
            name = f'AYQYN_ПРИМЕР_{family}_{side}.docx'
            text = ['УЧЕБНЫЙ ПРИМЕР AYQYN — вымышленные документы, не нормативный акт.',
                    f'{family}. Редакция {index+1}. {side.upper()} реорганизации.'] + paragraphs
            body = ''.join('<w:p><w:r><w:t>'+escape(p)+'</w:t></w:r></w:p>' for p in text)
            with ZipFile(ROOT/'sources'/name, 'w', ZIP_DEFLATED) as archive:
                archive.writestr('[Content_Types].xml', '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
                archive.writestr('_rels/.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
                archive.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'+body+'</w:body></w:document>')
            sources.append({'name':name, 'file':'sources/'+name})
    (ROOT/'demo-sources.js').write_text('/* Fictional example documents; real parsing and analysis. */\nwindow.AYQYN_EXAMPLE_SOURCES = '+json.dumps(sources,ensure_ascii=False,indent=2)+';\n',encoding='utf-8',newline='\n')


if __name__ == '__main__':
    generate()
