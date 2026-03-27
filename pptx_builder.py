"""
UKLC Purpose Lesson PPTX Builder — v3
Uses unpack/add_slide/pack scripts. Pure XML, no python-pptx shape API.

Visual style: white background, text in rounded-rect boxes, UKLC brand colours.
Slide count: 15-20 student slides per lesson.
"""
import io, os, re, subprocess, tempfile

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts')

# ── Brand hex colours (no #) ──────────────────────────────────────────────────
NAVY   = '1C3048'
YELLOW = 'E9EA7E'
PURPLE = '7030A0'
RED    = 'EC273B'
WHITE  = 'FFFFFF'
LIGHT  = 'E6EEF3'
PINK   = 'FAD7D8'
GREY   = 'AAAAAA'
DGREY  = '444444'

W = 12192000  # slide width  EMU
H = 6858000   # slide height EMU

ACCENTS = {
    'hook': NAVY, 'debate': NAVY,
    'vocab_intro': PURPLE, 'vocab_practice': PURPLE, 'grammar_focus': PURPLE,
    'discussion': RED,
    'reading': NAVY, 'info': NAVY, 'listening': NAVY,
    'task_setup': RED, 'task_content': RED, 'roleplay': PINK,
    'writing': LIGHT,
    'game': YELLOW, 'reflection': YELLOW,
    'quiz': PURPLE, 'matching': PURPLE, 'gap_fill': PURPLE,
    'pair_work': RED, 'group_work': RED,
}

# ── XML helpers ────────────────────────────────────────────────────────────────

def _esc(t):
    return (str(t)
        .replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
        .replace('\u2018',"'").replace('\u2019',"'")
        .replace('\u201c','"').replace('\u201d','"')
        .replace('\u2013','-').replace('\u2014','--')
        .replace('\u2026','...')
    )

def _fill(hex_colour):
    return f'<a:solidFill><a:srgbClr val="{hex_colour}"/></a:solidFill>'

def _rpr(sz, bold=False, colour=NAVY, italic=False):
    b = ' b="1"' if bold else ''
    i = ' i="1"' if italic else ''
    return (f'<a:rPr lang="en-GB" sz="{sz}"{b}{i} dirty="0">'
            f'{_fill(colour)}'
            f'<a:latin typeface="Calibri" pitchFamily="0" charset="0"/>'
            f'</a:rPr>')

def _para(text, sz, bold=False, colour=NAVY, align='l', italic=False, space_after=0):
    spc = f'<a:spcAft><a:spcPts val="{space_after}"/></a:spcAft>' if space_after else ''
    return (f'<a:p>'
            f'<a:pPr algn="{align}">{spc}</a:pPr>'
            f'<a:r>{_rpr(sz,bold,colour,italic)}<a:t>{_esc(text)}</a:t></a:r>'
            f'</a:p>')

def _empty_para():
    return '<a:p><a:endParaRPr lang="en-GB" dirty="0"/></a:p>'


# ── Shape builders (return XML strings) ──────────────────────────────────────

_sid = [100]
def _nid():
    v = _sid[0]; _sid[0] += 1; return v

def _rect(x, y, cx, cy, fill, line_colour=None):
    ln = (f'<a:ln><a:solidFill><a:srgbClr val="{line_colour}"/></a:solidFill></a:ln>'
          if line_colour else '<a:ln><a:noFill/></a:ln>')
    return (f'<p:sp><p:nvSpPr>'
            f'<p:cNvPr id="{_nid()}" name="r"/>'
            f'<p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
            f'<p:spPr>'
            f'<a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
            f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>{_fill(fill)}{ln}'
            f'</p:spPr>'
            f'<p:txBody><a:bodyPr rtlCol="0" anchor="ctr"/><a:lstStyle/>{_empty_para()}</p:txBody>'
            f'</p:sp>')

def _rrect(x, y, cx, cy, fill, line_colour=None, radius=40000):
    ln = (f'<a:ln><a:solidFill><a:srgbClr val="{line_colour}"/></a:solidFill></a:ln>'
          if line_colour else '<a:ln><a:noFill/></a:ln>')
    return (f'<p:sp><p:nvSpPr>'
            f'<p:cNvPr id="{_nid()}" name="rr"/>'
            f'<p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
            f'<p:spPr>'
            f'<a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
            f'<a:prstGeom prst="roundRect">'
            f'<a:avLst><a:gd name="adj" fmla="val {radius}"/></a:avLst>'
            f'</a:prstGeom>{_fill(fill)}{ln}'
            f'</p:spPr>'
            f'<p:txBody><a:bodyPr rtlCol="0" anchor="ctr"/><a:lstStyle/>{_empty_para()}</p:txBody>'
            f'</p:sp>')

