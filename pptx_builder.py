"""
UKLC Purpose Lesson PPTX Builder — v4
Clean white slides matching real UKLC lesson design.
No header/footer bars. Plain title text + coloured rounded-rect boxes.
"""
import os, re, subprocess, tempfile

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts')

# ── Brand colours ─────────────────────────────────────────────────────────────
NAVY   = '1C3048'
YELLOW = 'E9EA7E'
RED    = 'EC273B'
WHITE  = 'FFFFFF'
LIGHT  = 'E6EEF3'
PINK   = 'FAD7D8'
GREY   = 'AAAAAA'

W = 12192000   # slide width  EMU (33.87cm widescreen)
H = 6858000    # slide height EMU (19.05cm)

MAX_STUDENT_SLIDES = 16

# ── XML primitives ─────────────────────────────────────────────────────────────

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

def _para(text, sz, bold=False, colour=NAVY, align='l', italic=False):
    return (f'<a:p><a:pPr algn="{align}"/>'
            f'<a:r>{_rpr(sz,bold,colour,italic)}<a:t>{_esc(text)}</a:t></a:r>'
            f'</a:p>')

def _empty_para():
    return '<a:p><a:endParaRPr lang="en-GB" dirty="0"/></a:p>'

_sid = [100]
def _nid():
    v = _sid[0]; _sid[0] += 1; return v

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

# ── Shape builders ─────────────────────────────────────────────────────────────

def _bg(shapes):
    """White background rect."""
    ln = '<a:ln><a:noFill/></a:ln>'
    shapes.append(
        f'<p:sp><p:nvSpPr>'
        f'<p:cNvPr id="{_nid()}" name="bg"/>'
        f'<p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
        f'<p:spPr>'
        f'<a:xfrm><a:off x="0" y="0"/><a:ext cx="{W}" cy="{H}"/></a:xfrm>'
        f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>{_fill(WHITE)}{ln}'
        f'</p:spPr>'
        f'<p:txBody><a:bodyPr/><a:lstStyle/>{_empty_para()}</p:txBody>'
        f'</p:sp>'
    )

def _txbox(shapes, x, y, cx, cy, paras_xml):
    """Transparent text box."""
    shapes.append(
        f'<p:sp><p:nvSpPr>'
        f'<p:cNvPr id="{_nid()}" name="t"/>'
        f'<p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
        f'<p:spPr>'
        f'<a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/>'
        f'<a:ln><a:noFill/></a:ln></p:spPr>'
        f'<p:txBody>'
        f'<a:bodyPr wrap="square" rtlCol="0"><a:spAutoFit/></a:bodyPr>'
        f'<a:lstStyle/>{paras_xml}'
        f'</p:txBody></p:sp>'
    )

def _rrect(shapes, x, y, cx, cy, fill, paras_xml, anchor='ctr'):
    """Rounded rect with text."""
    shapes.append(
        f'<p:sp><p:nvSpPr>'
        f'<p:cNvPr id="{_nid()}" name="rr"/>'
        f'<p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
        f'<p:spPr>'
        f'<a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        f'<a:prstGeom prst="roundRect">'
        f'<a:avLst><a:gd name="adj" fmla="val 30000"/></a:avLst>'
        f'</a:prstGeom>{_fill(fill)}<a:ln><a:noFill/></a:ln>'
        f'</p:spPr>'
        f'<p:txBody>'
        f'<a:bodyPr wrap="square" rtlCol="0" anchor="{anchor}" lIns="360000" rIns="360000" tIns="180000" bIns="180000"/>'
        f'<a:lstStyle/>{paras_xml}'
        f'</p:txBody></p:sp>'
    )

def _title(shapes, text, x=457200, y=228600, cx=None, sz=3200):
    """Plain navy title text — no box."""
    cx = cx or (W - 914400)
    paras = _para(text, sz, bold=False, colour=NAVY)
    _txbox(shapes, x, y, cx, cy=700000, paras_xml=paras)

def _img_hint(shapes, img):
    if img:
        p = _para(f'[IMAGE: {img}]', 900, colour=GREY, align='ctr')
        _txbox(shapes, 457200, 1000000, W-914400, 400000, p)

