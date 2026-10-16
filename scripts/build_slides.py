"""Editable visual defense deck: 16 main slides (~18 min incl. demo), 6 backups.
Evidence comes from collect_evidence.py; render with export_office.ps1 for visual QA.
"""
from pathlib import Path
import re
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE as SH, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches as I, Pt
from pptx.oxml.ns import qn
from PIL import Image
from metadata_loader import load_project_metadata, load_test_results

ROOT=Path(__file__).resolve().parent.parent
INK,GRAY,PAPER,TEAL,PALE,WHITE,GOLD,RED='364653','5B6870','F7F3EA','456B88','E6EDF1','FFFDFA','927134','A75445'
SAGE,SOFT_SAGE,CLAY,BLUSH,LILAC,RULE='5C7359','E7EDE1','9B624B','F1E3D8','EAE6EF','D3D7D2'
ART=ROOT/'docs/assets/illustrations'
prs=Presentation(); prs.slide_width=I(13.333333); prs.slide_height=I(7.5)
meta=load_project_metadata(); data=load_test_results()


def box(s,x,y,w,h,fill=WHITE,border=None,kind=SH.RECTANGLE):
    q=s.shapes.add_shape(kind,I(x),I(y),I(w),I(h)); q.fill.solid(); q.fill.fore_color.rgb=RGBColor.from_string(fill)
    q.line.fill.background()
    style=q._element.find(qn('p:style'))
    if style is not None: q._element.remove(style)
    if border: q.line.color.rgb=RGBColor.from_string(border); q.line.width=Pt(1)
    return q


def text(s,x,y,w,h,t,size=24,c=INK,bold=False,mono=False,center=False):
    q=s.shapes.add_textbox(I(x),I(y),I(w),I(h)); f=q.text_frame; f.word_wrap=True
    f.margin_top=f.margin_left=f.margin_right=f.margin_bottom=0
    for i,row in enumerate(t.split('\n')):
        p=f.paragraphs[0] if not i else f.add_paragraph(); p.text=row
        p.font.name='Consolas' if mono else 'Segoe UI'; p.font.size=Pt(size); p.font.bold=bold
        p.font.color.rgb=RGBColor.from_string(c); p.space_after=Pt(3 if i<len(t.split('\n'))-1 else 0); p.line_spacing=1.1
        if center: p.alignment=PP_ALIGN.CENTER
    return q


def line(s,x,y,xx,yy,c=TEAL,width=2):
    q=s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,I(x),I(y),I(xx),I(yy))
    q.line.color.rgb=RGBColor.from_string(c); q.line.width=Pt(width)
    style=q._element.find(qn('p:style'))
    if style is not None: q._element.remove(style)


def arrow(s,x,y,w=.6,c=TEAL,left=False):
    box(s,x,y,w,.22,c,kind=SH.LEFT_ARROW if left else SH.RIGHT_ARROW)


def circle(s,x,y,n,d=.5,c=TEAL):
    box(s,x,y,d,d,c,kind=SH.OVAL); text(s,x,y+.055,d,.36,str(n),18,WHITE,True,center=True)


def folder(s,x,y,w=1,c=TEAL):
    box(s,x,y,w*.42,.15,c); box(s,x,y+.12,w,.58,c)


def file(s,x,y,name,w=2.5):
    box(s,x,y,w,.64,WHITE,RULE); box(s,x+.12,y+.15,.24,.32,PALE,TEAL)
    text(s,x+.46,y+.15,w-.55,.4,name,19,mono=True)


def terminal(s,x,y,w,h,cmd,rows,size=20):
    box(s,x,y,w,h,WHITE,RULE)
    box(s,x,y,w,.65,PALE)
    text(s,x+.25,y+.15,w-.5,.45,'$ '+cmd,size,TEAL,True,True)
    body=text(s,x+.25,y+.86,w-.5,h-.96,'\n'.join(rows),size,INK,mono=True)
    for p in body.text_frame.paragraphs: p.space_after=Pt(0); p.line_spacing=1.05


def art(s,name,x,y,w,h,description):
    """Contain the full generated cutout; labels and evidence stay native."""
    path=ART/f'{name}.png'
    with Image.open(path) as im: iw,ih=im.size
    scale=min(w/iw,h/ih); pw,ph=iw*scale,ih*scale
    p=s.shapes.add_picture(str(path),I(x+(w-pw)/2),I(y+(h-ph)/2),I(pw),I(ph))
    p.name='Illustration: '+name
    p._element._nvXxPr.cNvPr.set('descr','Minh họa tạo bằng imagegen: '+description+' Không phải ảnh chụp hay dữ liệu thực nghiệm.')
    return p


def new(title,sub='',tone=PAPER,backup=False):
    s=prs.slides.add_slide(prs.slide_layouts[6]); s.background.fill.solid()
    s.background.fill.fore_color.rgb=RGBColor.from_string(tone)
    if title: text(s,.82,.47,11.7,.65,title,30,INK,True)
    if sub: text(s,.85,1.24,11.6,.55,sub,18,GRAY)
    # Course and institution appear once on the cover. Sources live in notes.
    line(s,11.77,7.15,12.03,7.15,RULE,1)
    text(s,12.12,7.02,.45,.3,f'{len(prs.slides):02d}',10,GRAY,center=True)
    return s