def _txbox(x, y, cx, cy, paragraphs_xml):
    """Text box with correct OOXML bodyPr."""
    return (f'<p:sp><p:nvSpPr>'
            f'<p:cNvPr id="{_nid()}" name="t"/>'
            f'<p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
            f'<p:spPr>'
            f'<a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
            f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/>'
            f'</p:spPr>'
            f'<p:txBody>'
            f'<a:bodyPr wrap="square" rtlCol="0"><a:spAutoFit/></a:bodyPr>'
            f'<a:lstStyle/>'
            f'{paragraphs_xml}'
            f'</p:txBody></p:sp>')

def _label_box(x, y, cx, cy, fill, paras_xml, line_colour=None):
    """Rounded rect WITH text content inside — matches real UKLC lesson style."""
    ln = (f'<a:ln><a:solidFill><a:srgbClr val="{line_colour}"/></a:solidFill></a:ln>'
          if line_colour else '<a:ln><a:noFill/></a:ln>')
    return (f'<p:sp><p:nvSpPr>'
            f'<p:cNvPr id="{_nid()}" name="lb"/>'
            f'<p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
            f'<p:spPr>'
            f'<a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
            f'<a:prstGeom prst="roundRect">'
            f'<a:avLst><a:gd name="adj" fmla="val 40000"/></a:avLst>'
            f'</a:prstGeom>{_fill(fill)}{ln}'
            f'</p:spPr>'
            f'<p:txBody>'
            f'<a:bodyPr rtlCol="0" anchor="ctr"/>'
            f'<a:lstStyle/>{paras_xml}</p:txBody></p:sp>')

def _txt(x, y, cx, cy, text, sz=1400, bold=False, colour=NAVY, align='l', italic=False):
    if not text: return ''
    lines = str(text).split('\n')
    paras = ''.join(_para(ln, sz, bold, colour, align, italic) for ln in lines)
    return _txbox(x, y, cx, cy, paras)

def _txt_in_box(x, y, cx, cy, text, sz=1400, bold=False,
                txt_colour=NAVY, fill=WHITE, align='l', line_colour=None):
    """Text inside a rounded rect box — the signature PURPOSE style."""
    lines = [l for l in str(text).split('\n')]
    paras = ''.join(_para(ln, sz, bold, txt_colour, align) for ln in lines)
    return _label_box(x, y, cx, cy, fill, paras, line_colour)

def _badge(x, y, num, fill):
    paras = _para(str(num), 1500, bold=True, colour=WHITE, align='ctr')
    return (f'<p:sp><p:nvSpPr>'
            f'<p:cNvPr id="{_nid()}" name="badge"/>'
            f'<p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
            f'<p:spPr>'
            f'<a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="320000" cy="320000"/></a:xfrm>'
            f'<a:prstGeom prst="ellipse"><a:avLst/></a:prstGeom>{_fill(fill)}'
            f'<a:ln><a:noFill/></a:ln></p:spPr>'
            f'<p:txBody><a:bodyPr rtlCol="0" anchor="ctr"/><a:lstStyle/>{paras}</p:txBody>'
            f'</p:sp>')

def _slide_wrap(shapes):
    return (f'<?xml version="1.0" encoding="utf-8"?>'
            f'<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
            f' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
            f' xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
            f'<p:cSld><p:spTree>'
            f'<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
            f'<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>'
            f'<a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
            f'{"".join(shapes)}'
            f'</p:spTree></p:cSld>'
            f'<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>')


# ── Common slide chrome ────────────────────────────────────────────────────────

def _header_bar(shapes, title, accent):
    """Navy/accent top bar with white title — the UKLC header."""
    shapes.append(_rect(0, 0, W, 760000, accent))
    shapes.append(_txt(280000, 80000, W-400000, 600000,
                       title, sz=2800, bold=True, colour=WHITE))

