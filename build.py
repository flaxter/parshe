#!/usr/bin/env python3
"""Build the parshe-fun-der-vokh site: site/index.html + site/<slug>.html (+ PDF when --pdf).
Data: data/parshes.json (all 54, order + Yiddish names), data/parshes_hebcal.json (this year's dates/ranges),
data/parsha/<slug>.json (page config), data/kids/<slug>.md (children's text), data/yehoyesh/<slug>.*.json (Sefaria)."""
import glob, json, os, re, shutil, sys, html, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
D = lambda *p: os.path.join(HERE, 'data', *p)
SITE = os.path.join(HERE, 'docs')   # GitHub Pages serves /docs
MONTHS_YI = ['יאַנואַר','פֿעברואַר','מאַרץ','אַפּריל','מײַ','יוני','יולי','אויגוסט','סעפּטעמבער','אָקטאָבער','נאָוועמבער','דעצעמבער']
BOOKS = [('בראשית','Breyshis',0,12),('שמות','Shmoys',12,23),('ויקרא','Vayikro',23,33),('במדבר','Bamidber',33,43),('דברים','Dvorim',43,54)]
esc = html.escape

def sheymes(s):
    """Yehoyesh prints the Tetragrammaton; a handout for shul should not (genizah). Print ה׳ instead."""
    return s.replace('יהוה', 'ה׳')

def flatten(part):
    """Sefaria v3 text -> list of (chapter, verse, text)."""
    sec = [int(x) for x in part['sections']]
    c0, v0 = sec[0], (sec[1] if len(sec) > 1 else 1)
    t = part['text']
    out = []
    if isinstance(t, str):
        out.append((c0, v0, t))
    elif t and isinstance(t[0], str):
        for i, s in enumerate(t): out.append((c0, v0 + i, s))
    else:
        for ci, ch in enumerate(t):
            vs = v0 if ci == 0 else 1
            for i, s in enumerate(ch): out.append((c0 + ci, vs + i, s))
    return [(c, v, re.sub(r'\s*[–—-]\s*$', '', re.sub(r'<[^>]+>', '', s).replace('\xa0', ' ').strip())) for c, v, s in out if s]

def load_yehoyesh(slug, kind):
    fn = D('yehoyesh', f'{slug}.{kind}.json')
    if not os.path.exists(fn): return None
    d = json.load(open(fn))
    verses = []
    for part in d['parts']: verses += flatten(part)
    return {'ref': d['ref'], 'verses': verses, 'book': d['parts'][0]['ref'].rsplit(' ', 1)[0]}

def parse_ref(ref):
    m = re.match(r'(.+?) (\d+):(\d+)(?:-(?:(\d+):)?(\d+))?$', ref)
    book, c1, v1, c2, v2 = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4), m.group(5)
    c2 = int(c2) if c2 else c1
    v2 = int(v2) if v2 else v1
    return book, (c1, v1), (c2, v2)

def pick_verses(tor, ref):
    book, a, b = parse_ref(ref)
    return [(c, v, s) for c, v, s in tor['verses'] if a <= (c, v) <= b]

HEB_NUM = {1:'א',2:'ב',3:'ג',4:'ד',5:'ה',6:'ו',7:'ז',8:'ח',9:'ט',10:'י',20:'כ',30:'ל',40:'מ',50:'נ',60:'ס',70:'ע',80:'פ',90:'צ',100:'ק'}
def heb(n):
    if n == 15: return 'טו'
    if n == 16: return 'טז'
    s = ''
    for k in (100, 90, 80, 70, 60, 50, 40, 30, 20):
        while n >= k: s += HEB_NUM[k]; n -= k
    if n >= 10: s += HEB_NUM[10]; n -= 10
    if n: s += HEB_NUM[n]
    return s

