import pathlib,tarfile,json
from PIL import Image,ImageDraw,ImageFont
p=pathlib.Path(__file__).resolve().parent
dest=p/'验收记录';dest.mkdir(exist_ok=True)
with tarfile.open(p/'验收记录.tar.gz') as t:
    for item in t.getmembers():
        path=dest/item.name
        assert path.resolve().is_relative_to(dest.resolve())
        assert item.isfile() or item.isdir(),item.name
        if item.isdir():path.mkdir(parents=True,exist_ok=True)
        else:
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(t.extractfile(item).read())
qa=dest/'final_layout_20261008/camera_qa'
r=json.loads((qa/'report.json').read_text())['records']
font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',17)
for page,start in enumerate(range(0,len(r),12),1):
    group=r[start:start+12]
    out=Image.new('RGB',(1280,((len(group)+2)//3)*265),'white');d=ImageDraw.Draw(out)
    for j,row in enumerate(group):
        im=Image.open(qa/row['images'][row['primary_camera']]);im.thumbnail((420,235))
        x=(j%3)*426;y=(j//3)*265;out.paste(im,(x,y))
        d.text((x+2,y+235),'%02d %s %s'%(row['index'],row['task'],row['primary_camera']),fill='black',font=font)
    out.save(p/('取景总览%d.jpg'%page))
print('Camera QA images:',len(r),'pairs')