def note(s,time,t,source='src/ và include/myls.h'):
    images=[q.name.removeprefix('Illustration: ') for q in s.shapes if q.name.startswith('Illustration: ')]
    provenance=('\nMinh họa imagegen (không phải bằng chứng): '+', '.join(images)+'. Prompt gốc: docs/assets/illustrations/manifest.json.') if images else ''
    s.notes_slide.notes_text_frame.text=f'Thời lượng: {time}.\n{t}\nNguồn: {source}'+provenance


def demo(cmd):
    m=re.search(r'^\$ '+re.escape(cmd)+r'\n(.*?)\n-> Exit code: (\d+)',data['demo_run']['raw_output'],re.M|re.S)
    if not m: raise ValueError('Missing demo command: '+cmd)
    return m.group(1).splitlines(),int(m.group(2))


# 01 — opening illustration, not an architecture claim.
s=new('',tone='F2EEE4')
text(s,.85,.62,6.5,.45,'VKU · Lập trình hệ thống',18,GRAY)
text(s,.85,1.62,4,.45,'Đề tài 17',22,CLAY,True)
text(s,.78,2.13,5.9,1.6,'myls',88,INK,True,True)
text(s,.85,3.78,5.6,1.25,'Cài đặt lệnh ls\nbằng C trên Linux',32)
for i,(f,c) in enumerate(zip(['-a','-l','-R','-S'],[TEAL,SAGE,CLAY,TEAL])):
    x=.85+i*1.28; text(s,x,5.65,1,.65,f,32,c,True,True); line(s,x,6.4,x+.72,6.4,c,2)
art(s,'filesystem_atelier',6.08,1.15,6.75,5.65,'Không gian thư mục và các đường nối phân nhánh.')
if meta['members']:
    text(s,.85,6.68,10.8,.35,', '.join(m['name'] for m in meta['members']),15,GRAY)
note(s,'30 giây','Giới thiệu ba điều cần chứng minh: hành vi đúng, hiểu giao diện hệ thống và kiểm soát tài nguyên. Hình bìa chỉ minh họa. 16 slide chính khoảng 18 phút gồm 3 phút demo; sáu slide sau là dự phòng. Metadata hiện ở chế độ '+meta['mode']+'. Chưa có danh sách nhóm thì không tự gán tên đại diện; phải bổ sung nhóm trước khi nộp.')

# 02 — four decisions.
s=new('Bốn cờ tác động lên bốn quyết định','Có 2⁴ = 16 tổ hợp, bao gồm cả chế độ mặc định.')
for i,(f,title,body,api) in enumerate([('-a','CHỌN MỤC','Thêm tên bắt đầu bằng dấu chấm','name[0]'),('-l','CHỌN CÁCH IN','Quyền · owner\nsize · mtime','struct stat'),('-R','CHỌN NƠI ĐẾN','Đi vào thư mục con thật','S_ISDIR'),('-S','CHỌN THỨ TỰ','Size giảm; cùng size thì tên','st_size')]):
    x=.85+i*3.13; c=[TEAL,SAGE,CLAY,TEAL][i]
    text(s,x,2.15,1.7,1.0,f,54,c,True,True); line(s,x,3.23,x+2.65,3.23,c,2)
    if i in (0,1):
        box(s,x+1.9,2.2,.55,.72,WHITE,c)
        for k in range(3): line(s,x+2.01,2.39+k*.13,x+2.33,2.39+k*.13,c,1)
        if not i: box(s,x+1.76,2.13,.18,.18,CLAY,kind=SH.OVAL)
    elif i==2:
        folder(s,x+1.9,2.1,.55,c); line(s,x+2.17,2.8,x+2.17,3.02,c,1.2)
        line(s,x+1.86,3.02,x+2.5,3.02,c,1.2)
    else:
        for k,w in enumerate([.72,.5,.28]): box(s,x+1.8,2.23+k*.25,w,.12,c)
    text(s,x,3.53,2.7,.6,title,19,INK,True); text(s,x,4.25,2.9,1.25,body,22); text(s,x,5.9,2.7,.45,api,18,GRAY,mono=True)
note(s,'40 giây','Giải thích theo quyết định. -a chọn tập entry; -R điều khiển đi xuống; -S đổi thứ tự; -l đổi dạng in. Không đồng nhất hiển thị tệp ẩn với duyệt đệ quy. Vì kết hợp được nên kiểm 16 tổ hợp.','src/options.c; tests/run_tests.sh, Test 01–16')