def md_story(path):
    """Tiny markdown: '## ' headings, blank-line paragraphs, '| ' lines = verse kept line by line. Returns list of sections {title, paras}."""
    secs = []
    cur = None
    for block in re.split(r'\n\s*\n', open(path, encoding='utf-8').read().strip()):
        block = block.strip()
        if block.startswith('## '):
            cur = {'title': block[3:].strip(), 'paras': []}; secs.append(cur)
        else:
            if cur is None: cur = {'title': '', 'paras': []}; secs.append(cur)
            lines = [l.strip() for l in block.splitlines()]
            if all(l.startswith('| ') for l in lines):   # verse set line by line in the book
                cur['paras'].append('\n'.join(l[2:] for l in lines))
            else:
                cur['paras'].append(' '.join(lines))
    return secs

def yi_date(iso):
    d = datetime.date.fromisoformat(iso)
    return f'שבת, {d.day}טן {MONTHS_YI[d.month-1]} {d.year}'

CSS = r'''
@font-face{font-family:"Frank Ruhl Libre";src:url(fonts/FrankRuhlLibre.ttf) format("truetype");font-weight:300 900;}
@font-face{font-family:"Noto Sans Hebrew";src:url(fonts/NotoSansHebrew.ttf) format("truetype");font-weight:100 900;font-stretch:62.5% 100%;}
:root{--ink:#2b2219;--sub:#7a6a58;--paper:#fffaf2;--accent:#b5531c;--accent2:#1f6f8b;--rule:#e2d5c2;}
*{box-sizing:border-box}
html{direction:rtl}
body{margin:0;background:#efe6d6;color:var(--ink);font-family:"Frank Ruhl Libre",Georgia,serif;font-size:20px;line-height:1.55}
.sheet{background:var(--paper);max-width:800px;margin:18px auto;padding:34px 40px 40px;box-shadow:0 4px 24px rgba(60,40,10,.14);border-radius:6px}
nav.top{font-family:"Noto Sans Hebrew",sans-serif;font-size:15px;display:flex;gap:14px;align-items:center;justify-content:space-between;margin:-10px 0 18px;color:var(--sub)}
nav.top a{color:var(--accent2);text-decoration:none;font-weight:600}
nav.top button{font:inherit;font-weight:700;background:var(--accent);color:#fff;border:0;border-radius:999px;padding:7px 16px;cursor:pointer}
nav.top a.pdf{display:inline-block;background:#fff;border:2px solid var(--accent);color:var(--accent);border-radius:999px;padding:5px 14px;margin-inline-end:6px}
header.title{text-align:center;border-bottom:3px double var(--rule);padding-bottom:12px;margin-bottom:18px}
.kicker{font-family:"Noto Sans Hebrew",sans-serif;font-size:14px;letter-spacing:.06em;color:var(--sub);text-transform:uppercase}
h1{font-family:"Noto Sans Hebrew",sans-serif;font-weight:800;font-size:54px;margin:2px 0 0;line-height:1.1;color:var(--accent)}
.sub{font-family:"Noto Sans Hebrew",sans-serif;font-size:17px;color:var(--sub);margin-top:6px}
.sub .en{direction:ltr;unicode-bidi:isolate}
.sub.variant{color:var(--accent2);font-weight:700}
.alts{font-family:"Noto Sans Hebrew",sans-serif;font-size:14px;color:var(--sub);margin:-8px 0 14px}
.story p.v{margin:0 0 .35em}
.story .n{font-family:"Noto Sans Hebrew",sans-serif;font-size:11px;color:var(--sub);margin-left:5px;vertical-align:super}
figure.hero{margin:0 0 16px;text-align:center}
figure.hero img{max-width:100%;max-height:360px;border-radius:8px;box-shadow:0 2px 10px rgba(0,0,0,.18)}
figure.hero figcaption{font-size:14px;color:var(--sub);margin-top:6px;line-height:1.35}
h2{font-family:"Noto Sans Hebrew",sans-serif;font-weight:700;font-size:25px;color:var(--accent2);margin:22px 0 6px}
.story p{margin:0 0 .55em;text-align:right}
.story p.said{margin-right:1.2em}
.story p.poem{margin-right:2.5em}
.story p.fn{font-size:14px;color:var(--sub);border-top:1px solid var(--rule);padding-top:4px;margin-top:10px}
.box{border:2px solid var(--rule);border-radius:12px;padding:12px 18px 14px;margin:18px 0;background:#fff}
.box h2{margin-top:0;font-size:21px}
.verse{margin:0 0 .5em}
.verse .ref{font-family:"Noto Sans Hebrew",sans-serif;font-size:13px;color:var(--sub);margin-inline-end:8px;white-space:nowrap}
ol.q{padding-right:1.3em;margin:0}
ol.q li{margin:0 0 .5em}
ol.q .en{display:block;font-family:"Noto Sans Hebrew",sans-serif;font-size:13px;color:var(--sub);direction:ltr;text-align:left}
table.gl{width:100%;border-collapse:collapse;font-size:18px}
table.gl td{padding:2px 8px;border-bottom:1px dotted var(--rule);vertical-align:baseline}
table.gl td.w{font-weight:700;white-space:nowrap}
table.gl td.r{direction:ltr;text-align:left;font-family:"Noto Sans Hebrew",sans-serif;font-size:15px;color:var(--accent);white-space:nowrap}
table.gl td.g{direction:ltr;text-align:left;font-family:"Noto Sans Hebrew",sans-serif;font-size:13px;color:var(--sub);width:42%}
.two{align-items:start}
.box .note{font-family:"Noto Sans Hebrew",sans-serif;font-size:11px;color:var(--sub);margin-top:6px}
.draw{border:2px dashed var(--accent);border-radius:12px;height:230px;position:relative;margin:18px 0}
.draw span{position:absolute;top:8px;right:14px;font-family:"Noto Sans Hebrew",sans-serif;font-size:15px;color:var(--accent)}
footer.src{font-family:"Noto Sans Hebrew",sans-serif;font-size:11.5px;color:var(--sub);border-top:1px solid var(--rule);margin-top:22px;padding-top:8px;line-height:1.45}
footer.src a{color:var(--accent2)}
details.grown{margin-top:26px;font-size:18px}
details.grown summary{cursor:pointer;font-family:"Noto Sans Hebrew",sans-serif;font-weight:700;color:var(--accent2);font-size:18px}
details.grown .v{margin:0 0 .3em}
details.grown .n{font-family:"Noto Sans Hebrew",sans-serif;font-size:12px;color:var(--sub);margin-left:4px}
.two{display:grid;grid-template-columns:1fr 1fr;gap:0 20px}
@media (max-width:600px){.sheet{padding:22px 16px;margin:0;border-radius:0}h1{font-size:40px}body{font-size:18px}.two{grid-template-columns:1fr}}
@media print{
 @page{size:A4;margin:12mm 14mm 13mm}
 body{background:#fff;font-size:13pt;line-height:1.4}
 .sheet{box-shadow:none;max-width:none;margin:0;padding:0;border-radius:0;background:#fff}
 nav.top,details.grown,.no-print{display:none!important}
 h1{font-size:34pt}h2{font-size:16pt;margin:12pt 0 3pt;page-break-after:avoid}
 header.title{margin-bottom:9pt;padding-bottom:6pt}
 figure.hero{float:left;width:46%;margin:0 0 6pt 0;padding-left:0}
 figure.hero img{max-height:72mm;box-shadow:none;border-radius:4px}
 figure.hero figcaption{font-size:8.5pt}
 .story{text-align:right}
 .box{break-inside:avoid;margin:8pt 0;padding:7pt 11pt 8pt;border-color:#bbb;border-radius:8px}
 .box h2{font-size:14pt}
 .page2{}
 .draw{height:96mm;break-inside:avoid}
 .two{break-inside:avoid}
 table.gl{font-size:11.5pt}
 table.gl td{padding:1pt 6pt}
 .gloss{break-inside:avoid}
 .two{break-inside:avoid}
 footer.src{font-size:8pt}
 a{color:inherit;text-decoration:none}
}
'''

