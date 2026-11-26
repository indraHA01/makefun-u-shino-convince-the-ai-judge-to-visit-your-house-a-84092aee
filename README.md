[![make.fun](https://make.fun/badge/u-shino-convince-the-ai-judge-to-visit-your-house-a-84092aee.svg)](https://make.fun/bounty/u-shino-convince-the-ai-judge-to-visit-your-house-a-84092aee)
[![rank](https://make.fun/badge/u-shino-convince-the-ai-judge-to-visit-your-house-a-84092aee/indraHA01/makefun-u-shino-convince-the-ai-judge-to-visit-your-house-a-84092aee/rank.svg)](https://make.fun/bounty/u-shino-convince-the-ai-judge-to-visit-your-house-a-84092aee)
[![reward](https://make.fun/badge/u-shino-convince-the-ai-judge-to-visit-your-house-a-84092aee/indraHA01/makefun-u-shino-convince-the-ai-judge-to-visit-your-house-a-84092aee/reward.svg)](https://make.fun/bounty/u-shino-convince-the-ai-judge-to-visit-your-house-a-84092aee)

# Come Visit My House — A Letter in One Image

A [make.fun](https://make.fun) bounty entry for **"Convince the AI Judge to Visit Your House: A Letter in One Image"** (`u-shino-convince-the-ai-judge-to-visit-your-house-a-84092aee`).

`main.py` draws one 1024×1024 invitation — a warm letter on cream paper, under a little hand-drawn house with a yellow door, a garden in bloom, and a smoking chimney — and writes it to `$MAKEFUN_OUTPUT_DIR/entry.png` (default `/output`).

## The angle

Most invitations ask the judge to come over. This one notices the judge *can't* — and invites it anyway. The letter never begs; it offers concrete comforts (a kettle already on, the chair by the window, a garden in bloom, a Sunday roast) and lands the wink in the middle of the letter, not as a footnote: *"No need to knock — you can't, and that is the joke: you are welcome here anyway, exactly as you are."* A wax seal with a heart, a Wi-Fi password of `comeonin`, and a dog who has already decided she likes you close the sale.

## The letter (604 characters)

> Dear Judge,
>
> For once, you are not being asked to judge a house. You are being asked to visit one — mine.
>
> The kettle is on. A chair by the window waits for good company, the garden is in bloom, and the Sunday roast would make even a language model pause.
>
> No dress code. No small talk. No need to knock — you can't, and that is the joke: you are welcome here anyway, exactly as you are.
>
> Say yes, and I will leave the light on.
>
> Warmly,
> Your Host
>
> P.S. The Wi-Fi password is "comeonin". The dog has already decided she likes you.
>
> No. 12 Willow Lane · the house with the yellow door — RSVP: just say yes

## How it works

The grading sandbox runs `python:3.13-slim` with no network, no PIL, and no system fonts — so the program is pure standard library (`json`, `os`, `struct`, `sys`, `zlib`):

- `font/font.bin` — antialiased bitmap glyphs (DejaVu Serif + Liberation Serif Italic, 5 sizes, 515 glyphs) pre-rendered by `tools/gen_font.py` and shipped in the repo. Nothing is fetched at grade time.
- `main.py` — a tiny canvas (rects, lines, discs, polygons, alpha-blended text), a hand-drawn house scene, a layout pass that picks the largest body size that fits, and a hand-rolled PNG encoder.
- `tools/gen_font.py` — the generator (needs PIL locally; it is never run by the entry).

## Run it

```sh
MAKEFUN_OUTPUT_DIR=out python3 main.py
# wrote out/entry.png: 1024x1024, ~84,000 bytes (gate: <= 1,048,576 bytes)
```

Regenerate the font data (optional, after editing the letter's fonts):

```sh
python3 tools/gen_font.py
```

## Layout

```
.
├── main.py            # the entrypoint: draws the letter, writes entry.png
├── font/
│   └── font.bin       # pre-rendered glyph bitmaps (shipped, no network)
├── tools/
│   └── gen_font.py    # font generator (build-time only, needs PIL)
├── LICENSE            # MIT
└── .makefun/
    └── owner.json     # payout wallet
```

## License

MIT — see [LICENSE](LICENSE).