# 03 — actual output.
s=new('-a thay tập kết quả, không thay cách duyệt','Cùng một thư mục: thêm -a để thấy các tên bắt đầu bằng dấu chấm.')
a,_=demo('./myls'); b,_=demo('./myls -a')
terminal(s,.85,2.05,4.35,4.15,'./myls',a,20); terminal(s,5.48,2.05,4.35,4.15,'./myls -a',b,20)
art(s,'directory_discovery',10.05,2.16,2.55,2.65,'Kính lúp và lớp giấy mờ gợi việc nhìn thấy các mục ẩn.')
text(s,10.22,5.0,2.2,1.05,'Tên ẩn\nbắt đầu bằng .',22,CLAY,True)
text(s,.85,6.43,11.6,.5,'. và .. được in khi có -a; luôn bị loại khỏi bước đệ quy.',23,TEAL,True)
note(s,'45 giây','Chỉ vào .config_hidden, .env, . và .. ở cột phải. Nhắc rằng hiển thị và duyệt tiếp là hai quyết định. Đầu ra đọc trực tiếp từ JSON của lần chạy hiện tại, không gõ lại.','evidence/demo_session_output.txt')

# 04 — inode graph.
s=new('Tên tệp không chứa toàn bộ thông tin tệp','readdir() trả tên; lstat() lấy metadata của chính đối tượng tại đường dẫn.')
text(s,.85,2.0,3.5,.4,'MỤC TRONG THƯ MỤC',16,GRAY,True)
file(s,.85,2.85,'a.txt'); file(s,.85,4.05,'b.txt'); arrow(s,3.65,3.06,1.05); arrow(s,3.65,4.26,1.05)
box(s,5,2.7,3.55,2.45,PALE); text(s,5.25,2.95,3,.6,'inode 42',30,TEAL,True,True)
text(s,5.25,3.73,3.05,1.1,'mode · UID · GID\nsize · mtime · nlink',19,mono=True)
text(s,9,2.92,3.35,2.3,'Hai hard link\nMột inode\n\nst_nlink = 2',25)
line(s,.85,5.75,12.45,5.75,RULE,1)
text(s,.85,6.08,11.7,.55,'struct dirent: tên  →  struct stat: metadata',24,TEAL,True)
note(s,'60 giây','Hai tên cùng trỏ inode42 minh họa hard link. Inode42 không phải số đo thật. struct dirent không chứa quyền/size/owner. Phân biệt directory entry ở user space và dentry cache kernel. Không dựa riêng d_type vì có thể DT_UNKNOWN.','src/directory.c; man readdir(3), stat(2)')

# 05 — full-width pipeline.
s=new('Một pipeline cho mọi tổ hợp cờ','Thu thập → sắp xếp → in thư mục hiện tại → duyệt tiếp nếu có -R.')
for i,(title,module) in enumerate([('Đọc CLI','main + options'),('Thu thập','directory'),('Sắp xếp','sorting'),('Hiển thị','display')]):
    x=.85+i*3.12; circle(s,x+.6,2.25,i+1,.6,[TEAL,SAGE,CLAY,TEAL][i]); text(s,x,3.15,2.8,.6,title,29,INK,True)
    text(s,x,3.95,2.8,.5,module,19,GRAY,mono=True)
    if i<3: arrow(s,x+2.36,3.37,.5)
box(s,4.1,5.03,8.3,1.55,SOFT_SAGE)
line(s,11.2,4.7,11.2,5.6,SAGE); line(s,11.2,5.6,4.55,5.6,SAGE); arrow(s,4.3,5.49,.26,SAGE,left=True)
text(s,5,5.89,6.9,.6,'-R: lặp pipeline cho thư mục con thật',23,TEAL,True)
text(s,.85,6.56,11.7,.3,'Lỗi → stderr  ·  Exit status chỉ tăng mức nghiêm trọng: 0 → 1 → 2.',18,GRAY)
note(s,'60 giây','Theo dấu -alRS: getopt nhận flags; main phân loại operands; directory lọc mục/lấy metadata; sorting quyết định thứ tự; display đo cột rồi in. directory gọi lại cho thư mục con theo danh sách đã sort. Mũi tên vòng là lời gọi đệ quy, không phải vòng đọc readdir.')

# 06 — ownership.
s=new('EntryList sở hữu dữ liệu của mỗi thư mục','Không giữ con trỏ d_name qua lần readdir() kế tiếp; sao chép chuỗi vào heap.')
art(s,'memory_ownership',.75,2.05,3.5,2.7,'Khay sở hữu ba ngăn, với ba thẻ chuỗi riêng nối từ ngăn đầu.')
text(s,.95,4.95,3.3,.5,'EntryList',26,SAGE,True,True)
text(s,.95,5.47,3.4,.4,'items · count · capacity',17,GRAY,mono=True)
text(s,4.65,2.05,5,.45,'EntryList.items',21,TEAL,True,True)
for i in range(3):
    box(s,4.65+i*2.4,2.72,2.4,.95,PALE,RULE); text(s,4.84+i*2.4,3.0,2,.4,f'entry[{i}]',21,INK,True,True)
text(s,12,2.97,.45,.5,'…',25,TEAL)
# All three pointers belong to entry[0], not separate entries.
line(s,5.85,3.67,5.85,4.12); line(s,5.75,4.12,11.05,4.12)
for x,name in [(4.65,'name'),(7.3,'full_path'),(9.95,'link_target')]:
    line(s,x+1.1,4.12,x+1.1,4.62); box(s,x,4.62,2.4,.65,WHITE,RULE); text(s,x+.13,4.79,2.16,.36,name,18,mono=True)