def render_parsha(p, cfg, heb_info, prev_p, next_p, out_name=None, siblings=()):
    """out_name: file stem (slug, or slug--variant). siblings: [(label, stem)] other variants of this parsha."""
    slug = p['slug']; out_name = out_name or slug
    tor = load_yehoyesh(slug, 'torah'); haf = load_yehoyesh(slug, 'haftarah')
    extract = cfg.get('yehoyesh_extract')   # list of refs: the story IS Yehoyesh's text, verbatim from Sefaria
    story = None if extract else md_story(D('kids', cfg.get('kids', f'{out_name}.md')))
    variant_label = cfg.get('variant_label', '')
    hero = [i for i in cfg.get('images', []) if i.get('place') == 'hero']
    date_line = yi_date(heb_info['date']) if heb_info else ''
    torah_ref = heb_info['torah'] if heb_info else (tor['ref'] if tor else '')
    if torah_ref:
        _b, _a, _z = parse_ref(torah_ref)
        torah_yi = f'{p.get("book_yi", "")} {heb(_a[0])}:{heb(_a[1])}–{heb(_z[0])}:{heb(_z[1])}'.strip()
    else:
        torah_yi = ''
    o = []
    o.append(f'''<!DOCTYPE html><html lang="yi" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>פּרשת {esc(p["yi"])} · {esc(p["translit"])}</title><style>{CSS}</style></head><body><div class="sheet">
<nav class="top"><span>{'<a href="'+prev_p['slug']+'.html">→ '+esc(prev_p['yi'])+'</a>' if prev_p else ''}</span>
<a href="index.html">אַלע פּרשיות</a><span><a class="pdf" href="{out_name}.pdf">⬇ PDF</a> <button onclick="window.print()">🖨 דרוקן</button></span>
<span>{'<a href="'+next_p['slug']+'.html">'+esc(next_p['yi'])+' ←</a>' if next_p else ''}</span></nav>
<header class="title"><div class="kicker">די פּרשה פֿון דער װאָך · Parshe fun der vokh</div>
<h1>פּרשת {esc(p["yi"])}</h1>
<div class="sub">{esc(p["translit"])} · {esc(torah_yi)} · <span class="en">{esc(torah_ref)}</span>{(' · '+date_line) if date_line else ''}</div>
{('<div class="sub variant">נוסח: '+esc(variant_label)+'</div>') if variant_label else ''}</header>''')
    if siblings:
        o.append('<div class="alts no-print">אַן אַנדער נוסח פֿון דער פּרשה: ' + ' · '.join(f'<a href="{st}.html">{esc(lb)}</a>' for lb, st in siblings) + '</div>')
    if hero:
        im = hero[0]
        o.append(f'<figure class="hero"><img src="img/{im["file"]}" alt=""><figcaption>{esc(im["caption"])}</figcaption></figure>')
    o.append('<div class="story">')
    if extract:
        for ref in extract:
            ch = None
            for c, v, txt in pick_verses(tor, ref):
                if c != ch:
                    ch = c; o.append(f'<h2>{esc(p.get("book_yi") or tor["book"])} {heb(c)}</h2>')
                o.append(f'<p class="v"><span class="n">{heb(v)}</span>{esc(sheymes(txt))}</p>')
    for s in (story or []):
        if s['title']: o.append(f'<h2>{esc(s["title"])}</h2>')
        for para in s['paras']:
            if para.startswith('::: '):
                o.append(f'<p class="fn">{esc(para[4:])}</p>'); continue
            if '\n' in para:
                o.append('<p class="poem">' + '<br>'.join(esc(l) for l in para.split('\n')) + '</p>'); continue
            cls = ' class="said"' if para.startswith('—') else ''
            o.append(f'<p{cls}>{esc(para)}</p>')
    o.append('</div>')
    o.append('<div class="page2">')
    # Yehoyesh verses
    if tor and cfg.get('verses'):
        o.append('<div class="box"><h2>פּסוקים פֿון יהואשס תּנ״ך</h2>')
        for vv in cfg['verses']:
            vs = pick_verses(tor, vv['ref'])
            txt = ' '.join(sheymes(s) for c, v, s in vs)
            o.append(f'<p class="verse"><span class="ref">({esc(vv["label"])})</span>{esc(txt)}</p>')
        o.append('</div>')
    gfn = D('glossary', f'{out_name}.json')
    if os.path.exists(gfn):
        gl = [g for g in json.load(open(gfn)) if g['source'] != 'MISSING']
        o.append('<div class="box gloss"><h2>לשון־קודש־װערטער אין דער מעשׂה</h2><div class="two">')
        half = (len(gl) + 1) // 2
        for col in (gl[:half], gl[half:]):
            o.append('<table class="gl">')
            for g in col:
                o.append(f'<tr><td class="w">{esc(g["word"])}</td><td class="r">{esc(g["roman"])}</td><td class="g">{esc(g.get("gloss") or "")}</td></tr>')
            o.append('</table>')
        o.append('</div><div class="note">אַרױסרעד לױט ייִװאָ־טראַנסקריפּציע; װערטער אױטאָמאַטיש געפֿונען אין דער מעשׂה</div></div>')
    o.append(f'<div class="draw"><span>✏️ {esc(cfg.get("draw_prompt","מאָל דאָ"))}</span></div>')
    # sources
    src = []
    for ks in cfg.get('kids_sources', []):
        link = f'https://archive.org/details/{ks["ia"]}' + (f'/page/n{ks["leaf"]}/mode/1up' if ks.get('leaf') else '')
        src.append(f'די מעשׂה („{"“, „".join(ks["parts"])}“): {esc(ks["label"])} — <a href="{link}">דאָס בוך בײַם ייִדישן ביכער־צענטער / archive.org</a>')
    if extract:
        src.append('די מעשׂה: יהואשס תּנ״ך־איבערזעצונג, װאָרט בײַ װאָרט — ' + esc(cfg.get('extract_label') or ', '.join(extract)))
    if tor:
        src.append('פּסוקים: יהואשס תּנ״ך־איבערזעצונג (1941), דיגיטאַליזירט דורכן „יהואש־פּראָיעקט“ (ל. פּראַגער), CC0 דורך Open Siddur און <a href="https://www.sefaria.org/texts">Sefaria</a>. דער שם־הוויה װערט דאָ געדרוקט װי ה׳.')
    for im in cfg.get('images', []):
        src.append(f'בילד: {esc(im["credit"])}')
    o.append('<footer class="src">' + '<br>'.join(src) + '</footer>')
    o.append('</div>')  # page2
    # grown-ups: full Yehoyesh
    if tor:
        o.append('<details class="grown"><summary>פֿאַר די גרויסע: די גאַנצע פּרשה בײַ יהואשן</summary>')
        ch = None
        for c, v, s in tor['verses']:
            if c != ch:
                ch = c; o.append(f'<h2>{esc(p.get("book_yi") or tor["book"])} {heb(c)}</h2>')
            o.append(f'<p class="v"><span class="n">{heb(v)}</span>{esc(sheymes(s))}</p>')
        if haf:
            o.append(f'<h2>הפֿטרה: {esc(haf["ref"])}</h2>')
            for c, v, s in haf['verses']:
                o.append(f'<p class="v"><span class="n">{heb(c)}:{heb(v)}</span>{esc(sheymes(s))}</p>')
        o.append('</details>')
    o.append('</div></body></html>')
    return '\n'.join(o)