# ── Per-slide builders ─────────────────────────────────────────────────────────

def _gen_slide_xml(sd):
    _sid[0] = 100
    stype = sd.get('slide_type', 'info')
    title = sd.get('title', '')
    body  = sd.get('content', '')
    act   = sd.get('activity_instruction', '')
    img   = sd.get('image_placeholder', '')
    shapes = []
    _bg(shapes)

    if stype == 'hook':
        _build_hook(shapes, title, body, act, img)
    elif stype in ('vocab_intro', 'vocab_practice', 'matching'):
        _build_vocab(shapes, title, body, act)
    elif stype == 'info':
        _build_info(shapes, title, body, act, img)
    elif stype == 'video_placeholder':
        _build_video(shapes, title, body)
    elif stype == 'reading':
        _build_reading(shapes, title, body, act)
    elif stype == 'discussion':
        _build_discussion(shapes, title, body, act)
    elif stype in ('grammar_focus',):
        _build_grammar(shapes, title, body, act)
    elif stype == 'gap_fill':
        _build_gap_fill(shapes, title, body, act)
    elif stype in ('task_setup', 'task_content'):
        _build_task(shapes, title, body, act, img)
    elif stype in ('pair_work', 'group_work', 'roleplay'):
        _build_pair(shapes, title, body, act)
    elif stype == 'game':
        _build_game(shapes, title, body, act)
    elif stype == 'debate':
        _build_debate(shapes, title, body, act)
    else:
        _build_standard(shapes, title, body, act, img)

    return _slide_wrap(shapes)


def _build_hook(shapes, title, body, act, img):
    """White slide: image hint top, title, then pink question boxes."""
    _img_hint(shapes, img or title)
    # Title
    _title(shapes, title, y=228600, sz=3600)
    # Questions as pink boxes
    lines = [l.strip() for l in body.split('\n') if l.strip()][:2]
    y = H - 2000000
    gap = 120000
    box_h = 700000
    for line in lines:
        p = _para(line, 2000, colour=NAVY, align='ctr')
        _rrect(shapes, 457200, y, W-914400, box_h, PINK, p)
        y += box_h + gap
    # Activity instruction small below
    if act:
        p = _para(act, 1400, colour=GREY, align='ctr')
        _txbox(shapes, 457200, y + 60000, W-914400, 400000, p)