text(s,.85,6.05,5.65,.85,'Sức chứa: 64 → 128 → 256\nKiểm tra tràn trước phép nhân/realloc.',21)
text(s,7,6.05,5.4,.85,'entry_list_free():\nGiải phóng chuỗi rồi mảng items.',21,SAGE,True)
note(s,'60 giây','Ba trường name/full_path/link_target thuộc một entry minh họa. link_target chỉ cấp phát khi symlink và cần -l. Dùng con trỏ tạm cho realloc, cleanup mọi cấp phát dở khi push thất bại. Không giữ con trỏ do readdir quản lý. Danh sách cha còn sống trong recursion, không khẳng định RAM chỉ O(depth).')

# 07 — size bars from actual demo.
s=new('-S: kích thước giảm dần, tên phá hòa','So sánh theo byte; nếu bằng nhau, so tên theo thứ tự byte.')
size_rows=[]
for row in demo('./myls -lS')[0]:
    fields=row.split()
    if len(fields)>=9 and not row.startswith('total '): size_rows.append((fields[8],int(fields[4])))
if len(size_rows)!=5: raise ValueError('Unexpected long listing fixture')
scale=max(v for _,v in size_rows)
text(s,8.08,1.9,.85,.3,'byte',16,GRAY)
for i,(name,value) in enumerate(size_rows):
    y=2.42+i*.65; text(s,.85,y+.01,2.8,.45,name,21,mono=True)
    box(s,3.75,y,max(.025,value/scale*4.02),.4,TEAL if value!=512 else CLAY)
    text(s,8.03,y-.04,.95,.45,str(value),21,INK,True,True)
art(s,'size_ordering',9.15,2.34,3.4,3.4,'Năm tập hồ sơ có kích thước giảm dần; chỉ minh họa, không biểu diễn số đo.')
text(s,.85,6.04,11.6,.9,'512 = 512 → README.txt trước notes.txt\nSo sánh > / <, tránh trừ hai kích thước gây tràn.',21,TEAL,True)
note(s,'45 giây','Độ dài thanh tuyến tính theo byte; gốc chung, không ngắt trục. Symlink chỉ10byte vì chuỗi đích, không phải size thư mục đích. Hai tệp512byte dùng strcmp phá hòa. Giá trị đọc từ log, không giả định size thư mục4096 ở mọi máy.','src/sorting.c; evidence/demo_session_output.txt')

# 08 — field dissection.
s=new('-l biến metadata thành một dòng có cấu trúc','Từng trường trả lời một câu hỏi: loại, quyền, sở hữu, kích thước, thời gian, tên.')
x=.85
for i,(token,w,label) in enumerate([('-rwsr-xr-x',2.55,'Loại + quyền'),('1',.6,'n'),('user',1.0,'Owner'),('group',1.2,'Group'),('29',.8,'Bytes'),('Oct 16 10:00',2.55,'mtime'),('main.c',1.45,'Tên')]):
    box(s,x,2.75,w,.85,[PALE,SOFT_SAGE,SOFT_SAGE,SOFT_SAGE,BLUSH,LILAC,PALE][i]); text(s,x+.07,3.01,w-.14,.45,token,22,INK,True,True)
    line(s,x+w/2,3.6,x+w/2,4.15,TEAL,1.2); text(s,x,4.32,w,.6,label,17,GRAY,center=True); x+=w+.12
text(s,.85,5.68,5.6,.95,'Hai lượt: đo độ rộng → in canh cột.\nUID/GID không có tên thì dùng số.',21)
text(s,7,5.68,5.4,.95,'s = SUID + execute của owner.\nSymlink: thêm “tên → đích”.',21,TEAL,True)
note(s,'60 giây','Dòng minh họa từng trường, không phải log thực nghiệm. Đọc từ trái qua phải: loại, quyền, hard links, owner/group, byte, mtime, tên. SUID chồng vị trí execute owner: s khi có x, S khi thiếu x. Không dùng size để tính total; total dựa st_blocks. Device dùng major/minor thay size. Phụ lục có chi tiết.','src/display.c')

# 09 — stat vs lstat.
s=new('lstat() nhìn link; stat() nhìn đối tượng đích','Trong cây -R: giữ metadata của link, không đi vào đích.',tone='EDF0E8')
art(s,'symbolic_link',.85,2.05,5.9,4.25,'Một thẻ link nối với thư mục đích bằng chuỗi giấy.')
line(s,7.15,2.18,7.15,5.77,RULE,1)
text(s,7.55,2.28,4.8,.55,'stat(link_to_src)',26,TEAL,True,True)
text(s,7.55,3.0,4.8,.95,'Metadata của\nthư mục src_module/',25)
text(s,7.55,4.35,4.8,.55,'lstat(link_to_src)',26,SAGE,True,True)
text(s,7.55,5.06,4.8,.95,'Metadata của\nchính symlink',25)
text(s,.85,6.6,11.6,.4,'Operand CLI trỏ tới thư mục: không -l → duyệt đích; có -l → in link.',20,GRAY)
note(s,'60 giây','Hai ngữ cảnh khác nhau: symlink gặp trong thư mục không theo -R; symlink là operand CLI có ngoại lệ. Không -l: main dùng stat thử phân loại link tới thư mục. Có -l giữ lstat để in link. Dangling link vẫn lstat được. Không mở rộng kết luận sang -H/-L hay trailing slash.','src/main.c; src/directory.c')