def render_index(parshes, built, heb):
    cards = []
    for bi, (byi, ben, a, b) in enumerate(BOOKS):
        cards.append(f'<h2>{byi} <span class="en">{ben}</span></h2><div class="grid">')
        for p in parshes[a:b]:
            info = heb.get(p['hebcal'])
            date = info['date'] if info else ''
            vs = built.get(p['slug'])   # list of (label, stem); label '' = the default page
            if vs and vs[0][0] == '':
                stem = vs[0][1]
                extra = ''.join(f'<a class="alt" href="{st}.html">{esc(lb)}</a> <a class="pdflink" href="{st}.pdf">⬇</a><br>' for lb, st in vs[1:])
                cards.append(f'<span class="card on" data-slug="{p["slug"]}" data-date="{date}" data-page="{stem}.html" data-pdf="{stem}.pdf"><a href="{stem}.html"><b>{esc(p["yi"])}</b><i>{esc(p["translit"])}</i></a><a class="pdflink" href="{stem}.pdf">⬇ PDF</a>{("<span class=alts>"+extra+"</span>") if extra else ""}</span>')
            elif vs:
                rows = ''.join(f'<a class="alt" href="{st}.html">{esc(lb)}</a> <a class="pdflink" href="{st}.pdf">⬇</a><br>' for lb, st in vs)
                cards.append(f'<span class="card on" data-slug="{p["slug"]}" data-date="{date}" data-page="{vs[0][1]}.html"><b>{esc(p["yi"])}</b><i>{esc(p["translit"])}</i><span class="alts">{rows}</span></span>')
            else:
                cards.append(f'<span class="card" data-slug="{p["slug"]}" data-date="{date}"><b>{esc(p["yi"])}</b><i>{esc(p["translit"])}</i></span>')
        cards.append('</div>')
    css = CSS + '''
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:10px;margin-bottom:10px}
.card{display:block;border:2px solid var(--rule);border-radius:12px;padding:10px 8px;text-align:center;text-decoration:none;color:var(--sub);background:#f6efe3}
.card b{display:block;font-family:"Noto Sans Hebrew",sans-serif;font-size:21px;color:inherit}
.card i{font-style:normal;font-size:12px;font-family:"Noto Sans Hebrew",sans-serif}
.card.on{background:#fff;color:var(--ink);border-color:var(--accent2)}
.card a{text-decoration:none;color:inherit;display:block}
.card .pdflink{margin-top:6px;font-family:"Noto Sans Hebrew",sans-serif;font-size:12px;color:var(--accent);font-weight:700}
.card.now{outline:4px solid var(--accent);outline-offset:2px}
.card .alts{display:block;margin-top:6px;font-family:"Noto Sans Hebrew",sans-serif;font-size:13px;line-height:1.6}
.card .alts a.alt{display:inline;color:var(--accent2);font-weight:700}.card .alts a.pdflink{display:inline;margin:0 4px}
h2 .en{font-size:14px;color:var(--sub);font-weight:400}
#now{border:2px solid var(--accent);border-radius:14px;padding:12px 18px;margin:0 0 18px;font-family:"Noto Sans Hebrew",sans-serif}
#now a{color:var(--accent);font-weight:800;font-size:28px;text-decoration:none}
'''
    alias = {p['hebcal']: p['slug'] for p in parshes}
    return f'''<!DOCTYPE html><html lang="yi" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>פּרשה פֿון דער װאָך</title><style>{css}</style></head><body><div class="sheet">
<header class="title"><div class="kicker">Parshe fun der vokh · far kinder</div><h1>די פּרשה פֿון דער װאָך</h1>
<div class="sub">די װאָכעדיקע סדרה אויף ייִדיש פֿאַר קינדער — צום לייענען, צום דרוקן, צום מיטנעמען אין שול</div></header>
<div id="now">די װאָך: <a id="nowlink" href="#">…</a> <span id="nowdate" style="color:var(--sub);font-size:14px"></span> <a id="nowpdf" class="pdflink" href="#" style="display:none;margin-inline-start:12px">⬇ PDF</a></div>
{''.join(cards)}
<footer class="src">מעשׂיות פֿון ייִדישע קינדער־חומשים (ייִדישער ביכער־צענטער), פּסוקים פֿון יהואשס תּנ״ך (CC0 דורך Sefaria), בילדער פֿון מיטל־עלטערלעכע ייִדישע כּתבֿ־ידן (public domain). <span style="direction:ltr;unicode-bidi:isolate">Built from <a href="https://github.com/flaxter/parshe">flaxter/parshe</a>.</span></footer>
</div>
<script>
const ALIAS={json.dumps(alias)};
const norm=s=>s.toLowerCase().replace(/[^a-z]/g,'');
function mark(slug,label,date){{const a=document.getElementById('nowlink');const pp=document.getElementById('nowpdf');const c=document.querySelector('.card[data-slug="'+slug+'"]');if(c&&c.dataset.pdf){{pp.href=c.dataset.pdf;pp.style.display='inline';}}
 if(c)c.classList.add('now'); a.textContent=c?c.querySelector('b').textContent:label; a.href=(c&&c.dataset.page)||'#'; if(date)document.getElementById('nowdate').textContent='('+date+')';}}
function fallback(){{const today=new Date().toISOString().slice(0,10);let best=null;document.querySelectorAll('.card[data-date]').forEach(c=>{{const d=c.dataset.date;if(d&&d>=today&&(!best||d<best.dataset.date))best=c;}});if(best)mark(best.dataset.slug,best.dataset.slug,best.dataset.date);}}
fetch('https://www.sefaria.org/api/calendars?diaspora=1').then(r=>r.json()).then(d=>{{const it=d.calendar_items.find(i=>i.title.en==='Parashat Hashavua');if(!it)return fallback();
 const name=it.displayValue.en;const parts=name.split('-');let hit=null;for(const k in ALIAS){{if(parts.some(x=>norm(x)===norm(k))){{hit=ALIAS[k];break;}}}}
 if(hit)mark(hit,name,d.date);else fallback();}}).catch(fallback);
</script></body></html>'''