def _build_vocab(shapes, title, body, act):
    """Title + 2-column grid of light blue boxes."""
    _title(shapes, title)
    lines = [l.strip() for l in body.split('\n') if l.strip()][:8]
    n = len(lines)
    cols = 2
    rows = (n + 1) // 2
    col_w = (W - 1200000) // 2
    col_gap = 200000
    row_h = min(900000, max(500000, (H - 1200000) // rows))
    row_gap = 80000
    for i, line in enumerate(lines):
        col = i % 2
        row = i // 2
        x = 457200 + col * (col_w + col_gap)
        y = 900000 + row * (row_h + row_gap)
        fill = LIGHT if col == 0 else PINK
        p = _para(line, 1600, colour=NAVY)
        _rrect(shapes, x, y, col_w, row_h, fill, p, anchor='ctr')
    if act:
        p = _para(act, 1300, colour=GREY, align='ctr')
        _txbox(shapes, 457200, H-380000, W-914400, 340000, p)


def _build_info(shapes, title, body, act, img):
    """Title + large light blue content box."""
    _title(shapes, title)
    if body:
        p = ''.join(_para(l, 1700, colour=NAVY) for l in body.split('\n'))
        _rrect(shapes, 457200, 900000, W-914400, H-1300000, LIGHT, p, anchor='t')
    if act:
        p = _para(act, 1300, colour=GREY, align='ctr')
        _txbox(shapes, 457200, H-380000, W-914400, 340000, p)


def _build_video(shapes, title, body):
    """Navy instruction box + watch questions in pink boxes."""
    # Navy instruction top
    p = _para(title or 'Watch the video', 2200, colour=WHITE, align='ctr')
    _rrect(shapes, 457200, 300000, W-914400, 700000, NAVY, p)
    # Watch questions
    lines = [l.strip().lstrip('-•').strip() for l in body.split('\n') if l.strip()][:3]
    y = 1200000
    for line in lines:
        p = _para(line, 1800, colour=NAVY, align='ctr')
        _rrect(shapes, 914400, y, W-1828800, 650000, PINK, p)
        y += 730000


def _build_reading(shapes, title, body, act):
    """Title + light blue text left, pink questions right."""
    _title(shapes, title)
    if 'Questions' in body or '?' in body:
        parts = re.split(r'(Questions?:?)', body, maxsplit=1)
        rt = parts[0].strip()
        qt = ''.join(parts[1:]).strip() if len(parts) > 1 else ''
    else:
        rt, qt = body, ''
    left_w = int(W * 0.52) - 457200
    right_w = W - left_w - 1100000
    p = ''.join(_para(l, 1500, colour=NAVY) for l in rt.split('\n'))
    _rrect(shapes, 457200, 900000, left_w, H-1100000, LIGHT, p, anchor='t')
    if qt:
        p = ''.join(_para(l, 1500, colour=NAVY) for l in qt.split('\n'))
        _rrect(shapes, left_w + 700000, 900000, right_w, H-1100000, PINK, p, anchor='t')
    if act:
        p = _para(act, 1300, colour=GREY, align='ctr')
        _txbox(shapes, 457200, H-350000, W-914400, 320000, p)


def _build_discussion(shapes, title, body, act):
    """Instruction text top + stacked pink question boxes."""
    p = _para(title, 2200, colour=NAVY, align='ctr')
    _txbox(shapes, 457200, 180000, W-914400, 600000, p)
    qs = [q.strip().lstrip('•-0123456789. ').strip() for q in body.split('\n') if q.strip()][:5]
    available_h = H - 900000 - 200000
    box_h = min(700000, max(420000, (available_h - (len(qs)-1)*80000) // len(qs)))
    y = 900000
    for q in qs:
        p = _para(q, 1700, colour=NAVY, align='ctr')
        _rrect(shapes, 457200, y, W-914400, box_h, PINK, p)
        y += box_h + 80000
    if act:
        p = _para(act, 1300, colour=GREY, align='ctr')
        _txbox(shapes, 457200, H-330000, W-914400, 300000, p)


def _build_grammar(shapes, title, body, act):
    """Title + navy rule box + light blue example boxes."""
    _title(shapes, title)
    lines = [l.strip() for l in body.split('\n') if l.strip()]
    if lines:
        p = _para(lines[0], 1800, colour=WHITE, align='ctr')
        _rrect(shapes, 457200, 900000, W-914400, 650000, NAVY, p)
    y = 1650000
    for line in lines[1:4]:
        p = _para(line, 1600, colour=NAVY)
        _rrect(shapes, 457200, y, W-914400, 580000, LIGHT, p)
        y += 640000
    if act:
        p = _para(act, 1300, colour=GREY, align='ctr')
        _txbox(shapes, 457200, H-330000, W-914400, 300000, p)


def _build_gap_fill(shapes, title, body, act):
    """Title + numbered sentences in light blue boxes."""
    _title(shapes, title)
    lines = [l.strip() for l in body.split('\n') if l.strip()][:6]
    available_h = H - 1000000 - 300000
    box_h = min(700000, max(380000, (available_h - (len(lines)-1)*60000) // max(len(lines),1)))
    y = 1000000
    for line in lines:
        p = _para(line, 1600, colour=NAVY)
        _rrect(shapes, 457200, y, W-914400, box_h, LIGHT, p)
        y += box_h + 60000
    if act:
        p = _para(act, 1300, colour=GREY, align='ctr')
        _txbox(shapes, 457200, H-330000, W-914400, 300000, p)


def _build_task(shapes, title, body, act, img):
    """Navy instruction box top + large pink content box."""
    p = _para(title, 2000, colour=WHITE, align='ctr')
    _rrect(shapes, 457200, 228600, W-914400, 700000, NAVY, p)
    if body:
        lines = body.split('\n')
        p = ''.join(_para(l, 1700, colour=NAVY) for l in lines)
        _rrect(shapes, 457200, 1050000, W-914400, H-1400000, PINK, p, anchor='t')
    if act:
        p = _para(act, 1300, colour=GREY, align='ctr')
        _txbox(shapes, 457200, H-330000, W-914400, 300000, p)


def _build_pair(shapes, title, body, act):
    """Title top + pink instruction boxes."""
    p = _para(title, 2200, colour=NAVY, align='ctr')
    _txbox(shapes, 457200, 180000, W-914400, 600000, p)
    lines = [l.strip() for l in body.split('\n') if l.strip()][:4]
    available_h = H - 900000 - 300000
    box_h = min(900000, max(480000, (available_h - (len(lines)-1)*80000) // max(len(lines),1)))
    y = 900000
    for line in lines:
        p = _para(line, 1700, colour=NAVY, align='ctr')
        _rrect(shapes, 457200, y, W-914400, box_h, PINK, p)
        y += box_h + 80000
    if act:
        p = _para(act, 1300, colour=GREY, align='ctr')
        _txbox(shapes, 457200, H-330000, W-914400, 300000, p)


def _build_game(shapes, title, body, act):
    """Large centred title + light blue item boxes in rows."""
    p = _para(title, 3600, bold=True, colour=NAVY, align='ctr')
    _txbox(shapes, 457200, 200000, W-914400, 900000, p)
    lines = [l.strip() for l in body.split('\n') if l.strip()][:7]
    n = len(lines)
    if n <= 3:
        # single row
        box_w = (W - 1000000) // n - 80000
        for i, line in enumerate(lines):
            x = 457200 + i * (box_w + 80000)
            p = _para(line, 1600, colour=NAVY, align='ctr')
            _rrect(shapes, x, 1300000, box_w, 800000, LIGHT, p)
    else:
        # two rows
        cols = (n + 1) // 2
        box_w = (W - 1000000) // cols - 80000
        box_h = 700000
        for i, line in enumerate(lines):
            col = i % cols
            row = i // cols
            x = 457200 + col * (box_w + 80000)
            y = 1300000 + row * (box_h + 100000)
            p = _para(line, 1500, colour=NAVY, align='ctr')
            _rrect(shapes, x, y, box_w, box_h, LIGHT, p)
    if act:
        p = _para(act, 1300, colour=GREY, align='ctr')
        _txbox(shapes, 457200, H-330000, W-914400, 300000, p)


def _build_debate(shapes, title, body, act):
    """Title + two side-by-side navy/light boxes."""
    _title(shapes, title, sz=2800)
    lines = [l.strip() for l in body.split('\n') if l.strip()]
    mid = len(lines) // 2
    left = '\n'.join(lines[:mid])
    right = '\n'.join(lines[mid:])
    half = (W - 1200000) // 2
    p = ''.join(_para(l, 1600, colour=WHITE) for l in left.split('\n'))
    _rrect(shapes, 457200, 900000, half, H-1100000, NAVY, p, anchor='t')
    p = ''.join(_para(l, 1600, colour=NAVY) for l in right.split('\n'))
    _rrect(shapes, 457200 + half + 200000, 900000, half, H-1100000, LIGHT, p, anchor='t')
    if act:
        p = _para(act, 1300, colour=GREY, align='ctr')
        _txbox(shapes, 457200, H-330000, W-914400, 300000, p)


def _build_standard(shapes, title, body, act, img):
    """Fallback: title + light blue content box."""
    _title(shapes, title)
    if body:
        p = ''.join(_para(l, 1700, colour=NAVY) for l in body.split('\n'))
        _rrect(shapes, 457200, 900000, W-914400, H-1300000, LIGHT, p, anchor='t')
    if act:
        p = _para(act, 1300, colour=GREY, align='ctr')
        _txbox(shapes, 457200, H-330000, W-914400, 300000, p)
    _img_hint(shapes, img)


# ── Template slide modifiers ───────────────────────────────────────────────────

def _set_t(xml, old, new):
    return xml.replace(f'<a:t>{_esc(old)}</a:t>', f'<a:t>{_esc(new)}</a:t>', 1)

def _modify_slide1(xml, lesson):
    title = lesson.get('lesson_title', 'LESSON TITLE').upper()
    tl = lesson.get('lesson_type_label', 'LANG')
    lv = lesson.get('level_label', 'Level 3')
    wk = lesson.get('week', 'A')
    meta = f'WEEK {wk} | PURPOSE | {tl} | {lv.upper()}'
    xml = re.sub(
        r'(<a:rPr[^>]*sz="7000"[^>]*>.*?</a:rPr>\s*<a:t>)([^<]*)(</a:t>)',
        lambda m: m.group(1) + _esc(title) + m.group(3),
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
    xml = re.sub(r'<a:t>None\.</a:t>', f'<a:t>{_esc(extra)}</a:t>', xml, count=1)
    return xml

KNOWN_INSTRS = [
    "Introduce the topic by activating students\u2019 schemata. Brainstorm public spaces and elicit examples of things people commonly find annoying.",
    "Present the caf\u00e9 scenario using a picture. Have Ss discuss in groups whether the situations shown are very annoying, slightly annoying, or not annoying, and agree on their top five most annoying caf\u00e9 behaviors.",
    "Tell Ss they are going to complete a logic puzzle. Have them read info about different characters, including things they find annoying and things they do that annoy others. In groups, ask students to use logic to rearrange the characters so that no one is sitting next to someone who annoys them.",
    "Have Ss choose one thing that annoys them and one thing they do that is annoying. Recreate the caf\u00e9 scenario by seating students in a circle and have them rearrange themselves so they are not sitting next to someone who annoys them.",
    "Have Ss choose one thing that annoys them and one thing they do that is annoying. Recreate the caf\u00e9 scenario by seating students in a circle and have them rearrange themselves so they are not sitting next to someone who annoys them.",
]
KNOWN_TIMES = ["5'", "15'", "15'", "20'", "5'"]

def _modify_plan_xml(xml, steps):
    for step in steps:
        header = f"{step['step_num']}. {step['title']}"
        xml = re.sub(
            rf'(<a:t>){re.escape(str(step["step_num"]))}\.(?!\d)[^<]*(</a:t>)',
            lambda m, h=header: m.group(1) + _esc(h) + m.group(2),
            xml, count=1
        )
    return xml

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
        xml = xml.replace(f'<a:t>{old_t}</a:t>', f'<a:t>{_esc(new_t)}</a:t>', 1)
    return xml

def _modify_materials(xml, lesson):
    notes = lesson.get('materials_notes', 'None.')
    xml = re.sub(r'<a:t>None\.</a:t>', f'<a:t>{_esc(notes)}</a:t>', xml, count=1)
    return xml

def _fix_rels(unpacked):
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


# ── Main entry point ───────────────────────────────────────────────────────────

def build_lesson_pptx(lesson: dict, template_path: str) -> bytes:
    with tempfile.TemporaryDirectory() as tmpdir:
        unpacked = os.path.join(tmpdir, 'unpacked')

        # 1. Unpack template
        r = subprocess.run(
            ['python3', os.path.join(SCRIPTS_DIR, 'office', 'unpack.py'),
             template_path, unpacked],
            check=True, capture_output=True, text=True
        )
        print(f'[pptx_builder] unpack: {r.stdout.strip()}')
        if r.stderr.strip():
            print(f'[pptx_builder] unpack stderr: {r.stderr.strip()}')

        slides_dir   = os.path.join(unpacked, 'ppt', 'slides')
        prs_xml_path = os.path.join(unpacked, 'ppt', 'presentation.xml')

        # 2. Fix broken rels
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

        # 4. Write first student slide into slide5.xml
        student_slides = lesson.get('student_slides', [])[:MAX_STUDENT_SLIDES]
        if student_slides:
            open(os.path.join(slides_dir,'slide5.xml'),'w').write(
                _gen_slide_xml(student_slides[0]))

        # 5. Add remaining student slides
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

        # 6. Reorder sldIdLst
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
        subprocess.run(
            ['python3', os.path.join(SCRIPTS_DIR,'clean.py'), unpacked],
            check=True, capture_output=True, text=True
        )
        out = os.path.join(tmpdir, 'output.pptx')
        r = subprocess.run(
            ['python3', os.path.join(SCRIPTS_DIR,'office','pack.py'),
             unpacked, out, '--original', template_path],
            capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f'pack.py failed:\n{r.stdout}\n{r.stderr}')

        return open(out,'rb').read()
