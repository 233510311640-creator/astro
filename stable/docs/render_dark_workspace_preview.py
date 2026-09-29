"""Render a design reference, not a WPF execution screenshot. Requires Pillow.

This development-only renderer has no network or app integration. Windows' native
layout self-test is separate and runs in the installer before host replacement.
"""
from pathlib import Path
from xml.etree import ElementTree as ET
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
host = (ROOT / 'windows/Cypher.CorePreview/CypherCoreHost.cs').read_text(encoding='utf-8')
xaml = ET.fromstring(host.split('const string xaml = @"', 1)[1].split('";', 1)[0])
names = {e.get('{http://schemas.microsoft.com/winfx/2006/xaml}Name'): e for e in xaml.iter()}
BG = xaml.get('Background')
FG = xaml.get('Foreground')
MUTED = '#A5ADB9'
LINE = '#34373F'
FONT_ROOT = Path('/usr/share/fonts/truetype/dejavu')


def preview(width, height, approval=False):
    scale = 2
    pad, caption = 24, 70
    image = Image.new('RGB', ((width + pad * 2) * scale, (height + caption + pad) * scale), '#090A0C')
    draw = ImageDraw.Draw(image)

    def font(size, bold=False):
        return ImageFont.truetype(str(FONT_ROOT / ('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')), size * scale)

    def text(x, y, s, size=12, color=FG, bold=False):
        draw.text(((x+pad)*scale, (y+caption)*scale), s, font=font(size, bold), fill=color, anchor='lt')

    def rect(x, y, w, h, fill, border=None, radius=0):
        draw.rounded_rectangle(((x+pad)*scale, (y+caption)*scale, (x+pad+w)*scale, (y+caption+h)*scale), radius=radius*scale, fill=fill, outline=border, width=scale)

    def label(name):
        return names[name].get('Content')

    def button(x, y, w, h, name, fill='#202227', color=FG, border=LINE):
        rect(x, y, w, h, fill, border, 6)
        s=label(name)
        length=draw.textlength(s, font=font(12))/scale
        text(x+(w-length)/2, y+(h-12)/2-1, s, 12, color)

    text(0, -50, 'CYPHER / DARK WORKSPACE', 12, '#B6DCCC', True)
    text(0, -29, 'Design reference · native Windows rendering still to verify', 11, MUTED)
    rect(0, 0, width, height, BG, LINE)
    text(22, 19, 'CYPHER', 17, FG, True)
    text(22, 42, 'CORE PREVIEW 9.2.9', 10, MUTED)
    status = 'APPROVAL' if approval else 'PARTIAL'
    rect(width-230, 31, 6, 6, '#F3C969', radius=3)
    text(width-216, 28, status, 11, '#F3C969')
    text(width-128, 29, 'PIN', 10, MUTED)
    text(width-84, 26, '□', 15, MUTED)
    text(width-45, 26, '×', 15, MUTED)
    rect(22, 68, width-44, 1, '#292C32')
    text(22, 84, 'Conversation', 13, MUTED)
    text(width-232, 84, label('NewChatButton'))
    text(width-140, 84, label('CopyButton'))
    composer=height-170
    details=composer-54
    end=details-8
    if approval:
        end=composer-212
    body=Image.new('RGB', ((width-62)*scale, max(0,end-126)*scale), BG)
    bd=ImageDraw.Draw(body)
    content = (
        'RESEARCH PARTIAL · 2 source(s) read · 0 finding(s).\n\n'
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
        'retry was used.\n\nDiscovery query plan: "job autonomy" AND "task performance"\n\n'
        '6 eligible provider records remained outside local-model evidence after bounded local relevance selection.\n\n'
        'Bounded passages passing the lexical relationship preflight — S1: 0; S2: 0. '
        'These counts screen wording; they do not prove the relationship or causation.\n\n'
        'None of the selected sources’ bounded passages passed the existing lexical relationship check. '
        'Local model synthesis was skipped. This does not establish that the full papers or wider literature lack an answer.\n'
        'Diagnostic: PAPERS_DIRECT_PASSAGE_MISSING'
    )
    if approval:
        content='Preview of an action awaiting review.\n\nThe action buttons remain visible beneath the scrollable details, including at the minimum window size.'
    y=0
    for paragraph in content.split('\n'):
        line=''
        for word in paragraph.split():
            test=(line+' '+word).strip()
            if bd.textlength(test,font=font(15)) > (width-80)*scale and line:
                bd.text((0,y),line,font=font(15),fill=FG,anchor='lt');y+=22*scale;line=word
            else:line=test
        bd.text((0,y),line,font=font(15),fill=FG,anchor='lt');y+=22*scale
    image.paste(body, ((pad+24)*scale,(caption+122)*scale))
    rect(width-31, 123, 6, 86 if not approval else 25, '#535962', radius=3)
    if approval:
        text(22, composer-204, 'AWAITING APPROVAL', 11, MUTED)
        ay=composer-180
        rect(22, ay, width-44, 170, '#211E18', '#8D774C', 8)
        text(35, ay+14, 'Review this action', 13, '#ECD096', True)
        text(35, ay+43, 'Example action plan', 13)
        text(35, ay+69, 'Exact target and verification details appear here.', 12, '#C0BBAF')
        text(35, ay+93, 'Long plans scroll within this area.', 12, '#C0BBAF')
        button(width-261, ay+126, 80, 32, 'DenyApprovalButton')
        button(width-173, ay+126, 137, 32, 'ApproveOnceButton', '#293831', FG, '#698E7E')
    else:
        text(22, details+3, 'PARTIAL', 11, MUTED)
        text(22, details+27, '+  Session details', 11, MUTED)
    rect(22, composer, width-44, 138, '#17191D', LINE, 10)
    rect(35, composer+13, 61, 28, '#293831', radius=5)
    text(49, composer+21, label('AutoModeButton'), 12, '#C0E4D5')
    text(113, composer+21, label('FastModeButton'), 12, '#ADB3BD')
    text(174, composer+21, label('DeepModeButton'), 12, '#ADB3BD')
    text(width-137, composer+21, 'AUTO ROUTING', 11, MUTED)
    if not approval:
        text(39, composer+61, '│', 14, '#B6DCCC')
    button(width-115, composer+53, 80, 31, 'SendButton', '#53665E' if approval else '#B6DCCC', '#14241C', '#53665E' if approval else '#B6DCCC')
    button(width-115, composer+90, 80, 29, 'StopButton', '#202227' if approval else '#17191D', '#EDB9BD' if approval else '#766064', LINE if approval else '#282A30')
    text(24, height-18, 'Ctrl+Alt+Space to show or hide', 10, MUTED)
    text(width-292, height-18, 'Enter to send · Shift+Enter for a new line', 10, MUTED)
    return image.resize((width+pad*2,height+caption+pad),Image.Resampling.LANCZOS)


if __name__=='__main__':
    preview(1040,740).save(ROOT/'docs/cypher-dark-workspace-preview.png')
    preview(760,560,approval=True).save(ROOT/'docs/cypher-dark-workspace-minimum-preview.png')
    print('Saved two labelled design references. These are not native WPF screenshots.')
