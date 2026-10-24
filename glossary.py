#!/usr/bin/env python3
"""Loshn-koydesh glossary for a parsha's children's text.
Detects Hebrew-origin words (the ones a child can't sound out), romanizes them (YIVO) and glosses them:
  1. Bleaman's `yiddish` package (offline list of loshn-koydesh spellings -> pronunciation)
  2. Refoyl Finkel's online dictionary (romanization + English gloss), cached in data/finkel_cache.json
  3. data/names.json for biblical names neither knows (hand-written, flagged)
Usage: uv run --python 3.11 --with yiddish --with "setuptools<70" python glossary.py <slug> [...]
Writes data/glossary/<slug>.json = [{word, roman, gloss, source, count}]"""
import json, os, re, sys, time, urllib.request, urllib.parse, html
import yiddish
HERE = os.path.dirname(os.path.abspath(__file__))
D = lambda *p: os.path.join(HERE, 'data', *p)
CACHE = D('finkel_cache.json')
VOWELS = set('aeiou')
NIQQUD = re.compile(r'[֑-ׇ]')
UA = {'User-Agent': 'parshe-fun-der-vokh glossary (flaxter@gmail.com), ~1 req/s, cached'}

def naive(word):
    """letter-by-letter romanization with LK respelling switched off"""
    return yiddish.transliterate(word, loshn_koydesh=False)

def is_lk(word):
    bare = NIQQUD.sub('', word)
    if len(bare) < 2: return False
    with_lk = yiddish.transliterate(word, loshn_koydesh=True)
    without = naive(word)
    if with_lk != without: return True            # Bleaman respelled it -> known LK word
    # no vowel letters at all in the romanization -> unpointed Hebrew spelling (name/place) the list doesn't know
    return not (set(without) & VOWELS)

def finkel(word):
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    if word in cache: return cache[word]
    data = urllib.parse.urlencode({'word': word, 'wholeWord': 'on'}).encode()
    req = urllib.request.Request('https://www.cs.uky.edu/~raphael/yiddish/dictionary.cgi', data=data, headers=UA)
    t = urllib.request.urlopen(req, timeout=60).read().decode('utf-8', 'replace')
    time.sleep(1.0)
    txt = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', t)))
    m = re.search(r'Converting \S+ to (\S+)\s+(.*?)(?=A word or phrase|This dictionary|$)', txt)
    out = None
    if m:
        roman, body = m.group(1), m.group(2)
        # first entry whose Hebrew spelling matches our word (without niqqud)
        bare = NIQQUD.sub('', word).replace('־', '-')
        mm = re.search(re.escape(roman) + r'\s*\(\s*' + re.escape(bare) + r'\s*\)\s*(.*?)(?=\s\S+\s*\(\s*[א-ת]|$)', body)
        if mm:
            desc = mm.group(1)
            desc = re.sub(r'^(plural \S+\(.*?\),?\s*|gender [mfn],?\s*|has diminutive,?\s*|noun,.*?,\s*)*', '', desc).strip(' ,')
            out = {'roman': roman, 'gloss': desc[:80], 'source': 'finkel'}
    cache[word] = out
    json.dump(cache, open(CACHE, 'w'), ensure_ascii=False, indent=0)
    return out

def showdefs_glosses(slug, text):
    """Finkel's gloss displayer: whole text in, {word: gloss} out. Cached per parsha."""
    fn = D('glossary', f'{slug}.finkel.json')
    if os.path.exists(fn): return json.load(open(fn))
    data = urllib.parse.urlencode({'Text': text}).encode()
    req = urllib.request.Request('https://www.cs.uky.edu/~raphael/yiddish/showDefs.cgi', data=data, headers=UA)
    t = urllib.request.urlopen(req, timeout=120).read().decode('utf-8', 'replace')
    pairs = re.findall(r"<a id='a' class='tooltip'>([^<]+)<span class='info'>\u202a?([^<]*)</span></a>", t)
    out = {}
    for w, g in pairs:
        out.setdefault(w.strip(), html.unescape(g).strip())
    json.dump(out, open(fn, 'w'), ensure_ascii=False, indent=0)
    time.sleep(1.0)
    return out

def yivo_marks(w):
    """Drop Hebrew nikud that YIVO Yiddish does not write (Yehoyesh points loshn-koydesh words: שִטים, אֵפֿוֹד).
    Kept: pasekh/komets on alef, dagesh on ב פ כ ת ו, rafe on ב פ, shin/sin dots, khirik under yud."""
    keep = {'\u05b7': 'א\u05f2י', '\u05b8': 'א', '\u05bc': 'בפכתו', '\u05bf': 'בפ', '\u05c1': 'ש', '\u05c2': 'ש', '\u05b4': 'י'}
    out = []
    for ch in w:
        if '\u0591' <= ch <= '\u05c7':
            if ch in keep and out and out[-1] in keep[ch]: out.append(ch)
            continue
        out.append(ch)
    return ''.join(out)

