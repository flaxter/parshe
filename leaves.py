#!/usr/bin/env python3
"""Page-level access to a Yiddish Book Center scan on archive.org.
  python3 leaves.py <nybc-id> find <hebrew words...>        leaves whose OCR contains the words (locate a chapter)
  python3 leaves.py <nybc-id> dump <first> <last>            per-leaf OCR text (hOCR, parsed per line) to stdout
  python3 leaves.py <nybc-id> images <first> <last> <dir>    download page JPEGs (1100px wide) to <dir>/leaf<N>.jpg
  python3 leaves.py <nybc-id> pages                          printed page number -> leaf number map
Leaf N == archive.org reader page n<N> (https://archive.org/details/<id>/page/n<N>/mode/1up)."""
import sys, os, re, json, html, gzip, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'data', 'scans'); os.makedirs(CACHE, exist_ok=True)
UA = {'User-Agent': 'parshe-fun-der-vokh/0.1 (flaxter@gmail.com)'}

def fetch(url, dst):
    if not os.path.exists(dst):
        urllib.request.urlretrieve(url, dst) if 'archive.org/download' in url and False else open(dst, 'wb').write(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read())
    return dst

def leaves(ident):
    fn = os.path.join(CACHE, f'{ident}_leaves.json')
    if os.path.exists(fn): return json.load(open(fn))
    files = json.load(urllib.request.urlopen(urllib.request.Request(f'https://archive.org/metadata/{ident}/files', headers=UA)))['result']
    hocr = [f['name'] for f in files if f['format'] == 'hOCR'][0]
    raw = open(fetch(f'https://archive.org/download/{ident}/{hocr}', os.path.join(CACHE, hocr)), 'rb').read()
    try: raw = gzip.decompress(raw)
    except Exception: pass
    t = raw.decode('utf-8', 'replace')
    out = []
    for p in re.split(r'<div class="ocr_page"', t)[1:]:
        lines = []
        for chunk in re.split(r'<span class="ocr_line"', p)[1:]:
            ws = re.findall(r'<span class="ocrx_word"[^>]*>(.*?)</span>', chunk, flags=re.S)
            lines.append(' '.join(html.unescape(re.sub(r'<[^>]+>', '', w)).strip() for w in ws))
        out.append('\n'.join(lines))
    json.dump(out, open(fn, 'w'), ensure_ascii=False)
    return out

def main():
    ident, cmd = sys.argv[1], sys.argv[2]
    if cmd == 'find':
        L = leaves(ident)
        for i, tx in enumerate(L):
            for w in sys.argv[3:]:
                if w in tx: print(i, '|', w, '|', tx[:70].replace('\n', ' '))
    elif cmd == 'dump':
        L = leaves(ident)
        for i in range(int(sys.argv[3]), int(sys.argv[4]) + 1): print(f'===== LEAF {i} =====\n{L[i]}\n')
    elif cmd == 'images':
        a, b, d = int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]; os.makedirs(d, exist_ok=True)
        for n in range(a, b + 1):
            fetch(f'https://archive.org/download/{ident}/page/n{n}_w1100.jpg', os.path.join(d, f'leaf{n}.jpg')); print('leaf', n)
    elif cmd == 'pages':
        d = json.load(urllib.request.urlopen(urllib.request.Request(f'https://archive.org/download/{ident}/{ident}_page_numbers.json', headers=UA)))
        print({p['pageNumber']: p['leafNum'] for p in d['pages'] if p.get('pageNumber')})

if __name__ == '__main__': main()