# 10 — recursion map.
s=new('-R đi theo cây thư mục thật','In thư mục hiện tại → duyệt con đã sắp xếp; không theo symlink.')
folder(s,1.7,2.15,1); text(s,2.98,2.3,3.2,.5,'demo/',29,INK,True,True); circle(s,.85,2.28,1)
line(s,2.2,2.88,2.2,5.2)
for y,title,num in [(3.45,'.config_hidden/',2),(4.67,'src_module/',3)]:
    line(s,2.2,y+.25,2.95,y+.25); folder(s,2.95,y,.75); text(s,3.95,y+.08,3.7,.5,title,25,INK,True,True); circle(s,7.85,y+.04,num)
line(s,3.325,5.37,3.325,6.1); line(s,3.325,6.1,3.9,6.1); text(s,4.13,5.85,4.5,.65,'loop_parent → ..',23,GRAY,mono=True)
art(s,'recursion_garden',8.95,1.85,3.5,2.65,'Các nhánh thư mục và một dải link rẽ ra ngoài cây.')
box(s,8.95,4.65,3.5,2.0,BLUSH)
text(s,9.2,4.86,3,.4,'DỪNG TẠI',20,CLAY,True)
for x,w,label in [(9.2,.4,'.'),(9.9,.6,'..'),(10.72,1.5,'symlink')]:
    text(s,x,5.42,w,.5,label,22,INK,True,True)
for x in (9.72,10.55): line(s,x,5.45,x,5.85,'D8C6B9',1)
text(s,9.2,6.02,3,.5,'Với -aR: in, không đi vào.',17,GRAY)
note(s,'65 giây','Thứ tự1/2/3 minh họa -aR theo tên. Khi có -S thứ tự con lấy theo size rồi tên. .config_hidden được thăm vì -a. loop_parent dừng vì lstat nhận là link. Không tuyên bố chặn mọi vòng lặp: bind mount chưa có kiểm tra cặp st_dev/st_ino.','src/directory.c, process_directory()')

# 11 — FD lifetime.
s=new('Đóng DIR* trước khi gọi đệ quy','Giảm descriptor đang mở; dữ liệu cha vẫn còn trong bộ nhớ.')
for i,label in enumerate(['Cha','Con','Cháu']):
    y=2.4+i*1.05; x=2.5+i*2.7; text(s,.85,y,1.4,.5,label,24,INK,True)
    box(s,x-.16,y-.13,3.32,.76,WHITE)
    box(s,x,y,.92,.48,SOFT_SAGE); text(s,x+.05,y+.08,.84,.32,'open',16,SAGE,True,True)
    line(s,x+.92,y+.24,x+2.05,y+.24,TEAL,3); box(s,x+2.05,y,.95,.48,BLUSH); text(s,x+2.09,y+.08,.88,.32,'close',16,CLAY,True,True)
    if i<2: line(s,x+2.53,y+.5,x+2.7,y+1.05,RULE,1.5)
text(s,.85,6.0,5.5,.85,'FD: không giữ DIR* theo mỗi độ sâu.\nStack lời gọi: vẫn tăng theo độ sâu.',21)
text(s,7,6.0,5.4,.85,'RAM: tổng EntryList còn sống\ntrên nhánh, cộng chuỗi đường dẫn.',21,TEAL,True)
note(s,'45 giây','Phân biệt descriptor kernel, stack lời gọi và heap dữ liệu. closedir sau thu thập, trước gọi con. Không có đồng thời một DIR mở cho mỗi tổ tiên, nhưng EntryList tổ tiên vẫn cần để tiếp tục duyệt anh em. Không khẳng định O(1) RAM hay độ sâu không giới hạn.')

# 12 — errors and genuine mixed-operand output.
s=new('Báo lỗi nhưng vẫn xử lý operand hợp lệ','Mã thoát giữ mức nghiêm trọng cao nhất đã gặp.')
for i,(n,title,desc,c) in enumerate([('0','Hoàn tất','Không ghi nhận lỗi',TEAL),('1','Lỗi khi duyệt','Entry / thư mục con',GOLD),('2','Lỗi\nnghiêm trọng','CLI · bộ nhớ · stdout',RED)]):
    x=.85+i*4.05; box(s,x,2.08,.95,.95,[PALE,SOFT_SAGE,BLUSH][i],kind=SH.OVAL)
    text(s,x,2.11,.95,.85,n,44,c,True,True,True); text(s,x+1.15,2.25,2.65,.9,title,24,INK,True); text(s,x,3.4,3.8,.8,desc,21,GRAY)
