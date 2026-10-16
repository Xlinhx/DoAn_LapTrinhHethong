"""High-resolution monochrome diagrams for the academic report (not screenshots)."""
from pathlib import Path
import math
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'docs/assets/diagrams'
OUT.mkdir(parents=True,exist_ok=True)


def font(size=32,bold=False,mono=False):
    names=([r'C:\Windows\Fonts\consolab.ttf' if bold else r'C:\Windows\Fonts\consola.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'] if mono else
           [r'C:\Windows\Fonts\arialbd.ttf' if bold else r'C:\Windows\Fonts\arial.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'])
    return ImageFont.truetype(next(p for p in names if Path(p).exists()),size)


def canvas(h):
    img=Image.new('RGB',(1800,h),'white'); return img,ImageDraw.Draw(img)


def label(d,xy,t,size=32,bold=False,mono=False):
    d.multiline_text(xy,t,font=font(size,bold,mono),fill='black',spacing=14)


def rect(d,xy,t,size=32):
    d.rectangle(xy,fill='#F4F4F4',outline='black',width=3)
    x,y,xx,yy=xy; b=d.textbbox((0,0),t,font=font(size,True))
    label(d,(x+(xx-x-(b[2]-b[0]))/2,y+(yy-y-size)/2-4),t,size,True)


def arrow(d,a,b):
    d.line([a,b],fill='black',width=4); angle=math.atan2(b[1]-a[1],b[0]-a[0])
    d.polygon([b]+[(b[0]-20*math.cos(angle+i*.5),b[1]-20*math.sin(angle+i*.5)) for i in (-1,1)],fill='black')


def build_diagrams():
    img,d=canvas(520)
    for i,t in enumerate(['Phân tích CLI','Thu thập mục','Sắp xếp','Hiển thị']):
        x=35+i*445; rect(d,(x,80,x+370,200),t,35)
        if i<3: arrow(d,(x+375,140),(x+435,140))
    label(d,(55,230),'main / options',28,mono=True); label(d,(500,230),'directory',28,mono=True)
    label(d,(945,230),'sorting',28,mono=True); label(d,(1390,230),'display',28,mono=True)
    d.line([(1570,280),(1570,355),(650,355)],fill='black',width=3); arrow(d,(650,355),(650,205))
    label(d,(750,385),'-R: lặp cho từng thư mục con thật',34,True)
    label(d,(55,455),'Không theo . / .. / symlink trong bước đi xuống cây.',29)
    img.save(OUT/'diagram_1_pipeline.png')

    img,d=canvas(680)
    rect(d,(50,80,390,180),'a.txt'); rect(d,(50,240,390,340),'b.txt')
    arrow(d,(395,130),(710,180)); arrow(d,(395,290),(710,235))
    rect(d,(720,80,1280,340),'inode 42',42)
    label(d,(1350,120),'Hard link:\n2 tên, 1 inode\nst_nlink = 2',31)
    rect(d,(50,450,500,565),'link_to_a'); arrow(d,(505,505),(930,505))
    rect(d,(940,450,1580,565),'inode riêng: lưu “a.txt”',33)
    label(d,(50,610),'lstat(link) lấy chính link; stat(link) lấy đối tượng đích. Mô hình minh họa.',32)
    img.save(OUT/'diagram_2_links_inode.png')

    img,d=canvas(690)
    rect(d,(50,50,560,155),'1. demo/')
    d.line([(180,155),(180,480)],fill='black',width=3)
    for y,t in [(235,'2. .config_hidden/'),(420,'3. src_module/')]:
        d.line([(180,y+55),(350,y+55)],fill='black',width=3); rect(d,(350,y,1000,y+110),t)
    d.line([(500,530),(500,595),(640,595)],fill='black',width=3)
    label(d,(660,570),'loop_parent → ..',34,mono=True)
    rect(d,(1180,210,1730,330),'Không đi xuống',36)
    label(d,(1230,375),'.  /  ..  / symlink',34,True)
    label(d,(50,640),'Ví dụ -aR: thứ tự theo tên. Với -S, duyệt con theo size rồi tên.',32)
    img.save(OUT/'diagram_3_recursion_tree.png')

    img,d=canvas(510)
    label(d,(50,35),'Ví dụ minh họa một dòng -l (không phải log thực nghiệm)',31,True)
    fields=[('-rwsr-xr-x',390,'Loại + quyền'),('1',100,'Links'),('user',170,'Owner'),('group',190,'Group'),('29',110,'Bytes'),('Oct 16 10:00',410,'mtime'),('main.c',260,'Tên')]
    x=45
    for t,w,desc in fields:
        d.rectangle((x,135,x+w-6,225),outline='black',width=2)
        label(d,(x+12,154),t,33,True,True); d.line([(x+w/2,225),(x+w/2,280)],fill='black',width=2)
        label(d,(x+8,303),desc,27); x+=w
    label(d,(50,400),'s/S, s/S, t/T: các bit đặc biệt chồng lên vị trí execute của owner/group/other.',30)
    label(d,(50,457),'total dùng st_blocks; size dùng st_size; thiết bị hiển thị major, minor.',30)
    img.save(OUT/'diagram_4_long_format.png')


if __name__=='__main__':
    build_diagrams(); print('Generated 4 monochrome report diagrams.')
