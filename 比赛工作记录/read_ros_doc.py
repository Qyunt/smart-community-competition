from zipfile import ZipFile
from lxml import etree
from pathlib import Path

src = Path('F:/qq文件/ROS基础实验.docx')
ns = {'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main', 'a':'http://schemas.openxmlformats.org/drawingml/2006/main', 'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
with ZipFile(src) as z:
    root=etree.fromstring(z.read('word/document.xml'))
    lines=[]
    for i,p in enumerate(root.xpath('//w:body//w:p', namespaces=ns)):
        text=''.join(p.xpath('.//w:t/text()', namespaces=ns))
        images=p.xpath('.//a:blip/@r:embed', namespaces=ns)
        if text or images:
            lines.append(f'{i:04d} {text}' + (' [IMAGES: '+','.join(images)+']' if images else ''))
    Path('ros-document-text.txt').write_text('\n'.join(lines),encoding='utf-8')
    print('\n'.join(lines[:300]))
