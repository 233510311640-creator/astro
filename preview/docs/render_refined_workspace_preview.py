"""Development-only design reference. Pillow rendering is not native WPF verification.

The output uses substitute fonts. The installer separately exercises actual WPF.
No network, model calls or user content are involved.
"""
from pathlib import Path
from xml.etree import ElementTree as ET
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
host=(ROOT/'windows/Cypher.CorePreview/CypherCoreHost.cs').read_text(encoding='utf-8')
tree=ET.fromstring(host.split('const string xaml = @"',1)[1].split('";',1)[0])
names={e.get('{http://schemas.microsoft.com/winfx/2006/xaml}Name'):e for e in tree.iter()}
FONTS=Path('/usr/share/fonts/truetype/dejavu')


def render(width=1040,height=740,state='welcome'):
    k=2; pad=28; top=74
    canvas=Image.new('RGB',((width+2*pad)*k,(height+top+pad)*k),'#08080D')
    d=ImageDraw.Draw(canvas)
    def font(n,bold=False):return ImageFont.truetype(str(FONTS/('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')),int(n*k))
    def text(x,y,s,n=12,c='#F1F0F7',bold=False):d.text(((x+pad)*k,(y+top)*k),s,font=font(n,bold),fill=c,anchor='lt')
    def length(s,n=12,bold=False):return d.textlength(s,font=font(n,bold))/k
    def box(x,y,w,h,fill,outline=None,r=0):d.rounded_rectangle(((x+pad)*k,(y+top)*k,(x+pad+w)*k,(y+top+h)*k),radius=r*k,fill=fill,outline=outline,width=k)
    def line(points,c='#C0B1EC',w=1.4):d.line([((x+pad)*k,(y+top)*k) for x,y in points],fill=c,width=round(w*k),joint='curve')
    def button(x,y,w,h,name,fill='#20202D',c='#F1F0F7',outline='#353546'):
        label=names[name].get('Content')
        box(x,y,w,h,fill,outline,9);text(x+(w-length(label))/2,y+(h-12)/2-1,label,12,c)
    def wrap(x,y,s,maxw,n=15,c='#F1F0F7',lineheight=23,limit=None):
        yy=y
        for para in s.split('\n'):
            row=''
            for word in para.split():
                trial=(row+' '+word).strip()
                if length(trial,n)>maxw and row:
                    if limit is None or yy+n<=limit:text(x,yy,row,n,c)
                    yy+=lineheight;row=word
                else:row=trial
            if limit is None or yy+n<=limit:text(x,yy,row,n,c)
            yy+=lineheight
        return yy
    text(0,-51,'CYPHER / REFINED WORKSPACE',12,'#C4B6EE',True)
    text(0,-28,'Design reference · substitute font · native Windows appearance unverified',11,'#A7A4BC')
    # Opaque restrained gradient matching the native brush.
    for yy in range(height):
        ratio=yy/max(height-1,1)
        col=tuple(round(a+(b-a)*ratio) for a,b in zip((20,18,29),(13,13,20)))
        box(0,yy,width,1,col)
    d.rectangle((pad*k,top*k,(pad+width)*k,(top+height)*k),outline='#353546',width=k)
    box(28,21,34,34,'#2D263F','#5B4D80',11)
    line([(51,31),(42,31),(37,38),(42,45),(51,45)],'#D3C4FF',1.7)
    line([(42,38),(49,38)],'#D3C4FF',1.7)
    text(74,20,'Cypher',19,'#F1F0F7',True);text(74,44,'Your personal workspace',12,'#A7A4BC')
    status={'welcome':'READY','report':'PARTIAL','approval':'APPROVAL'}[state]
    sc='#4DE3C1' if state=='welcome' else '#F3C969'
    box(width-244,35,6,6,sc,r=3);text(width-230,31,status,11,sc)
    text(width-128,32,'PIN',10,'#A7A4BC');text(width-85,28,'□',15,'#A7A4BC');text(width-46,27,'×',16,'#A7A4BC')
    cw=min(900,width-56);left=(width-cw)/2
    text(left,92,'Conversation',18,'#E4E0F0',True)
    text(left+cw-153,95,names['NewChatButton'].get('Content'),12)
    text(left+cw-44,95,names['CopyButton'].get('Content'),12)
    composer=height-178
    lower=composer-58
    if state=='welcome':
        contentw=min(710,cw-20);wx=(width-contentw)/2
        wy=124+max(8,(lower-124-240)/2)
        text(wx,wy,'YOUR LOCAL WORKSPACE',11,'#B9ABDF')
        text(wx,wy+30,'Where should we begin?',34,'#F4F0FC')
        text(wx,wy+86,'Ask, research, or turn an idea into a plan.',15,'#AAA6BF')
        cardw=(contentw-20)/3;cy=wy+134
        titles=['Explore a topic','Research papers','Make a plan']
        desc=['Find a clearer picture','Look for cited evidence','Turn ideas into steps']
        for i in range(3):
            xx=wx+i*(cardw+10);box(xx,cy,cardw,116,'#191824','#323041',12)
            ix=xx+16;iy=cy+18
            if i==0:
                d.ellipse(((ix+pad)*k,(iy+top)*k,(ix+pad+22)*k,(iy+top+22)*k),outline='#C0B1EC',width=3)
                d.ellipse(((ix+pad+6)*k,(iy+top)*k,(ix+pad+16)*k,(iy+top+22)*k),outline='#C0B1EC',width=2)
                line([(ix,iy+11),(ix+22,iy+11)])
            elif i==1:
                line([(ix+4,iy),(ix+15,iy),(ix+20,iy+5),(ix+20,iy+22),(ix+4,iy+22),(ix+4,iy)])
                line([(ix+15,iy),(ix+15,iy+5),(ix+20,iy+5)])
                line([(ix+8,iy+11),(ix+16,iy+11)]);line([(ix+8,iy+16),(ix+16,iy+16)])
            else:
                for off in (0,11):
                    line([(ix,iy+off+4),(ix+3,iy+off+7),(ix+8,iy+off)])
                    line([(ix+12,iy+off+4),(ix+22,iy+off+4)])
            text(xx+16,cy+60,titles[i],13,'#F1F0F7',True)
            text(xx+16,cy+83,desc[i],12,'#A7A4BC')
    else:
        end=lower-4 if state=='report' else composer-210
        box(left,124,cw,max(45,end-124),'#11111B','#272635',14)
        report=('RESEARCH PARTIAL · 2 source(s) read · 0 finding(s).\n\n'
                'Discovery route: official OpenAlex Works API. The route permits one keyless search request. '
                'An unambiguous two-concept relationship question uses the two normalized literal concept phrases '
                'joined by a fixed Boolean AND; other questions retain the existing punctuation-safe terms. '
                'Reserved ? and * wildcard characters cannot become provider syntax; the original question remains local '
                'for selection and synthesis. Up to eight returned records are validated, then at most two are selected '
                'by bounded local question-term coverage and direct-relation signals in abstract text; provider order '
                'breaks exact score ties. Only reconstructed English abstract text is eligible evidence; titles, '
                'identifiers, ranking, citation counts, and other metadata were not used for local selection or treated '
                'as findings.\n\nAt most two eligible abstracts can enter one installed local-model synthesis. '
                'Crossref fallback was not used. No API key, authorization header, billing credential, wait, or automatic '
                'retry was used.\n\nDiscovery query plan: "job autonomy" AND "task performance"')
        if state=='approval':report='Example action awaiting your review.'
        wrap(left+20,144,report,cw-57,15,limit=end-16)
        if state=='report':box(left+cw-17,147,5,72,'#555165',r=3)
    if state=='approval':
        text(left,composer-197,'AWAITING APPROVAL',11,'#B3B1C4')
        ay=composer-170;box(left,ay,cw,160,'#211E18','#8D774C',8)
        text(left+13,ay+13,'Review this action',13,'#ECD096',True)
        text(left+13,ay+42,'Example action plan',13)
        text(left+13,ay+66,'Exact review details scroll here.',12,'#C0BBAF')
        button(left+cw-243,ay+114,80,32,'DenyApprovalButton')
        button(left+cw-155,ay+114,142,32,'ApproveOnceButton','#2D2648','#F1F0F7','#9681CD')
    else:
        text(left,lower+7,'IDLE' if state=='welcome' else 'PARTIAL',11,'#B3B1C4')
        text(left,lower+33,'+  Session details',11,'#A7A4BC')
    box(left,composer,cw,142,'#1B1929','#57486F',16)
    box(left+13,composer+13,63,29,'#2D2648',r=7)
    text(left+28,composer+22,'Auto',12,'#DAD0FF');text(left+95,composer+22,'Fast',12,'#B3B1C4');text(left+162,composer+22,'Deep',12,'#B3B1C4')
    text(left+cw-121,composer+23,'AUTO ROUTING',11,'#A7A4BC')
    text(left+17,composer+65,'Ask Cypher anything…',14,'#ABA3BF')
    button(left+cw-93,composer+57,80,31,'SendButton','#635A7B' if state=='approval' else '#BEB0FF','#1C1434','#635A7B' if state=='approval' else '#BEB0FF')
    button(left+cw-93,composer+94,80,29,'StopButton','#20202D' if state=='approval' else '#171621','#EDB9BD' if state=='approval' else '#786570','#353546' if state=='approval' else '#2A2735')
    text(24,height-20,'CORE PREVIEW 9.2.10  ·  Ctrl+Alt+Space',11,'#A7A4BC')
    hint='Enter to send · Shift+Enter for a new line';text(width-24-length(hint,11),height-20,hint,11,'#A7A4BC')
    return canvas.resize((width+2*pad,height+top+pad),Image.Resampling.LANCZOS)


if __name__=='__main__':
    render().save(ROOT/'docs/cypher-refined-workspace-preview.png')
    render(state='report').save(ROOT/'docs/cypher-refined-workspace-report.png')
    render(760,560,'approval').save(ROOT/'docs/cypher-refined-workspace-approval.png')
    print('Rendered welcome, report and minimum-size approval design references.')