def main(slug):
    names = json.load(open(D('names.json')))
    if os.path.exists(D('kids', f'{slug}.md')):
        text = open(D('kids', f'{slug}.md'), encoding='utf-8').read()
    else:   # a Yehoyesh-extract page: the story is verses from Sefaria, no markdown file
        import build
        cfg = json.load(open(D('parsha', f'{slug}.json')))
        tor = build.load_yehoyesh(cfg['slug'], 'torah')
        text = '\n'.join(s for ref in cfg['yehoyesh_extract'] for c, v, s in build.pick_verses(tor, ref))
    text = re.sub(r'^## .*$', '', text, flags=re.M)
    glosses = showdefs_glosses(slug, text)
    words = re.findall("[" + "\u05d0-\u05ea\u05f0-\u05f4\ufb1d-\ufb4f\u0591-\u05c7" + "\u05be']+", text)
    seen = {}
    for w in words:
        w = w.strip("'־")
        w = yivo_marks(w)
        if '\u05f3' in w: continue   # contractions like ס׳איז are not loshn-koydesh
        # fold inflected names/nouns onto a base already seen (אַבֿרהמען, אַבֿרהמס -> אַבֿרהם)
        nf = lambda x: x.replace('\u05bf', '').translate(str.maketrans('םןץףך', 'מנצפכ'))   # rafe dropped: יוספֿן -> יוסף
        base = next((b for b in seen if len(nf(w)) > len(nf(b)) and nf(w).startswith(nf(b)) and nf(w)[len(nf(b)):] in ('ענ', 'נ', 'ס', 'עס', 'ימ')), None)   # suffixes in nf form
        if base: seen[base]['count'] += 1; continue
        if w in seen: seen[w]['count'] += 1; continue
        if not is_lk(w) and w not in names and NIQQUD.sub('', w) not in names: continue   # names.json also covers names spelled phonetically (חוה, קין)
        # inflected name/noun whose base we know (הגרן -> הגר, שׂרהן -> שׂרה): count it under the base
        _b = NIQQUD.sub('', w)
        _fin = lambda x: (lambda y: y[:-1] + y[-1].translate(str.maketrans('מנצפכ', 'םןץףך')) if y else y)(x.rstrip('\u05bf'))   # restore final letter (rafe dropped: יוספֿ -> יוסף)
        _suf = next((x for x in ('ען', 'ן', 'ס', 'עס') if w.endswith(x) and (_fin(w[:-len(x)]) in names or _fin(_b[:-len(x)]) in names)), None)
        if _suf:
            w = _fin(w[:-len(_suf)])
            if w in seen: seen[w]['count'] += 1; continue
        bare = NIQQUD.sub('', w)
        entry = None
        if w in names or bare in names:
            n = names.get(w) or names[bare]; entry = dict(n)
            if entry.get('source') == 'manual' and entry.get('roman') and yiddish.transliterate(w, loshn_koydesh=True) != naive(w):
                entry['source'] = 'bleaman+names'   # name known to Bleaman too; names.json supplies the gloss/capitalisation
        else:
            bl = yiddish.transliterate(w, loshn_koydesh=True)
            f = {}
            if not (set(bl) & VOWELS): f = finkel(bare) or {}   # dictionary.cgi only as a romanization fallback
            # pronunciation: Bleaman's list (Weinreich-style Yiddish forms) first, Finkel as fallback; gloss from Finkel
            roman = (bl if set(bl) & VOWELS else None) or f.get('roman')
            if roman is None:
                entry = {'roman': '?', 'gloss': '?', 'source': 'MISSING'}
            else:
                entry = {'roman': roman, 'gloss': glosses.get(w) or glosses.get(bare) or f.get('gloss', ''), 'source': 'bleaman' if set(bl) & VOWELS else 'finkel'}
        entry.update(word=w, count=1); seen[w] = entry
    out = sorted(seen.values(), key=lambda e: -e['count'])
    json.dump(out, open(D('glossary', f'{slug}.json'), 'w'), ensure_ascii=False, indent=1)
    for e in out: print(f"{e['count']:3d}  {e['word']:14} {e['roman']:14} {e['source']:8} {e['gloss']}")

if __name__ == '__main__':
    for s in sys.argv[1:]: main(s)