def _footer_bar(shapes, colour=YELLOW):
    shapes.append(_rect(0, H-180000, W, 180000, colour))

def _img_hint(shapes, img, y=H-480000):
    if img:
        shapes.append(_txt(380000, y, 8000000, 260000,
                           f'[IMAGE: {img}]', sz=800, colour=GREY))

def _activity_box(shapes, act, y=H-720000):
    if act:
        shapes.append(_txt_in_box(380000, y, W-760000, 480000,
                                  f'\U0001f4ac  {act}',
                                  sz=1300, bold=True, txt_colour=NAVY,
                                  fill=LIGHT))


# ── Slide layout builders ──────────────────────────────────────────────────────

def _gen_slide_xml(sd, lesson_type='LANG'):
    _sid[0] = 100  # reset ID counter per slide
    stype  = sd.get('slide_type', 'info')
    title  = sd.get('title', '')
    body   = sd.get('content', '')
    act    = sd.get('activity_instruction', '')
    img    = sd.get('image_placeholder', '')
    accent = ACCENTS.get(stype, NAVY)
    shapes = []

    # White background on all slides
    shapes.append(_rect(0, 0, W, H, WHITE))

    if stype in ('hook',):
        _build_hook(shapes, title, body, act, img)
    elif stype == 'debate':
        _build_debate(shapes, title, body, act, img)
    elif stype in ('game', 'quiz'):
        _build_game(shapes, title, body, act, img, accent)
    elif stype == 'reflection':
        _build_reflection(shapes, title, body, act, img)
    elif stype in ('vocab_intro', 'vocab_practice', 'grammar_focus', 'matching', 'gap_fill'):
        _build_vocab(shapes, title, body, act, img, accent)
    elif stype == 'discussion':
        _build_discussion(shapes, title, body, act, img)
    elif stype in ('pair_work', 'group_work', 'roleplay'):
        _build_task(shapes, title, body, act, img, accent)
    elif stype == 'reading':
        _build_reading(shapes, title, body, act, img)
    elif stype == 'video_placeholder':
        _build_video_placeholder(shapes, title, body)
    elif stype == 'answers_hidden':
        _build_answers_hidden(shapes, title, body)
    elif stype in ('info', 'listening', 'writing', 'task_setup', 'task_content'):
        _build_standard(shapes, title, body, act, img, accent)
    else:
        _build_standard(shapes, title, body, act, img, accent)

    return _slide_wrap(shapes)


def _build_hook(shapes, title, body, act, img):
    """Full-width image placeholder with title overlay at bottom."""
    # Dark overlay bar at bottom
    shapes.append(_rect(0, H-2200000, W, 2200000, NAVY))
    # Large image area
    shapes.append(_txt(380000, 200000, W-760000, H-2400000,
                       f'[IMAGE: {img or title}]', sz=1100, colour=GREY, align='ctr'))
    # Title in overlay
    shapes.append(_txt(280000, H-2100000, W-560000, 700000,
                       title, sz=3200, bold=True, colour=YELLOW))
    if body:
        shapes.append(_txt(280000, H-1350000, W-560000, 900000,
                           body, sz=1700, colour=WHITE))
    if act:
        shapes.append(_txt_in_box(280000, H-380000, W-560000, 340000,
                                  act, sz=1300, bold=True,
                                  txt_colour=NAVY, fill=YELLOW))


def _build_debate(shapes, title, body, act, img):
    """Split screen: two columns for debate positions."""
    _header_bar(shapes, title, NAVY)
    _footer_bar(shapes, YELLOW)
    lines = [l.strip() for l in body.split('\n') if l.strip()]
    # Find the split point — look for Group A / Group B
    mid = len(lines) // 2
    for i, l in enumerate(lines):
        if 'Group B' in l or 'DISAGREE' in l:
            mid = i; break
    left  = '\n'.join(lines[:mid])
    right = '\n'.join(lines[mid:])
    shapes.append(_txt_in_box(200000, 860000, 5750000, H-1240000,
                               left, sz=1500, txt_colour=WHITE, fill=NAVY))
    shapes.append(_txt_in_box(6240000, 860000, 5750000, H-1240000,
                               right, sz=1500, txt_colour=NAVY, fill=LIGHT,
                               line_colour=NAVY))
    _img_hint(shapes, img)
    _activity_box(shapes, act)