def main():
    parshes = json.load(open(D('parshes.json')))
    heb = json.load(open(D('parshes_hebcal.json')))
    os.makedirs(SITE, exist_ok=True)
    for sub in ('img', 'fonts'):
        dst = os.path.join(SITE, sub); os.makedirs(dst, exist_ok=True)
        for f in os.listdir(os.path.join(HERE, sub)): shutil.copy2(os.path.join(HERE, sub, f), dst)
    def configs(slug):
        """[(label, stem, cfg)]: data/parsha/<slug>.json is the default page (label ''); data/parsha/<slug>--<variant>.json are variants."""
        out = []
        if os.path.exists(D('parsha', f'{slug}.json')): out.append(('', slug, json.load(open(D('parsha', f'{slug}.json')))))
        for fn in sorted(glob.glob(D('parsha', f'{slug}--*.json'))):
            cfg = json.load(open(fn)); stem = os.path.basename(fn)[:-5]
            out.append((cfg.get('variant_label') or stem.split('--', 1)[1], stem, cfg))
        return out
    allcfg = {p['slug']: configs(p['slug']) for p in parshes}
    built = {k: [(lb, st) for lb, st, _ in v] for k, v in allcfg.items() if v}
    def nav_entry(q):   # neighbour link target: its default page, else its first variant
        return dict(q, slug=allcfg[q['slug']][0][1]) if allcfg.get(q['slug']) else None
    for i, p in enumerate(parshes):
        if not allcfg[p['slug']]: continue
        prev_p = next((nav_entry(q) for q in reversed(parshes[:i]) if allcfg.get(q['slug'])), None)
        next_p = next((nav_entry(q) for q in parshes[i+1:] if allcfg.get(q['slug'])), None)
        for lb, stem, cfg in allcfg[p['slug']]:
            sib = [(l2 or 'הויפּט־נוסח', s2) for l2, s2, _ in allcfg[p['slug']] if s2 != stem]
            out = render_parsha(p, cfg, heb.get(p['hebcal']), prev_p, next_p, out_name=stem, siblings=sib)
            open(os.path.join(SITE, f'{stem}.html'), 'w', encoding='utf-8').write(out)
            print('built', stem)
            if '--pdf' in sys.argv:
                import weasyprint
                doc = weasyprint.HTML(string=out, base_url=SITE + '/').render()
                pdf = os.path.join(SITE, f'{stem}.pdf'); doc.write_pdf(pdf)
                print('  pdf', pdf, len(doc.pages), 'pages')
    open(os.path.join(SITE, 'index.html'), 'w', encoding='utf-8').write(render_index(parshes, built, heb))
    print('index with', len(built), 'built')

if __name__ == '__main__':
    main()
