"""Fetch Yehoyesh's Yiddish Tanakh (CC0, via Sefaria) for every parsha + haftarah into data/yehoyesh/.
Torah/haftarah ranges come from data/parshes_hebcal.json (hebcal leyning API, diaspora). Doubled parshes are
split by looking up both halves' standard ranges from Sefaria's parasha index when hebcal only gives the combined one."""
import json, os, sys, time, urllib.request, urllib.parse
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'data', 'yehoyesh')
VT = "yiddish|Yehoyesh's Yiddish Tanakh Translation [yi]"
UA = {'User-Agent': 'parshe-fun-der-vokh/0.1 (flaxter@gmail.com)'}

def get(url):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60))

def fetch_ref(ref):
    u = "https://www.sefaria.org/api/v3/texts/" + urllib.parse.quote(ref) + "?version=" + urllib.parse.quote(VT)
    d = get(u)
    v = [x for x in d['versions'] if 'Yehoyesh' in x['versionTitle']]
    if not v:
        raise RuntimeError('no Yehoyesh for ' + ref)
    return {'ref': ref, 'sections': d.get('sections'), 'toSections': d.get('toSections'), 'text': v[0]['text'],
            'versionTitle': v[0]['versionTitle'], 'license': v[0].get('license'), 'source': v[0].get('versionSource')}

def main():
    os.makedirs(OUT, exist_ok=True)
    parshes = json.load(open(os.path.join(HERE, 'data', 'parshes.json')))
    heb = json.load(open(os.path.join(HERE, 'data', 'parshes_hebcal.json')))
    # Sefaria's parasha index gives the canonical Torah range for every single parsha (hebcal has combined ones)
    cal = get("https://www.sefaria.org/api/index/Genesis")  # warm-up / sanity
    only = sys.argv[1:] 
    for p in parshes:
        if only and p['slug'] not in only:
            continue
        name = p['hebcal']
        h = heb.get(name)
        torah = h['torah'] if h else None
        haft = h['haft'] if h else None
        if not torah:
            # doubled this year or outside the fetched span: ask Sefaria for the parasha ref
            try:
                d = get("https://www.sefaria.org/api/v2/raw/index/Genesis")
            except Exception:
                d = None
            print('  no hebcal range for', name, '- using Sefaria terms')
            t = get("https://www.sefaria.org/api/terms/" + urllib.parse.quote('Parashat ' + p['en_sef'] if p.get('en_sef') else 'Parashat ' + name))
            torah = t.get('ref')
        for kind, ref in (('torah', torah), ('haftarah', haft)):
            if not ref:
                continue
            fn = os.path.join(OUT, f"{p['slug']}.{kind}.json")
            if os.path.exists(fn):
                continue
            parts = [r.strip() for r in ref.split(',')]
            # second part of a comma range lacks the book name
            book = parts[0].rsplit(' ', 1)[0]
            parts = [r if r[0].isalpha() else book + ' ' + r for r in parts]
            data = [fetch_ref(r) for r in parts]
            json.dump({'ref': ref, 'parts': data}, open(fn, 'w'), ensure_ascii=False)
            print('fetched', fn, sum(len(c) for d in data for c in d['text']) if isinstance(data[0]['text'][0], list) else len(data[0]['text']), 'verses')
            time.sleep(0.4)

if __name__ == '__main__':
    main()
