"""
UKLC Purpose Lesson PPTX Builder — v5
Immersive design: dark atmospheric background + floating white card.
Matches visual style of real UKLC PURPOSE lesson decks (Reading Challenge,
Brainworm Apocalypse, Game of Morals reference PPTXs).
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
GREY   = '8A9BAD'

# Dark atmospheric background tones
D_NAVY   = '0B1520'
D_PURPLE = '130A28'
D_TEAL   = '081520'
D_DARK   = '05050F'
D_GREEN  = '081508'
D_RED    = '180808'

W = 12192000   # slide width  EMU (widescreen)
H = 6858000    # slide height EMU

MAX_STUDENT_SLIDES = 16

# ── Background themes: (gradient_top, gradient_bottom, accent_strip) ──────────
_BG = {
    'hook':              (D_NAVY,   NAVY,      YELLOW),
    'vocab_intro':       (D_PURPLE, '2D1B69',  PINK),
    'vocab_practice':    (D_PURPLE, '2D1B69',  PINK),
    'matching':          (D_PURPLE, '2D1B69',  LIGHT),
    'discussion':        (D_TEAL,   '1A3A4A',  LIGHT),
    'game':              (D_DARK,   '150A28',  YELLOW),
    'task_setup':        (D_RED,    '2A0E0E',  RED),
    'task_content':      (D_RED,    '2A0E0E',  RED),
    'info':              (D_NAVY,   NAVY,      LIGHT),
    'reading':           (D_GREEN,  '1C2B1A',  LIGHT),
    'grammar_focus':     (D_NAVY,   '1A1500',  YELLOW),
    'gap_fill':          (D_TEAL,   '1A3A4A',  LIGHT),
    'video_placeholder': (D_DARK,   '050505',  RED),
    'pair_work':         (D_TEAL,   '1A3A4A',  YELLOW),
    'group_work':        (D_TEAL,   '1A3A4A',  YELLOW),
    'roleplay':          (D_PURPLE, '2D1B69',  PINK),
    'debate':            (D_NAVY,   NAVY,      RED),
}
_BG_DEFAULT = (D_NAVY, NAVY, LIGHT)

# ── ID counter ────────────────────────────────────────────────────────────────
_sid = [100]
def _nid():
    v = _sid[0]; _sid[0] += 1; return v

# ── XML helpers ────────────────────────────────────────────────────────────────
def _esc(t):
    return (str(t)
        .replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
        .replace('\u2018',"'").replace('\u2019',"'")
        .replace('\u201c','"').replace('\u201d','"')
        .replace('\u2013','-').replace('\u2014','--')
        .replace('\u2026','...')
    )

def _fill(hex_col):
    return f'<a:solidFill><a:srgbClr val="{hex_col}"/></a:solidFill>'

def _rpr(sz, bold=False, colour=NAVY, italic=False):
    b = ' b="1"' if bold else ''
    i = ' i="1"' if italic else ''
    return (f'<a:rPr lang="en-GB" sz="{sz}"{b}{i} dirty="0" smtClean="0">'
            f'{_fill(colour)}'
            f'<a:latin typeface="Calibri" pitchFamily="0" charset="0"/>'
            f'</a:rPr>')

def _para(text, sz, bold=False, colour=NAVY, align='l', italic=False):
    return (f'<a:p><a:pPr algn="{align}"/>'
            f'<a:r>{_rpr(sz,bold,colour,italic)}<a:t>{_esc(text)}</a:t></a:r>'
            f'</a:p>')

def _empty_para(sz=1400):
    return f'<a:p><a:pPr/><a:endParaRPr lang="en-GB" sz="{sz}" dirty="0"/></a:p>'

def _spacer():
    """Short spacing paragraph between content sections."""
    return '<a:p><a:pPr spc="-100000"/><a:endParaRPr lang="en-GB" sz="600" dirty="0"/></a:p>'

def _rich_paras(text, sz, colour=NAVY, align='l', strip_bullets=False):
    """Build paragraph XML. Handles **bold** inline markers."""
    if not text:
        return _empty_para(sz)
    result = []
    for raw in text.split('\n'):
        line = raw.strip()
        if not line:
            result.append(_spacer())
            continue
        if strip_bullets:
            line = re.sub(r'^[\-•*]\s*', '', line)
            line = re.sub(r'^\d+[\.\)]\s*', '', line)
        parts = re.split(r'\*\*([^*]+)\*\*', line)
        runs = []
        for i, part in enumerate(parts):
            if not part:
                continue
            runs.append(
                f'<a:r>{_rpr(sz, bold=(i%2==1), colour=colour)}'
                f'<a:t>{_esc(part)}</a:t></a:r>'
            )
        if runs:
            result.append(f'<a:p><a:pPr algn="{align}"/>' + ''.join(runs) + '</a:p>')
    return ''.join(result) if result else _empty_para(sz)

# ── Shape primitives ───────────────────────────────────────────────────────────
def _grad_rect(shapes, x, y, cx, cy, col1, col2, angle=5400000):
    grad = (f'<a:gradFill rotWithShape="1"><a:gsLst>'
            f'<a:gs pos="0"><a:srgbClr val="{col1}"/></a:gs>'
            f'<a:gs pos="100000"><a:srgbClr val="{col2}"/></a:gs>'
            f'</a:gsLst><a:lin ang="{angle}" scaled="0"/></a:gradFill>')
    shapes.append(
        f'<p:sp><p:nvSpPr>'
        f'<p:cNvPr id="{_nid()}" name="bg"/>'
        f'<p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
        f'<p:spPr>'
        f'<a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>{grad}'
        f'<a:ln><a:noFill/></a:ln></p:spPr>'
        f'<p:txBody><a:bodyPr/><a:lstStyle/>{_empty_para()}</p:txBody></p:sp>'
    )

def _solid_rect(shapes, x, y, cx, cy, col, name='r'):
    shapes.append(
        f'<p:sp><p:nvSpPr>'
        f'<p:cNvPr id="{_nid()}" name="{name}"/>'
        f'<p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
        f'<p:spPr>'
        f'<a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>{_fill(col)}'
        f'<a:ln><a:noFill/></a:ln></p:spPr>'
        f'<p:txBody><a:bodyPr/><a:lstStyle/>{_empty_para()}</p:txBody></p:sp>'
    )

def _txt_box(shapes, x, y, cx, cy, paras_xml, anchor='t'):
    """Transparent floating text box (for labels outside cards)."""
    shapes.append(
        f'<p:sp><p:nvSpPr>'
        f'<p:cNvPr id="{_nid()}" name="lbl"/>'
        f'<p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
        f'<p:spPr>'
        f'<a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/>'
        f'<a:ln><a:noFill/></a:ln></p:spPr>'
        f'<p:txBody>'
        f'<a:bodyPr wrap="square" rtlCol="0" anchor="{anchor}"><a:spAutoFit/></a:bodyPr>'
        f'<a:lstStyle/>{paras_xml}'
        f'</p:txBody></p:sp>'
    )

def _float_card(shapes, x, y, cx, cy, paras_xml, anchor='t', adj=50000):
    """
    White floating card — the primary content container.
    Generous corner radius (adj=50000 = very round, like real lessons).
    Uses normAutofit so text scales to fit card.
    """
    shapes.append(
        f'<p:sp><p:nvSpPr>'
        f'<p:cNvPr id="{_nid()}" name="card"/>'
        f'<p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
        f'<p:spPr>'
        f'<a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        f'<a:prstGeom prst="roundRect">'
        f'<a:avLst><a:gd name="adj" fmla="val {adj}"/></a:avLst>'
        f'</a:prstGeom>{_fill(WHITE)}<a:ln><a:noFill/></a:ln>'
        f'</p:spPr>'
        f'<p:txBody>'
        f'<a:bodyPr wrap="square" rtlCol="0" anchor="{anchor}" '
        f'lIns="720000" rIns="720000" tIns="540000" bIns="360000">'
        f'<a:normAutofit/></a:bodyPr>'
        f'<a:lstStyle/>{paras_xml}'
        f'</p:txBody></p:sp>'
    )

def _colour_card(shapes, x, y, cx, cy, fill_col, paras_xml, anchor='ctr', adj=30000):
    """Coloured rounded card (vocab pills, item grids, debate panels)."""
    shapes.append(
        f'<p:sp><p:nvSpPr>'
        f'<p:cNvPr id="{_nid()}" name="cc"/>'
        f'<p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
        f'<p:spPr>'
        f'<a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        f'<a:prstGeom prst="roundRect">'
        f'<a:avLst><a:gd name="adj" fmla="val {adj}"/></a:avLst>'
        f'</a:prstGeom>{_fill(fill_col)}<a:ln><a:noFill/></a:ln>'
        f'</p:spPr>'
        f'<p:txBody>'
        f'<a:bodyPr wrap="square" rtlCol="0" anchor="{anchor}" '
        f'lIns="360000" rIns="360000" tIns="180000" bIns="180000">'
        f'<a:normAutofit/></a:bodyPr>'
        f'<a:lstStyle/>{paras_xml}'
        f'</p:txBody></p:sp>'
    )

def _badge(shapes, cx_c, cy_c, r, fill_col, num):
    """Numbered circle badge positioned by centre point."""
    d = r * 2
    shapes.append(
        f'<p:sp><p:nvSpPr>'
        f'<p:cNvPr id="{_nid()}" name="badge"/>'
        f'<p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
        f'<p:spPr>'
        f'<a:xfrm><a:off x="{cx_c-r}" y="{cy_c-r}"/><a:ext cx="{d}" cy="{d}"/></a:xfrm>'
        f'<a:prstGeom prst="ellipse"><a:avLst/></a:prstGeom>{_fill(fill_col)}'
        f'<a:ln><a:noFill/></a:ln></p:spPr>'
        f'<p:txBody>'
        f'<a:bodyPr anchor="ctr" lIns="0" rIns="0" tIns="0" bIns="0"/>'
        f'<a:lstStyle/>'
        f'{_para(str(num), 1600, bold=True, colour=WHITE, align="ctr")}'
        f'</p:txBody></p:sp>'
    )

# ── Background helper ──────────────────────────────────────────────────────────
def _bg(shapes, stype):
    """Apply atmospheric gradient bg + thin accent strip at bottom."""
    col1, col2, accent = _BG.get(stype, _BG_DEFAULT)
    _grad_rect(shapes, 0, 0, W, H, col1, col2)
    strip_h = int(H * 0.055)   # ~6% height accent strip
    _solid_rect(shapes, 0, H - strip_h, W, strip_h, accent, 'strip')

def _strip_h():
    return int(H * 0.055)

# ── Per-slide builders ─────────────────────────────────────────────────────────

def _build_hook(shapes, title, body, act, img):
    """
    Hook: large bold white title + floating card with opening questions/content.
    Dark navy gradient, yellow accent strip.
    """
    _bg(shapes, 'hook')
    # Large white title — outside card, top area
    t = _para(title.upper(), 4400, bold=True, colour=WHITE, align='ctr')
    _txt_box(shapes, 400000, 160000, W - 800000, 1100000, t, anchor='ctr')
    # White card — lower 65%
    card_y  = 1450000
    card_h  = H - card_y - _strip_h() - 60000
    lines   = [l.strip() for l in body.split('\n') if l.strip()][:3]
    xml     = _rich_paras('\n'.join(lines), 2600, NAVY, 'ctr')
    if act:
        xml += _spacer() + _para(act, 1600, italic=True, colour=GREY, align='ctr')
    _float_card(shapes, 400000, card_y, W - 800000, card_h, xml, anchor='ctr', adj=50000)


def _build_vocab(shapes, title, body, act):
    """
    Vocab: dark purple gradient + 2-column grid of LIGHT/PINK cards.
    Words (bold large) + definitions (small italic) if separator found.
    """
    _bg(shapes, 'vocab_intro')
    # Section label — white text at top
    lbl = _para(title, 2200, bold=True, colour=WHITE, align='ctr')
    _txt_box(shapes, 400000, 160000, W - 800000, 650000, lbl, anchor='ctr')
    lines = [l.strip() for l in body.split('\n') if l.strip()][:8]
    n     = len(lines)
    rows  = (n + 1) // 2
    sh    = _strip_h()
    avail_h = H - 950000 - sh - 60000
    avail_w = W - 900000
    cell_w  = (avail_w - 200000) // 2
    cell_h  = min(1050000, max(480000, (avail_h - (rows-1)*120000) // max(rows,1)))
    FILLS   = [LIGHT, PINK]
    for i, line in enumerate(lines):
        col = i % 2
        row = i // 2
        x   = 450000 + col * (cell_w + 200000)
        y   = 950000  + row * (cell_h + 120000)
        # Detect word — definition separator
        split = None
        for sep in [' — ', ' - ', ' – ', ': ']:
            if sep in line:
                split = line.split(sep, 1)
                break
        if split:
            xml = (_para(split[0], 2200, bold=True, colour=NAVY) +
                   _spacer() +
                   _para(split[1], 1700, italic=True, colour=NAVY))
        else:
            xml = _para(line, 2400, bold=True, colour=NAVY, align='ctr')
        _colour_card(shapes, x, y, cell_w, cell_h, FILLS[col%2], xml,
                     anchor='ctr' if not split else 't', adj=35000)
    if act:
        xml = _para(act, 1400, italic=True, colour=WHITE, align='ctr')
        _txt_box(shapes, 400000, H - sh - 300000, W - 800000, 260000, xml)


def _build_info(shapes, title, body, act, img):
    """Info/content: navy gradient + full-width white card with body text."""
    _bg(shapes, 'info')
    lbl = _para(title, 2400, bold=True, colour=WHITE)
    _txt_box(shapes, 500000, 180000, W - 1000000, 680000, lbl, anchor='ctr')
    sh     = _strip_h()
    card_h = H - 1050000 - sh - 60000
    xml    = _rich_paras(body, 2200, NAVY)
    if act:
        xml += _spacer() + _para(act, 1600, italic=True, colour=GREY)
    _float_card(shapes, 400000, 980000, W - 800000, card_h, xml, anchor='t', adj=45000)


def _build_reading(shapes, title, body, act):
    """
    Reading: dark forest green gradient.
    If body has questions section: two side-by-side cards (passage | questions).
    Otherwise: single large card.
    """
    _bg(shapes, 'reading')
    lbl = _para(title, 2200, bold=True, colour=WHITE)
    _txt_box(shapes, 500000, 180000, W - 1000000, 640000, lbl)
    sh     = _strip_h()
    card_y = 920000
    card_h = H - card_y - sh - 80000
    # Split passage from questions
    m = re.search(r'(Questions?:?\s*\n)', body, re.IGNORECASE)
    if m:
        passage   = body[:m.start()].strip()
        questions = body[m.end():].strip()
    elif body.count('\n') >= 3 and '?' in body:
        lines  = [l.strip() for l in body.split('\n') if l.strip()]
        qs     = [l for l in lines if '?' in l or l.startswith(str(len(lines)))]
        non_qs = [l for l in lines if l not in qs]
        passage   = '\n'.join(non_qs)
        questions = '\n'.join(qs)
    else:
        passage, questions = body, ''

    if questions:
        gap    = 180000
        left_w = int(W * 0.52) - 400000 - gap // 2
        right_w = W - left_w - 800000 - gap
        _float_card(shapes, 400000, card_y, left_w, card_h,
                    _rich_paras(passage, 1900, NAVY), anchor='t', adj=40000)
        _float_card(shapes, 400000 + left_w + gap, card_y, right_w, card_h,
                    _rich_paras(questions, 1900, NAVY), anchor='t', adj=40000)
    else:
        xml = _rich_paras(passage, 2100, NAVY)
        if act:
            xml += _spacer() + _para(act, 1600, italic=True, colour=GREY)
        _float_card(shapes, 400000, card_y, W - 800000, card_h, xml,
                    anchor='t', adj=45000)


def _build_discussion(shapes, title, body, act):
    """
    Discussion: dark teal gradient.
    Title outside card (white), numbered badge circles + individual question cards.
    """
    _bg(shapes, 'discussion')
    t = _para(title, 2800, bold=True, colour=WHITE, align='ctr')
    _txt_box(shapes, 400000, 160000, W - 800000, 800000, t, anchor='ctr')
    qs = [re.sub(r'^[\-•*\d\.\)]\s*', '', q.strip())
          for q in body.split('\n') if q.strip()][:5]
    sh       = _strip_h()
    avail_h  = H - 1100000 - sh
    n        = len(qs)
    gap      = 100000
    card_h   = min(1400000, max(500000, (avail_h - (n-1)*gap) // max(n,1)))
    BADGE_R  = 260000
    card_x   = 400000 + BADGE_R * 2 + 120000
    card_w   = W - card_x - 400000
    BCOLS    = [NAVY, RED, '2D1B69', '1A3A4A', '8B0000']
    y = 1060000
    for i, q in enumerate(qs):
        # Draw card, then badge on top (badge is to the LEFT of card, flush)
        _float_card(shapes, card_x, y, card_w, card_h,
                    _rich_paras(q, 2200, NAVY), anchor='ctr', adj=38000)
        _badge(shapes, 400000 + BADGE_R, y + card_h // 2, BADGE_R, BCOLS[i%len(BCOLS)], i+1)
        y += card_h + gap
    if act:
        _txt_box(shapes, 400000, H - sh - 290000, W - 800000, 260000,
                 _para(act, 1400, italic=True, colour=WHITE, align='ctr'))


def _build_grammar(shapes, title, body, act):
    """Grammar: navy-amber gradient. First line as rule (bold large), rest as examples."""
    _bg(shapes, 'grammar_focus')
    lbl = _para(title, 2400, bold=True, colour=WHITE)
    _txt_box(shapes, 500000, 180000, W - 1000000, 680000, lbl)
    lines  = [l.strip() for l in body.split('\n') if l.strip()]
    sh     = _strip_h()
    card_h = H - 1050000 - sh - 60000
    xml = ''
    if lines:
        xml += _para(lines[0], 2600, bold=True, colour=NAVY)
        xml += _spacer() + _spacer()
        for line in lines[1:]:
            xml += _rich_paras(line, 2100, NAVY) + _spacer()
    if act:
        xml += _para(act, 1600, italic=True, colour=GREY)
    _float_card(shapes, 400000, 980000, W - 800000, card_h, xml, anchor='t', adj=45000)


def _build_gap_fill(shapes, title, body, act):
    """Gap fill: alternating LIGHT / PINK cards on teal bg."""
    _bg(shapes, 'gap_fill')
    lbl = _para(title, 2400, bold=True, colour=WHITE)
    _txt_box(shapes, 500000, 180000, W - 1000000, 680000, lbl)
    lines  = [l.strip() for l in body.split('\n') if l.strip()][:7]
    sh     = _strip_h()
    avail_h = H - 1000000 - sh
    n       = len(lines)
    gap     = 80000
    cell_h  = min(780000, max(380000, (avail_h - (n-1)*gap) // max(n,1)))
    FILLS   = [LIGHT, PINK]
    y = 1000000
    for i, line in enumerate(lines):
        _colour_card(shapes, 400000, y, W - 800000, cell_h,
                     FILLS[i%2], _rich_paras(line, 2000, NAVY),
                     anchor='ctr', adj=25000)
        y += cell_h + gap
    if act:
        _txt_box(shapes, 400000, H - sh - 290000, W - 800000, 260000,
                 _para(act, 1400, italic=True, colour=WHITE, align='ctr'))


def _build_task(shapes, title, body, act, img):
    """Task setup/content: dark red gradient. Bold white title + large white card."""
    _bg(shapes, 'task_setup')
    t = _para(title, 3400, bold=True, colour=WHITE, align='ctr')
    _txt_box(shapes, 400000, 160000, W - 800000, 1050000, t, anchor='ctr')
    sh     = _strip_h()
    card_h = H - 1400000 - sh - 60000
    xml    = _rich_paras(body, 2300, NAVY, strip_bullets=True)
    if act:
        xml += _spacer() + _para(act, 1600, italic=True, colour=GREY)
    _float_card(shapes, 400000, 1330000, W - 800000, card_h, xml, anchor='t', adj=45000)


def _build_pair(shapes, title, body, act):
    """Pair / group work: dark teal + stacked white question cards."""
    _bg(shapes, 'pair_work')
    t = _para(title, 2800, bold=True, colour=WHITE, align='ctr')
    _txt_box(shapes, 400000, 160000, W - 800000, 800000, t, anchor='ctr')
    lines   = [re.sub(r'^[\-•*\d\.\)]\s*', '', l.strip())
               for l in body.split('\n') if l.strip()][:4]
    sh      = _strip_h()
    avail_h = H - 1100000 - sh
    n       = len(lines)
    gap     = 110000
    card_h  = min(1450000, max(500000, (avail_h - (n-1)*gap) // max(n,1)))
    y = 1060000
    for line in lines:
        _float_card(shapes, 400000, y, W - 800000, card_h,
                    _rich_paras(line, 2300, NAVY, 'ctr'),
                    anchor='ctr', adj=42000)
        y += card_h + gap
    if act:
        _txt_box(shapes, 400000, H - sh - 290000, W - 800000, 260000,
                 _para(act, 1400, italic=True, colour=WHITE, align='ctr'))


def _build_game(shapes, title, body, act):
    """
    Game: near-black gradient + huge yellow UPPERCASE title outside card,
    then coloured item grid below.
    """
    _bg(shapes, 'game')
    # Massive display title
    t = _para(title.upper(), 5600, bold=True, colour=YELLOW, align='ctr')
    _txt_box(shapes, 300000, 130000, W - 600000, 1350000, t, anchor='ctr')
    lines = [re.sub(r'^[\-•*\d\.\)]\s*', '', l.strip())
             for l in body.split('\n') if l.strip()][:8]
    n     = len(lines)
    sh    = _strip_h()
    area_y = 1580000
    area_h = H - area_y - sh - 100000
    if n <= 3:
        cols, rows = n, 1
    elif n <= 4:
        cols, rows = 2, 2
    elif n <= 6:
        cols, rows = 3, 2
    else:
        cols, rows = 4, 2
    gap_x  = 160000
    gap_y  = 150000
    cell_w = (W - 800000 - (cols-1)*gap_x) // cols
    cell_h = min(1000000, (area_h - (rows-1)*gap_y) // max(rows,1))
    FILLS  = [LIGHT, PINK, LIGHT, PINK, LIGHT, PINK, LIGHT, PINK]
    for i, line in enumerate(lines):
        col = i % cols
        row = i // cols
        x   = 400000 + col * (cell_w + gap_x)
        y   = area_y  + row * (cell_h + gap_y)
        _colour_card(shapes, x, y, cell_w, cell_h, FILLS[i%2],
                     _para(line, 2100, bold=True, colour=NAVY, align='ctr'),
                     anchor='ctr', adj=32000)
    if act:
        _txt_box(shapes, 400000, H - sh - 290000, W - 800000, 260000,
                 _para(act, 1400, italic=True, colour=WHITE, align='ctr'))


def _build_video(shapes, title, body):
    """Video placeholder: near-black dramatic + watch-question cards."""
    _bg(shapes, 'video_placeholder')
    icon = _para('▶  ' + (title or 'Watch the video'), 3200, bold=True, colour=WHITE, align='ctr')
    _txt_box(shapes, 400000, 160000, W - 800000, 1150000, icon, anchor='ctr')
    lines = [l.strip().lstrip('-•').strip() for l in body.split('\n') if l.strip()][:4]
    sh    = _strip_h()
    avail_h = H - 1500000 - sh
    n     = max(len(lines), 1)
    gap   = 120000
    card_h = min(950000, max(480000, (avail_h - (n-1)*gap) // n))
    y = 1450000
    for line in lines:
        _float_card(shapes, 1000000, y, W - 2000000, card_h,
                    _para(line, 2300, colour=NAVY, align='ctr'),
                    anchor='ctr', adj=48000)
        y += card_h + gap


def _build_debate(shapes, title, body, act):
    """
    Debate: two side-by-side cards — left white (pro), right dark navy (con).
    Bold white title above.
    """
    _bg(shapes, 'debate')
    lbl = _para(title, 2800, bold=True, colour=WHITE, align='ctr')
    _txt_box(shapes, 400000, 160000, W - 800000, 780000, lbl, anchor='ctr')
    lines = [l.strip() for l in body.split('\n') if l.strip()]
    mid   = max(1, len(lines) // 2)
    left  = '\n'.join(lines[:mid])
    right = '\n'.join(lines[mid:])
    sh    = _strip_h()
    half_w = (W - 1000000) // 2
    card_h = H - 1080000 - sh - 60000
    _float_card(shapes, 400000, 1020000, half_w, card_h,
                _rich_paras(left, 2100, NAVY), adj=40000)
    _colour_card(shapes, 400000 + half_w + 200000, 1020000, half_w, card_h,
                 NAVY, _rich_paras(right, 2100, WHITE), anchor='t', adj=40000)
    if act:
        _txt_box(shapes, 400000, H - sh - 290000, W - 800000, 260000,
                 _para(act, 1400, italic=True, colour=WHITE, align='ctr'))


def _build_standard(shapes, title, body, act, img):
    """Fallback: navy gradient + white card."""
    _bg(shapes, 'standard')
    lbl = _para(title, 2400, bold=True, colour=WHITE)
    _txt_box(shapes, 500000, 180000, W - 1000000, 680000, lbl)
    sh     = _strip_h()
    card_h = H - 1050000 - sh - 60000
    xml    = _rich_paras(body, 2200, NAVY)
    if act:
        xml += _spacer() + _para(act, 1600, italic=True, colour=GREY)
    _float_card(shapes, 400000, 980000, W - 800000, card_h, xml, anchor='t', adj=45000)


# ── Slide XML assembly ─────────────────────────────────────────────────────────
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

def _gen_slide_xml(sd):
    _sid[0] = 100
    stype = sd.get('slide_type', 'info')
    title = sd.get('title', '')
    body  = sd.get('content', '')
    act   = sd.get('activity_instruction', '')
    img   = sd.get('image_placeholder', '')
    shapes = []

    if   stype == 'hook':
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
    elif stype == 'grammar_focus':
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


# ── Template slide modifiers (unchanged from v4) ───────────────────────────────
def _set_t(xml, old, new):
    return xml.replace(f'<a:t>{_esc(old)}</a:t>', f'<a:t>{_esc(new)}</a:t>', 1)

def _modify_slide1(xml, lesson):
    title = lesson.get('lesson_title', 'LESSON TITLE').upper()
    tl    = lesson.get('lesson_type_label', 'LANG')
    lv    = lesson.get('level_label', 'Level 3')
    wk    = lesson.get('week', 'A')
    meta  = f'WEEK {wk} | PURPOSE | {tl} | {lv.upper()}'
    xml   = re.sub(
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
    xml   = xml.replace(_esc(FOCUS_OLD), _esc(focus), 1)
    xml   = xml.replace(_esc(OBJ_OLD),   _esc(objvs), 1)
    xml   = re.sub(r'<a:t>None\.</a:t>', f'<a:t>{_esc(extra)}</a:t>', xml, count=1)
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
        xml   = xml.replace(f'<a:t>{old_t}</a:t>', f'<a:t>{_esc(new_t)}</a:t>', 1)
    return xml

def _modify_materials(xml, lesson):
    notes = lesson.get('materials_notes', 'None.')
    xml   = re.sub(r'<a:t>None\.</a:t>', f'<a:t>{_esc(notes)}</a:t>', xml, count=1)
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

        slides_dir   = os.path.join(unpacked, 'ppt', 'slides')
        prs_xml_path = os.path.join(unpacked, 'ppt', 'presentation.xml')

        # 2. Fix broken rels
        _fix_rels(unpacked)

        # 3. Modify structural slides
        steps = lesson.get('teacher_steps', [])
        mods  = [
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
        next_id    = max(existing_ids) + 1 if existing_ids else 600
        new_sld_ids = []

        for sd in student_slides[1:]:
            r = subprocess.run(
                ['python3', os.path.join(SCRIPTS_DIR,'add_slide.py'),
                 unpacked, 'slide5.xml'],
                capture_output=True, text=True, check=True)
            lines   = r.stdout.strip().split('\n')
            new_fname = lines[0].split()[1]
            rid_m   = re.search(r'r:id="([^"]+)"', lines[1])
            if rid_m:
                new_sld_ids.append(f'<p:sldId id="{next_id}" r:id="{rid_m.group(1)}"/>')
                next_id += 1
            open(os.path.join(slides_dir, new_fname),'w').write(_gen_slide_xml(sd))

        # 6. Reorder sldIdLst
        prs_xml = open(prs_xml_path).read()
        mat_m   = re.search(r'<p:sldId[^>]*r:id="rId7"[^/]*/>', prs_xml)
        nts_m   = re.search(r'<p:sldId[^>]*r:id="rId8"[^/]*/>', prs_xml)
        mat_s   = mat_m.group() if mat_m else ''
        nts_s   = nts_m.group() if nts_m else ''
        prs_xml = prs_xml.replace(mat_s,'',1).replace(nts_s,'',1)
        ins     = '\n'.join(f'    {el}' for el in new_sld_ids)
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
        r   = subprocess.run(
            ['python3', os.path.join(SCRIPTS_DIR,'office','pack.py'),
             unpacked, out, '--original', template_path],
            capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f'pack.py failed:\n{r.stdout}\n{r.stderr}')

        return open(out,'rb').read()
