#!/usr/bin/env python3
"""Correct archive.org OCR of the 1940 "Khumesh far kinder loyt Yehoash" against Yehoyesh's own text (Sefaria).
The book copies Yehoyesh nearly verbatim, so:
  pass 1  tokens that are real Yehoyesh words (anywhere in his Khumesh) are kept, in his spelling;
  pass 2  the OCR token stream is aligned to the Yehoyesh text of the same chapters, and a token that differs from
          its aligned counterpart by one edit (two for long words) is replaced by it — this is what fixes זי/זיי, נ/ג;
  pass 3  remaining unknown tokens are snapped to a Yehoyesh word one edit away if unambiguous, else flagged ⟦so⟧.
Usage: ocr_fix.py <leaves.json> <first> <last> <chapter-yehoyesh.json ...>   (full-Khumesh vocab from data/yehoyesh/_books)"""
import json, re, sys, os, glob, collections, difflib
HERE = os.path.dirname(os.path.abspath(__file__))
NIQ = re.compile(r'[֑-ׇ]')
TOK = r"[א-תװ-״֑-ׇ]+|\S"

def norm(w):
    w = NIQ.sub('', w)
    return w.replace('װ', 'וו').replace('ױ', 'וי').replace('ײ', 'יי')

def tokens_of(files):
    toks = []
    for f in files:
        d = json.load(open(f))
        for part in d['parts']:
            flat = []
            def walk(x):
                if isinstance(x, str): flat.append(x)
                else:
                    for y in x: walk(y)
            walk(part['text'])
            for s in flat:
                s = re.sub(r'<[^>]+>', '', s)
                toks += re.findall(r"[א-תװ-״֑-ׇ]+", s)
    return toks

def dl(a, b, maxd):
    if abs(len(a) - len(b)) > maxd: return maxd + 1
    prev2 = None; prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            v = min(prev[j] + 1, cur[j-1] + 1, prev[j-1] + (ca != cb))
            if prev2 is not None and i > 1 and j > 1 and a[i-1] == b[j-2] and a[i-2] == b[j-1]:
                v = min(v, prev2[j-2] + 1)
            cur.append(v)
        prev2, prev = prev, cur
        if min(prev) > maxd: return maxd + 1
    return prev[-1]

# systematic tesseract misreads on this typeface (נ for ג, װ for ז, lost dagesh/rafe), and the book's own spellings
SUBS = {'געזאָנט':'געזאָגט','גענאַנגען':'געגאַנגען','בּרעננען':'ברענגען','ברעננען':'ברענגען','אַװי':'אַזױ','אַװױ':'אַזױ','דערוען':'דערזען',
        'בּאָמת':'באמת','באָמת':'באמת','שער':'שװער','וי':'װי','ריידן':'רײדן','רײדן':'רײדן','אַרוסגעפירט':'אַרױסגעפֿירט','נאָט':'גאָט',
        'אומנעקוקט':'אומגעקוקט','אומנעקערט':'אומגעקערט','אַראָפּנעקוקט':'אַראָפּגעקוקט','אויפנעשטעלט':'אױפֿגעשטעלט','אַרומנערינגלט':'אַרומגערינגלט',
        'אַרײַננעקומען':'אַרײַנגעקומען','אײַננאַנג':'אײַנגאַנג','זאָנן':'זאָגן','נעװען':'געװען','געװוען':'געװען','אַזױי':'אַזױ','אױיבּ':'אױב','בּיו':'ביז','אונדו':'אונדז'}
POST = {'אבֿרהם':'אַבֿרהם','אבֿרהמען':'אַבֿרהמען','אבֿרהמס':'אַבֿרהמס','אבֿרם':'אַבֿרם','אבֿרמען':'אַבֿרמען'}

def clean(text):
    text = re.sub(r'-\s*\n\s*', '', text)                 # hyphen at line end
    text = re.sub(r'(\S)"\s*\n\s*(\S)', r'\1\2', text)    # OCR shows that hyphen as " sometimes
    text = text.replace('\n', ' ')
    text = re.sub(r'[{}|\[\]]\s*\d(?:\s*\d)*\s*[{}|\[\]]?', ' ', text)   # page numbers  { 28 |
    text = re.sub(r'\s*-\s*-\s*', ' — ', text)             # -- -> em dash
    return text

def main():
    leaves = json.load(open(sys.argv[1])); a, b = int(sys.argv[2]), int(sys.argv[3])
    chap = tokens_of(sys.argv[4:])
    full = tokens_of(glob.glob(os.path.join(HERE, 'data', 'yehoyesh', '_books', '*.json')))
    cnt = collections.Counter(norm(t) for t in full)
    spell = {}
    for t in chap + full: spell.setdefault(norm(t), t)
    chap_keys = [norm(t) for t in chap]
    for li in range(a, b + 1):
        raw = re.findall(TOK, clean(leaves[li]))
        words = [t for t in raw if re.search(r'[א-תװ-״]', t)]
        keys = [norm(w) for w in words]
        # pass 2: align with the chapter text (difflib on keys) and adopt one-edit neighbours
        fixed = list(words)
        sm = difflib.SequenceMatcher(None, keys, chap_keys, autojunk=False)
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == 'replace' and (i2 - i1) == (j2 - j1):
                for k in range(i2 - i1):
                    ok, yk = keys[i1 + k], chap_keys[j1 + k]
                    maxd = 1 if len(ok) < 6 else 2
                    if dl(ok, yk, maxd) <= maxd: fixed[i1 + k] = spell[yk]
            elif op == 'equal':
                for k in range(i2 - i1): fixed[i1 + k] = spell[keys[i1 + k]]
        # pass 1/3 on whatever is left
        for i, w in enumerate(fixed):
            k = norm(w)
            if k in cnt: fixed[i] = spell[k]; continue
            if w != words[i]: continue           # already fixed by alignment
            maxd = 1 if len(k) < 6 else 2
            cands = [(dl(k, c, maxd), -n, c) for c, n in cnt.items() if abs(len(c) - len(k)) <= maxd]
            cands = sorted(x for x in cands if x[0] <= maxd)
            if cands and (len(cands) == 1 or cands[0][0] < cands[1][0]) and cands[0][0] == 1:
                fixed[i] = spell[cands[0][2]]
            else:
                fixed[i] = '⟦' + w + '⟧'
        # re-interleave punctuation
        out = []; wi = 0
        for t in raw:
            if re.search(r'[א-תװ-״]', t): out.append(fixed[wi]); wi += 1
            else: out.append(t)
        s = ' '.join(out)
        s = re.sub(r'\s+([,.;:!?])', r'\1', s)
        s = re.sub(r'(:)\s*[,;\'`]+\s*', r'\1 „', s)          # opening quote after colon
        s = re.sub(r'^\s*[,;]\s*', '„', s)
        s = re.sub(r'\s*(["\'”″]+)(\s|$)', r'“\2', s)          # closing quote
        s = re.sub(r'\s*(["\'”″]+)([,.;:!?])', r'“\2', s)
        s = re.sub(r'\s+', ' ', s).strip()
        s = re.sub(r'(?:\s\d)+\s*$', '', s)
        for k_, v_ in POST.items(): s = re.sub(r'(?<![\u05d0-\u05ea])' + k_ + r'(?![\u05d0-\u05ea])', v_, s)
        print(f'===== LEAF {li} =====\n{s}\n')

if __name__ == '__main__': main()