err,rc=demo('./myls missing_path.txt src_module')
terminal(s,.85,4.32,11.58,2.2,'./myls missing_path.txt src_module',[r for r in err if r.strip()][:4],17)
text(s,.85,6.64,11.6,.3,f'Demo trả exit {rc}; lỗi ghi stderr, kết quả hợp lệ ghi stdout.',18,TEAL,True)
note(s,'45 giây','elevate_status dùng max nên không hạ lỗi trước đó. Khung minh chứng gộp hai luồng để đọc, chương trình thật tách stdout và stderr. Log thật có thể hiện stderr trước stdout do buffering. Không so nguyên chuỗi lỗi phụ thuộc locale, kiểm rc và sự hiện diện stderr.','include/myls.h; evidence/demo_session_output.txt')

# 13 — coverage, honest categories.
s=new('Kiểm chứng cả hành vi lẫn đường lỗi','26 ca đối chiếu GNU ls · 11 ca kiểm hợp đồng, helper và lỗi giả lập.')
reg,san=data['regular_suite'],data['sanitizer_suite']
for x,suite,label in [(.85,reg,'Bản thường'),(4.9,san,'ASan + UBSan + LSan')]:
    text(s,x,2.35,3.65,1.05,f"{suite['passed']} / {suite['total']}",49,TEAL,True); text(s,x,3.56,3.7,.7,label,22,INK,True)
art(s,'testing_workbench',8.85,2.02,3.55,2.5,'Bàn kiểm thử với laptop và checklist; số liệu kết quả là text thật trên slide.')
x=.85
for count,label,c in [(16,'Tổ hợp 4 cờ',TEAL),(10,'GNU: ca biên',SAGE),(11,'Hợp đồng / fault / unit',CLAY)]:
    w=11.58*count/37; box(s,x,4.87,w,.75,c); text(s,x+.14,5.07,w-.28,.4,str(count),23,WHITE,True)
    text(s,x,5.89,w-.1,.65,label,19,INK,True); x+=w
text(s,.85,6.69,11.6,.32,f"Bản thường / sanitizer: FAIL {reg['failed']} / {san['failed']} · SKIP {reg['skipped']} / {san['skipped']}",16,GRAY)
note(s,'60 giây','Không nói cả37ca đều diff GNU: 16tổ hợp+10ca biên differential;11ca gồm helper và lỗi giả lập. Source hash ràng buộc JSON với source/tests. Các ca lỗi gồm readdir/readlink/closedir/realloc và /dev/full. Không suy không còn bug từ suite hoặc sanitizer PASS.','tests/run_tests.sh; tests/test_internals.c; tests/fault_inject.c; evidence/test_results.json')

# 14 — live demo score.
s=new('Demo: bốn thay đổi có thể quan sát','Mục ẩn → thứ tự → đệ quy → xử lý lỗi.',tone='EDF0E8')
art(s,'live_terminal',.65,2.12,3.7,3.8,'Trạm terminal dành cho phần chạy demo trực tiếp.')
text(s,1.02,6.02,3,.5,'make demo',27,SAGE,True,True)
for i,(cmd,watch) in enumerate([('./myls → ./myls -a','Xuất hiện mục ẩn, . và ..'),('./myls -lS','Size giảm; hai tệp 512 byte phá hòa theo tên'),('./myls -alRS','Vào thư mục ẩn, không theo link tới ..'),('./myls missing_path.txt src_module','Có lỗi, vẫn in operand hợp lệ; exit 2')]):
    y=2.08+i*1.13; circle(s,4.65,y,i+1,.44,[TEAL,SAGE,CLAY,TEAL][i]); text(s,5.34,y-.02,7.12,.5,cmd,22,INK,True,True)
    text(s,5.34,y+.55,7.12,.46,watch,20,GRAY)
    if i<3: line(s,5.34,y+1.0,12.44,y+1.0,RULE,1)
note(s,'3 phút','Chuyển terminal chạy make demo. Fixture nằm trong /tmp để tách khỏi quyền của ổ Windows. Không đọc mọi dòng. Dừng ở SUID main.c và loop_parent để giải thích. Nếu terminal trục trặc dùng log evidence/demo_session_output.txt và nói rõ đó là log đã thu, không giả là đang chạy trực tiếp.','tests/run_demo.sh')

# 15 — scope boundaries, three rows.
s=new('Phạm vi rõ giúp đánh giá kết quả đúng','Tái hiện bốn cờ trong hợp đồng đã công bố; vẫn có khác biệt với GNU ls.')
for i,(label,yes,no) in enumerate([('HIỂN THỊ','Một tên mỗi dòng; LC_ALL=C, so tên theo byte.','Chưa có nhiều cột, màu, quoting ký tự điều khiển.'),('METADATA','Quyền Unix, link, device, size, time và total.','Chưa có ACL/SELinux; phụ thuộc metadata filesystem.'),('DUYỆT CÂY','Bỏ . / ..; không theo symlink khi đi xuống.','Chưa có tập tổ tiên (st_dev, st_ino) để chặn vòng bind mount.')]):
    y=2.05+i*1.43; c=[TEAL,SAGE,CLAY][i]
    box(s,.85,y,.07,1.02,c); text(s,1.1,y,2.15,.55,label,21,c,True); text(s,3.4,y,8.92,.6,yes,22,INK,True); text(s,3.4,y+.65,8.92,.65,no,20,GRAY)
    if i<2: line(s,3.4,y+1.21,12.42,y+1.21,RULE,1)