def _build_game(shapes, title, body, act, img, accent):
    """Bold title top, game content in cards below."""
    shapes.append(_rect(0, 0, W, 1800000, accent))
    tc = NAVY if accent == YELLOW else WHITE
    shapes.append(_txt(200000, 150000, W-400000, 1500000,
                       title, sz=3600, bold=True, colour=tc, align='ctr'))
    _footer_bar(shapes, NAVY if accent == YELLOW else YELLOW)
    if body:
        lines = [l.strip() for l in body.split('\n') if l.strip()]
        y = 1950000
        for line in lines[:8]:
            shapes.append(_txt_in_box(380000, y, W-760000, 440000,
                                       line, sz=1500, txt_colour=NAVY, fill=LIGHT))
            y += 500000
    _img_hint(shapes, img)
    _activity_box(shapes, act)


def _build_reflection(shapes, title, body, act, img):
    """Warm yellow accent, reflection prompts in boxes."""
    shapes.append(_rect(0, 0, W, 900000, YELLOW))
    shapes.append(_txt(200000, 100000, W-400000, 700000,
                       title, sz=3200, bold=True, colour=NAVY, align='ctr'))
    _footer_bar(shapes, NAVY)
    lines = [l.strip() for l in body.split('\n') if l.strip()]
    y = 1050000
    for line in lines[:5]:
        shapes.append(_txt_in_box(380000, y, W-760000, 500000,
                                   line, sz=1600, txt_colour=NAVY, fill=LIGHT))
        y += 600000
    _img_hint(shapes, img)
    _activity_box(shapes, act)


