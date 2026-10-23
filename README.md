# פּרשה פֿון דער װאָך · Parshe fun der vokh (far kinder)

Weekly Torah portion in Yiddish for children: a printable handout (A4, 3 pages) plus a web page per parsha.

- **Children's text first**: retellings from Yiddish children's Khumeshim scanned by the Yiddish Book Center
  (Bromberg, *Khumesh-mayses far kinder*, Arbeter Ring 1956; *Khumesh far kinder loyt Yehoash*, 1940),
  cleaned from archive.org OCR into `data/kids/<slug>.md`.
- **Yehoyesh**: selected pesukim and (on screen) the whole parsha + haftarah from Yehoyesh's Tanakh,
  CC0 via Sefaria (`fetch_yehoyesh.py` → `data/yehoyesh/`). The Tetragrammaton is printed as ה׳.
- **Pictures**: public-domain medieval Jewish manuscripts (British Library Sister/Golden Haggadah) where a scene exists,
  plus a "draw it yourself" box on the printout.
- **Verbatim rule**: each parsha's children's text is one source, reproduced as printed (paragraphing, speech dashes,
  the book's own footnotes). Only spelling is normalized to YIVO. Both built parshes use Bromberg 1956 (short, ~800 words, 3-4 pages).
  A proofread transcription of Vayero from the 1940 *Khumesh far kinder loyt Yehoash* (2,500 words, 8 pages) is parked
  in `data/kids/alt/` as the long alternative. `ocr_fix.py` pre-corrects that book's
  OCR by aligning it with Yehoyesh's own text from Sefaria (the book copies him nearly word for word).
- **Loshn-koydesh glossary** (`glossary.py`): Hebrew-origin words in the story are detected automatically
  (Bleaman's `yiddish` package respells them or leaves them vowel-less), romanized in YIVO transcription
  (Bleaman's list; Finkel's dictionary as fallback) and glossed by Refoyl Finkel's gloss displayer
  (one cached request per parsha). Biblical names neither tool knows live in `data/names.json`, hand-written and flagged.
  Nothing on the handout is invented: no vocabulary picks, no discussion questions.
- **This week**: `index.html` asks Sefaria's calendar API which parsha it is (diaspora) and highlights it.

```
python3 fetch_yehoyesh.py [slug ...]      # Sefaria → data/yehoyesh (cached)
uv run --python 3.11 --with yiddish --with 'setuptools<70' python glossary.py <slug>   # → data/glossary/<slug>.json
uv run --with weasyprint python build.py --pdf   # → docs/*.html, docs/*.pdf   (needs DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib for pango)
```

Adding a parsha = `data/parsha/<slug>.json` (images, verses, questions, verter) + `data/kids/<slug>.md`.