note(s,'45 giây','Nêu giới hạn chủ động. Không nói tương đương toàn bộ GNU. DrvFs phụ thuộc cấu hình metadata, không phải WSL luôn0777. Chưa an toàn trước mọi thay đổi cây đồng thời. Ưu tiên nâng cấp cycle detection, họ hàm *at và hiển thị tên an toàn thay vì thêm cờ lạc đề.')

# 16 — finish.
s=new('Từ một lệnh quen thuộc đến cơ chế hệ thống',tone='F2EEE4')
text(s,.85,1.73,7.2,1.65,'Đọc đúng. In đúng.\nGiải phóng đúng.',42,INK,True)
art(s,'closing_archive',7.85,2.1,4.75,4.45,'Tập hồ sơ, sách và kính lúp kết lại việc tìm hiểu và kiểm chứng chương trình.')
for i,(title,body) in enumerate([('HÀNH VI','4 cờ, 16 tổ hợp, cả ca lỗi'),('CƠ CHẾ','dirent · stat · heap · descriptor'),('KIỂM CHỨNG','GNU ls + sanitizer + fault injection')]):
    y=3.75+i*.86; c=[TEAL,SAGE,CLAY][i]
    line(s,.85,y-.12,7.68,y-.12,RULE,1); text(s,.85,y,2.2,.5,title,18,c,True); text(s,3.1,y,4.6,.72,body,21,INK)
text(s,.85,6.64,7,.4,'Trao đổi & câu hỏi',22,TEAL)
note(s,'30 giây','Kết bằng ba năng lực: tái hiện hành vi, lý giải cơ chế, đưa bằng chứng chạy lại được. Không thêm số đo hay tính năng mới ở trang kết. Dùng phụ lục đúng chủ đề khi có câu hỏi.')


def grid(s,headers,rows,widths,y=2.1,rowh=.9):
    x=.85
    for j,w in enumerate(widths):
        box(s,x,y,w,.7,PALE); text(s,x+.18,y+.18,w-.36,.42,headers[j],21,INK,True)
        for i,row in enumerate(rows):
            yy=y+.7+i*rowh; box(s,x,yy,w,rowh,WHITE if not i%2 else SOFT_SAGE); text(s,x+.14,yy+.22,w-.28,rowh-.25,row[j],21)
        x+=w


s=new('Quyền đặc biệt thay ký tự execute thế nào?','Tệp mẫu main.c được chmod 4755 trong demo.',backup=True)
grid(s,['Bit đặc biệt','Vị trí','Có x','Không có x'],[['SUID','owner','s','S'],['SGID','group','s','S'],['Sticky','other','t','T']],[3.65,2.5,2.5,2.9])
text(s,.85,6.0,11.6,.85,'04755 → -rwsr-xr-x\nDùng mask S_ISUID / S_ISGID / S_ISVTX và các bit quyền.',22,TEAL,True)
note(s,'Dự phòng','Sticky trên thư mục hạn chế xóa/đổi tên entry. SUID executable liên quan quyền thực thi, không phải quyền đọc. SGID thư mục thường cho entry mới kế thừa group. Chỉ format mask, không khẳng định filesystem nào cũng thực thi các bit.','src/display.c, format_mode_string()')

s=new('Size, total và thời gian là ba khái niệm khác nhau',backup=True)
for i,(title,body) in enumerate([('st_size','Byte logic của một đối tượng'),('st_blocks','Số khối 512 byte đã cấp phát'),('st_mtime','Lần sửa nội dung gần nhất')]):
    x=.85+i*4.05; circle(s,x,2.22,i+1); text(s,x+.7,2.2,2.9,.55,title,26,INK,True,True); text(s,x,3.18,3.65,1,body,24,GRAY)
box(s,.85,4.55,11.55,1.42,PALE); text(s,1.15,4.9,10.95,.7,'total (1 KiB) = (Σ st_blocks + 1) / 2',30,INK,True,True)
text(s,.85,6.25,11.6,.5,'Gần hiện tại: HH:MM; quá nửa năm hoặc ở tương lai: năm. Test cố định TZ=UTC0.',20,GRAY)
note(s,'Dự phòng','total dùng phép chia nguyên làm tròn lên và các entry được chọn. Sparse file cho thấy st_size không phải allocated bytes. Device hiển thị major/minor. Mốc nửa năm theo code hiện tại, không hỗ trợ TIME_STYLE env.','src/display.c')

s=new('Symlink: phân biệt CLI với mục khi duyệt',backup=True)
grid(s,['Ngữ cảnh','Không -l','Có -l'],[['Link → thư mục, operand CLI','Liệt kê nội dung đích','In chính link'],['Link đứt, operand CLI','In tên link','In link → chuỗi đích'],['Link gặp trong thư mục -R','Chỉ in tên;\nkhông đệ quy','In link;\nkhông đi xuống']],[5.05,3.1,3.43],rowh=1.05)
text(s,.85,6.4,11.6,.5,'-R không biến symlink bên trong cây thành cạnh đệ quy.',23,TEAL,True)
note(s,'Dự phòng','Bảng giới hạn operand không trailing slash, bốn cờ hỗ trợ. -H/-L và các biến thể trailing slash nằm ngoài phạm vi kiểm chứng.','src/main.c; tests/run_tests.sh')