def _build_vocab(shapes, title, body, act, img, accent):
    """Two-column card grid for vocabulary."""
    _header_bar(shapes, title, accent)
    _footer_bar(shapes)
    lines = [l.strip() for l in body.split('\n') if l.strip()]
    rows  = max((len(lines)+1)//2, 1)
    ch    = min(860000, max(480000, (H-1200000)//rows))
    cw    = 5700000
    cg    = 200000
    for idx, line in enumerate(lines[:10]):
        col, row = idx % 2, idx // 2
        x = 200000 + col*(cw+cg)
        y = 870000 + row*(ch+80000)
        fill = LIGHT if col == 0 else PINK
        shapes.append(_txt_in_box(x, y, cw, ch, line,
                                   sz=1300, txt_colour=NAVY, fill=fill))
    _img_hint(shapes, img)
    _activity_box(shapes, act)


def _build_discussion(shapes, title, body, act, img):
    """Numbered discussion questions."""
    _header_bar(shapes, title, RED)
    _footer_bar(shapes, YELLOW)
    qs = [q.strip().lstrip('•-0123456789. ').strip()
          for q in body.split('\n') if q.strip()]
    y = 900000
    fills = [LIGHT, PINK, LIGHT, PINK, LIGHT, PINK]
    for i, q in enumerate(qs[:6]):
        shapes.append(_badge(200000, y+30000, i+1, RED if i%2==0 else PURPLE))
        shapes.append(_txt_in_box(600000, y, W-800000, 440000,
                                   q, sz=1500, txt_colour=NAVY,
                                   fill=fills[i]))
        y += 530000
    _img_hint(shapes, img)
    _activity_box(shapes, act)


def _build_task(shapes, title, body, act, img, accent):
    """Task/group work slide with instruction box + content."""
    _header_bar(shapes, title, accent)
    _footer_bar(shapes)
    lines = [l.strip() for l in body.split('\n') if l.strip()]
    y = 900000
    for line in lines[:7]:
        shapes.append(_txt_in_box(200000, y, W-400000, 520000,
                                   line, sz=1600, txt_colour=NAVY, fill=LIGHT))
        y += 610000
    _img_hint(shapes, img)
    _activity_box(shapes, act)


def _build_reading(shapes, title, body, act, img):
    """Two-column: reading text left, questions right."""
    _header_bar(shapes, title, NAVY)
    _footer_bar(shapes)
    if 'Question' in body or '?' in body:
        parts = re.split(r'(Questions?:?)', body, maxsplit=1)
        rt = parts[0].strip()
        qt = ''.join(parts[1:]).strip() if len(parts) > 1 else ''
    else:
        rt, qt = body, ''
    shapes.append(_txt_in_box(200000, 880000, 6400000, H-1200000,
                               rt, sz=1300, txt_colour=NAVY, fill=LIGHT))
    if qt:
        shapes.append(_txt(6800000, 880000, 5000000, 300000,
                           'Questions', sz=1800, bold=True, colour=NAVY))
        shapes.append(_txt_in_box(6800000, 1220000, 5000000, H-1520000,
                                   qt, sz=1300, txt_colour=NAVY, fill=PINK))
    elif img:
        shapes.append(_txt(6800000, 880000, 5000000, H-1100000,
                           f'[IMAGE: {img}]', sz=1000, colour=GREY, align='ctr'))
    if act:
        _activity_box(shapes, act)


def _build_video_placeholder(shapes, title, body):
    """Blank slide with a centred instruction box — teacher embeds video."""
    shapes.append(_rect(0, 0, W, H, WHITE))
    _header_bar(shapes, title or 'Video', NAVY)
    _footer_bar(shapes)
    instruction = body or 'Your teacher will play a video.\n\nAs you watch, follow the instructions above.'
    shapes.append(_txt_in_box(1500000, 1800000, W-3000000, 3200000,
                               instruction, sz=2000, txt_colour=NAVY, fill=LIGHT))


def _build_answers_hidden(shapes, title, body):
    """Hidden answer slide — plain list of answers on light background."""
    shapes.append(_rect(0, 0, W, H, WHITE))
    _header_bar(shapes, title or 'Answers', PURPLE)
    _footer_bar(shapes, YELLOW)
    if body:
        shapes.append(_txt_in_box(400000, 900000, W-800000, H-1300000,
                                   body, sz=1800, txt_colour=NAVY, fill=LIGHT))


def _build_standard(shapes, title, body, act, img, accent):
    """Standard slide: header + content in a rounded box."""
    _header_bar(shapes, title, accent)
    _footer_bar(shapes)
    if body:
        shapes.append(_txt_in_box(200000, 900000, W-400000, H-1300000,
                                   body, sz=1700, txt_colour=NAVY, fill=LIGHT))
    _img_hint(shapes, img)
    _activity_box(shapes, act)


# ── Template slide modifiers ──────────────────────────────────────────────────

def _set_t(xml, old, new):
    return xml.replace(f'<a:t>{_esc(old)}</a:t>',
                       f'<a:t>{_esc(new)}</a:t>', 1)

def _modify_slide1(xml, lesson):
    title = lesson.get('lesson_title', 'LESSON TITLE').upper()
    tl = lesson.get('lesson_type_label', 'LANG')
    lv = lesson.get('level_label', 'Level 3')
    wk = lesson.get('week', 'A')
    meta = f'WEEK {wk} | PURPOSE | {tl} | {lv.upper()}'
    # Title: sz=7000 rPr block, two paragraphs
    xml = re.sub(
        r'(<a:rPr[^>]*sz="7000"[^>]*>.*?</a:rPr>\s*<a:t>)([^<]*)(</a:t>)',
        lambda m: m.group(1) + _esc(title) + m.group(3),
        xml, count=1, flags=re.DOTALL
    )
    xml = re.sub(
        r'(<a:rPr[^>]*sz="7000"[^>]*>.*?</a:rPr>\s*<a:t>)([^<]*)(</a:t>)',
        lambda m: m.group(1) + '' + m.group(3),
        xml, count=1, flags=re.DOTALL
    )
    xml = re.sub(
        r'(<a:t>)(WEEK A \| PURPOSE \| LANG \| LEVEL 2)(</a:t>)',
        lambda m: m.group(1) + _esc(meta) + m.group(3),
        xml
    )
    return xml

FOCUS_OLD = ('Learning and practicing common English expressions used to complain '
             'about everyday situations (with a specific focus on public spaces). '
             'Students explore how complaints can be expressed with different levels '
             'of formality (from casual to polite) and different degrees of annoyance '
             '(from mildly irritating to extremely frustrating).')
OBJ_OLD   = ('By the end of the lesson, students will be able to use appropriate '
             'English expressions to complain about situations, choosing suitable '
             'language based on how formal the context is and how strong their '
             'feelings of annoyance are.')

def _modify_slide2(xml, lesson):
    focus = lesson.get('lesson_focus', '')
    objvs = lesson.get('objectives', '')
    extra = lesson.get('extra_materials', 'None.')
    xml = xml.replace(_esc(FOCUS_OLD), _esc(focus), 1)
    xml = xml.replace(_esc(OBJ_OLD),   _esc(objvs), 1)
    xml = re.sub(r'<a:t>None\.</a:t>',
                 f'<a:t>{_esc(extra)}</a:t>', xml, count=1)
    return xml

def _find_step_groups_xml(xml):
    """Find all numbered step groups by searching for '1. ' pattern in t-nodes."""
    return re.findall(r'<p:grpSp>.*?</p:grpSp>', xml, re.DOTALL)

def _modify_plan_xml(xml, steps):
    # Replace step titles (e.g. "1. Introduction")
    for step in steps:
        header = f"{step['step_num']}. {step['title']}"
        xml = re.sub(
            rf'(<a:t>){re.escape(str(step["step_num"]))}\.(?!\d)[^<]*(</a:t>)',
            lambda m, h=header: m.group(1) + _esc(h) + m.group(2),
            xml, count=1
        )
    return xml

KNOWN_INSTRS = [
    "Introduce the topic by activating students\u2019 schemata. Brainstorm public spaces and elicit examples of things people commonly find annoying.",
    "Present the caf\u00e9 scenario using a picture. Have Ss discuss in groups whether the situations shown are very annoying, slightly annoying, or not annoying, and agree on their top five most annoying caf\u00e9 behaviors.",
    "Tell Ss they are going to complete a logic puzzle. Have them read info about different characters, including things they find annoying and things they do that annoy others. In groups, ask students to use logic to rearrange the characters so that no one is sitting next to someone who annoys them.",
    "Have Ss choose one thing that annoys them and one thing they do that is annoying. Recreate the caf\u00e9 scenario by seating students in a circle and have them rearrange themselves so they are not sitting next to someone who annoys them.",
    "Have Ss choose one thing that annoys them and one thing they do that is annoying. Recreate the caf\u00e9 scenario by seating students in a circle and have them rearrange themselves so they are not sitting next to someone who annoys them.",
]
KNOWN_TIMES = ["5'", "15'", "15'", "20'", "5'"]

def _modify_plan_instrs(xml, steps):
    for i, step in enumerate(steps):
        if i < len(KNOWN_INSTRS):
            old = _esc(KNOWN_INSTRS[i])
            new = _esc(step['instructions'])
            if old in xml:
                xml = xml.replace(old, new, 1)
            else:
                xml = xml.replace(KNOWN_INSTRS[i], step['instructions'], 1)
    return xml

def _modify_plan_times(xml, steps, known_times):
    for step, old_t in zip(steps, known_times):
        new_t = f"{step['time_mins']}'"
        xml = xml.replace(f'<a:t>{old_t}</a:t>',
                          f'<a:t>{_esc(new_t)}</a:t>', 1)
    return xml

def _modify_materials(xml, lesson):
    notes = lesson.get('materials_notes', 'None.')
    xml = re.sub(r'<a:t>None\.</a:t>',
                 f'<a:t>{_esc(notes)}</a:t>', xml, count=1)
    return xml

def _fix_rels(unpacked):
    """Remove broken inter-slide shortcut rels and matching hlinkClick elements."""
    slides_dir = os.path.join(unpacked, 'ppt', 'slides')
    rels_dir   = os.path.join(slides_dir, '_rels')
    for slide_f, rels_f in [('slide3.xml','slide3.xml.rels'),
                              ('slide4.xml','slide4.xml.rels')]:
        rp = os.path.join(rels_dir, rels_f)
        if not os.path.exists(rp): continue
        rels = open(rp).read()
        rids = re.findall(r'<Relationship[^>]+Id="([^"]+)"[^>]+/relationships/slide[^>]*/>', rels)
        rels = re.sub(r'\s*<Relationship[^>]+/relationships/slide[^>]*/>', '', rels)
        open(rp,'w').write(rels)
        sp = os.path.join(slides_dir, slide_f)
        if not os.path.exists(sp): continue
        sxml = open(sp).read()
        for rid in rids:
            sxml = re.sub(rf'<a:hlinkClick[^>]*r:id="{re.escape(rid)}"[^>]*/>', '', sxml)
        open(sp,'w').write(sxml)


# ── Main entry point ──────────────────────────────────────────────────────────

def build_lesson_pptx(lesson: dict, template_path: str) -> bytes:
    """Build a clean, valid PPTX using unpack/add_slide/pack scripts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        unpacked = os.path.join(tmpdir, 'unpacked')

        # 1. Unpack
        subprocess.run(['python3', os.path.join(SCRIPTS_DIR,'office','unpack.py'),
                        template_path, unpacked],
                       check=True, capture_output=True)

        slides_dir   = os.path.join(unpacked, 'ppt', 'slides')
        prs_xml_path = os.path.join(unpacked, 'ppt', 'presentation.xml')

        # 2. Fix broken shortcut rels in plan slides
        _fix_rels(unpacked)

        # 3. Modify structural slides
        steps = lesson.get('teacher_steps', [])
        mods = [
            ('slide1.xml', lambda x: _modify_slide1(x, lesson)),
            ('slide2.xml', lambda x: _modify_slide2(x, lesson)),
            ('slide3.xml', lambda x: _modify_plan_times(
                _modify_plan_instrs(_modify_plan_xml(x, steps[:3]), steps[:3]),
                steps[:3], KNOWN_TIMES[:3])),
            ('slide4.xml', lambda x: _modify_plan_times(
                _modify_plan_instrs(_modify_plan_xml(x, steps[3:5]), steps[3:5]),
                steps[3:5], KNOWN_TIMES[3:5])),
            ('slide6.xml', lambda x: _modify_materials(x, lesson)),
        ]
        for fname, transform in mods:
            p = os.path.join(slides_dir, fname)
            if not os.path.exists(p): continue
            with open(p) as fh: orig = fh.read()
            with open(p,'w') as fh: fh.write(transform(orig))

        # 4. Write first student slide into slide5.xml (blank placeholder)
        student_slides = lesson.get('student_slides', [])
        if student_slides:
            open(os.path.join(slides_dir,'slide5.xml'),'w').write(
                _gen_slide_xml(student_slides[0]))

        # 5. Add remaining student slides via add_slide.py
        existing_ids = list(map(int, re.findall(
            r'<p:sldId id="(\d+)"', open(prs_xml_path).read())))
        next_id = max(existing_ids) + 1 if existing_ids else 600
        new_sld_ids = []

        for sd in student_slides[1:]:
            r = subprocess.run(
                ['python3', os.path.join(SCRIPTS_DIR,'add_slide.py'),
                 unpacked, 'slide5.xml'],
                capture_output=True, text=True, check=True)
            lines = r.stdout.strip().split('\n')
            new_fname = lines[0].split()[1]
            rid_m = re.search(r'r:id="([^"]+)"', lines[1])
            if rid_m:
                new_sld_ids.append(f'<p:sldId id="{next_id}" r:id="{rid_m.group(1)}"/>')
                next_id += 1
            open(os.path.join(slides_dir, new_fname),'w').write(_gen_slide_xml(sd))

        # 6. Reorder sldIdLst: structural + student slides + Materials + Notes
        prs_xml = open(prs_xml_path).read()
        mat_m = re.search(r'<p:sldId[^>]*r:id="rId7"[^/]*/>', prs_xml)
        nts_m = re.search(r'<p:sldId[^>]*r:id="rId8"[^/]*/>', prs_xml)
        mat_s = mat_m.group() if mat_m else ''
        nts_s = nts_m.group() if nts_m else ''
        prs_xml = prs_xml.replace(mat_s,'',1).replace(nts_s,'',1)
        ins = '\n'.join(f'    {el}' for el in new_sld_ids)
        if mat_s: ins += f'\n    {mat_s}'
        if nts_s: ins += f'\n    {nts_s}'
        prs_xml = prs_xml.replace('</p:sldIdLst>', f'{ins}\n  </p:sldIdLst>')
        open(prs_xml_path,'w').write(prs_xml)

        # 7. Clean + Pack
        subprocess.run(['python3', os.path.join(SCRIPTS_DIR,'clean.py'), unpacked],
                       check=True, capture_output=True)

        out = os.path.join(tmpdir, 'output.pptx')
        r = subprocess.run(
            ['python3', os.path.join(SCRIPTS_DIR,'office','pack.py'),
             unpacked, out, '--original', template_path],
            capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f'pack.py failed:\n{r.stdout}\n{r.stderr}')

        return open(out,'rb').read()
