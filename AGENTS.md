# Working on parshe-fun-der-vokh (read fully before adding a parsha)

Goal: one printable Yiddish handout per parsha for children. **Nothing on a handout may be invented.** Every word of
the story comes verbatim from one named source book, checked against the page scan. No vocabulary lists, no
discussion questions, no summaries, no bridging sentences written by you. If the source has nothing for a parsha,
that parsha stays unbuilt (leave it out; note it in `data/parsha/UNBUILT.md` with the reason).

## Sources (Yiddish Book Center scans on archive.org, with OCR)
- **Breyshis (Bereshit … Vayechi)**: Aaron Bromberg, *Khumesh-mayses far kinder*, Arbeter Ring 1956, `nybc204961`.
  Short chapters, big clean type, YIVO spelling, OCR nearly perfect. ~3–4 handout pages per parsha. Chapters are
  titled; Bromberg sometimes reorders or skips episodes — reproduce his choices, never patch from another book.
- **Shmoys … Dvorim**: *Khumesh far kinder loyt Yehoash* (ed. Solomon Simon, Yudel Mark; Yehoash Farlag 1940),
  `nybc210870`. Yehoyesh's own text abridged for children, organized as 13 narrative chapters with titled
  sub-sections (not by parsha). OCR is rough: נ for ג, זי for זיי, lost dagesh/rafe. The book prints בּ for /b/,
  plain ב only in loshn-koydesh words, פ unmarked for /f/, פּ for /p/, nikud on Hebrew words. Normalize spelling to
  YIVO (פֿ, בֿ only in Hebrew-origin words, אַ/אָ, ײַ, no other nikud); change nothing else.
  `ocr_fix.py` pre-corrects this book's OCR by aligning it to Yehoyesh's text from Sefaria (the book copies him
  nearly word for word): `python3 ocr_fix.py data/scans/nybc210870_leaves.json <first> <last> data/yehoyesh/<slug>.torah.json`.
  Its output is a draft only; ⟦flagged⟧ tokens and זי/זיי must be settled from the page image.
  Map sub-sections to parshes by the Torah chapters they retell (section titles are in the table of contents, leaf 272–274).

## Workflow per parsha (<slug> as in data/parshes.json)
1. `python3 leaves.py <id> find <a distinctive Hebrew word from the chapter title>` → leaf numbers;
   `python3 leaves.py <id> dump <first> <last>` → OCR; `python3 leaves.py <id> images <first> <last> /tmp/<slug>` → page JPEGs.
2. Transcribe into `data/kids/<slug>.md`: `## <chapter title as printed>` then paragraphs exactly as the book sets
   them (one blank line between paragraphs; speeches as their own paragraphs, no added dashes or quotation marks
   unless the book prints them; the 1940 book's „…“ quotes are kept). Book footnotes go on a line starting `::: `. Verse the book sets line by line (a song, a blessing): one block,
   each line starting `| `.
3. **Proofread every page against its JPEG with the Read tool** (open the image, compare line by line). This is the
   step that makes it verbatim; the OCR alone is not good enough even for Bromberg (hyphen joins, זי/זיי, lost yuds).
4. `python3 fetch_yehoyesh.py <slug>` (Yehoyesh text for the pesukim box; CC0 via Sefaria). For a parsha that is
   doubled this year (e.g. Chukat-Balak) add the two halves' standard Torah/haftarah ranges to
   `data/parshes_hebcal.json` under the single names first.
5. `data/parsha/<slug>.json` — copy `data/parsha/vayera.json` and edit: `kids_sources` (label with book, publisher,
   year, printed page numbers; `ia` id; `leaf` of the first page; `parts` = the chapter titles used), 2–3 `verses`
   from the chapters the story retells (ref + Hebrew-letter label like "בראשית יח, א–ב"), `draw_prompt`
   "מאָל דאָ עפּעס פֿון דער מעשׂה", and `images` only if a matching scene exists (below) — otherwise `"images": []`.
6. Pictures: only public-domain Jewish manuscript art, from `data/images_commons.json` (British Library Sister and
   Golden Haggadah; Creation → Exodus scenes). Pick a file whose scene is actually in the story; download with
   `curl -sL -A "parshe/0.1" -o img/<name>.jpg "https://commons.wikimedia.org/w/index.php?title=Special:FilePath/<File name without 'File:'>"`;
   credit as in vayera.json. **No Christian publishers' illustration sets, no modern copyrighted art, no stock art.**
7. Glossary: `uv run --quiet --python 3.11 --with yiddish --with "setuptools<70" python glossary.py <slug>`.
   Any entry printed as `MISSING`, and any biblical name the tools lack, goes into `data/names.json` with
   `"source": "manual"` (YIVO romanization, Ashkenazi pronunciation, English gloss). Fix wrong Finkel glosses there too.
8. Build: `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib uv run --quiet --with weasyprint python build.py --pdf`
   (uv is at ~/.local/bin/uv). Then **open the PDF with the Read tool** and check every page: no text cut off,
   glossary box intact, drawing box present, footer credits correct. The Tetragrammaton must never appear (build
   prints ה׳); grep the HTML for יהוה.
9. Publish: `git pull --rebase origin main`, rebuild (docs/ is generated from data; if a rebase conflicts in
   docs/, do not hand-edit — rebuild and `git add docs`), `git add -A`, commit, `git push origin HEAD:main`.
   Commit as `-c user.name="Seth Flaxman" -c user.email="flaxter@gmail.com"`, one parsha per commit, message
   "<Parsha>: <source book> pp. <pages>", ending with the attribution lines your session instructions give.
   Push after every parsha so the site updates as you go (https://flaxter.github.io/parshe/).

Hard rules: verbatim from one source per parsha; flag anything manual; never print יהוה; never use unlicensed
or Christian-sourced pictures; never add content of your own to a handout; if unsure, leave it out and say so.