s=new('Fault injection làm đường lỗi có thể tái lập','LD_PRELOAD ép một số lời gọi thất bại theo điều kiện; kiểm cách xử lý của chương trình.',backup=True)
for i,(name,result) in enumerate([('readdir / closedir','Báo lỗi; giữ mức exit phù hợp'),('readlink / realloc','Dọn dữ liệu dở; không crash'),('/dev/full (stdout)','Phát hiện lỗi ghi và flush; exit 2')]):
    y=2.2+i*1.28; c=[TEAL,SAGE,CLAY][i]
    box(s,.85,y,4.1,.75,[PALE,SOFT_SAGE,BLUSH][i]); text(s,1.05,y+.2,3.7,.42,name,23,c,True,True); arrow(s,5.23,y+.25,.8,c); text(s,6.4,y+.05,5.95,.8,result,23)
text(s,.85,6.43,11.6,.4,'Helper nội bộ: bit quyền, device, total, overflow; cũng được build với sanitizer.',19,TEAL,True)
note(s,'Dự phòng','Fault injection ép đường lỗi có điều kiện, không mô phỏng đầy đủ lỗi thiết bị vật lý. Test scan cả diagnostics trong stderr đã thu. Helper không thay source production.','tests/fault_inject.c; tests/test_internals.c')

s=new('Chạy trên WSL: chọn đúng nơi tạo fixture',backup=True)
for x,c,title,body in [(.85,SAGE,'/tmp · Linux filesystem','Fixture tự động ở đây.\nchmod, symlink và special bits\nđược thử trên môi trường Linux.'),(7,TEAL,'/mnt/p · ổ Windows','Có thể lưu và build repo.\nQuyền phụ thuộc DrvFs,\nmount options và metadata.')]:
    box(s,x+.1,2.04,2.6,.9,SOFT_SAGE if x<2 else PALE)
    folder(s,x+.35,2.13,1.4,c)
    box(s,x+2.0,2.2,.4,.52,WHITE,c); line(s,x+1.25,2.72,x+1.91,2.72,c,1.2)
    text(s,x,3.4,5.4,.65,title,28,c,True); text(s,x,4.35,5.4,1.6,body,24)
text(s,.85,6.4,11.6,.5,'Không kết luận “WSL luôn hiện 0777”; kiểm mount và cấu hình máy đang chạy.',21,GRAY)
note(s,'Dự phòng','Không tự sửa wsl.conf. Dùng /tmp cho test quyền; ca skip phải được ghi rõ.','https://learn.microsoft.com/en-us/windows/wsl/file-permissions')

s=new('Đọc tiếp và tái lập từ đúng nguồn','README để chạy; tài liệu kỹ thuật để học; log để kiểm chứng.',backup=True)
for i,(title,path,body) in enumerate([('Chạy chương trình','README.md','Build · test · sanitizer · demo'),('Hiểu triển khai','docs/TECHNICAL_DEEP_DIVE.md','Khái niệm → trace → cờ → tài nguyên → lỗi'),('Xem minh chứng','evidence/test_results.json','Môi trường · source hash · từng ca · demo')]):
    y=2.15+i*1.25; c=[TEAL,SAGE,CLAY][i]
    text(s,.85,y+.02,.55,.6,f'{i+1:02d}',22,c,True,True); text(s,1.6,y,3.08,.6,title,24,c,True); text(s,4.98,y,7.4,.48,path,21,INK,True,True); text(s,4.98,y+.56,7.4,.5,body,20,GRAY)
text(s,.85,6.15,11.6,.75,'Tham chiếu: GNU Coreutils (ls) · Linux man-pages (stat, readdir, readlink) · Microsoft Learn (WSL).',18,GRAY)
note(s,'Dự phòng','Một thư mục: thu thập/đo cột O(N), sort thường O(N log N) với qsort đang sử dụng; chuẩn C không cam kết độ phức tạp qsort. Đệ quy giữ tổng EntryList trên nhánh cùng stack. Các URL sau xác minh semantics; repo xác định hành vi cài đặt.','https://www.gnu.org/software/coreutils/manual/html_node/ls-invocation.html ; https://man7.org/linux/man-pages/man2/stat.2.html ; https://man7.org/linux/man-pages/man3/readdir.3.html')

assert len(prs.slides)==22
prs.core_properties.title='myls — Đề tài 17, Lập trình hệ thống VKU'
prs.core_properties.subject='16 slide chính + 6 phụ lục; khoảng 18 phút gồm demo'
prs.core_properties.author=', '.join(m['name'] for m in meta['members']) or 'Nhóm đồ án — chờ danh sách thành viên'
out=ROOT/'docs/Slides.pptx'; prs.save(out)
print(f'Generated {out}: 22 slides. Render and inspect before delivery.')
