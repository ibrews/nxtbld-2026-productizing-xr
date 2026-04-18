# New Slide Layouts — Splice Instructions

Preview: [`tools/layouts/preview.html`](preview.html). Open it to see the three layouts rendered with dummy data before splicing.

This patch is **not** applied automatically because `index.html` usually has uncommitted edits. Apply by hand when you're ready.

## What you get

Three new values for a case's `layout` field (the field is new — default stays the existing 48/52 layout, so nothing breaks if you never set it):

| `layout` | Use when | Reads bullets as |
|---|---|---|
| unset / `'split-48'` | **default** — current behaviour | flat list |
| `'split-50'` | hero image + equal-weight text | flat list |
| `'bleed'` | image IS the content; text steps out of the way | **pill tags**, not bullets |
| `'trio'` | three-way comparison | **grouped**: `["Col1 header", "b1", "b2", "---", "Col2 header", "b1", ...]` (`---` separates columns) |

## Step 1 — add CSS

Paste into `index.html` just after the existing `.case-slide` block (around the `.accent-rose .case-bl li::before` line). Match the dense single-line style of the surrounding file.

```css
.case-split{display:grid;grid-template-columns:1fr 1fr;gap:clamp(28px,3.5vw,72px);padding:clamp(48px,5vw,100px) clamp(64px,7vw,140px);height:100%;align-items:center}
.case-split .case-image{aspect-ratio:4/3;border-radius:14px;overflow:hidden}
.case-split .case-image img,.case-split .case-image iframe{width:100%;height:100%;object-fit:cover;display:block}
.case-split .case-content{display:flex;flex-direction:column;gap:12px}

.case-bleed{position:relative;height:100%;overflow:hidden;padding:0}
.case-bleed .case-image{position:absolute;inset:0;border-radius:0}
.case-bleed .case-image img,.case-bleed .case-image iframe{width:100%;height:100%;object-fit:cover;display:block;border-radius:0}
.case-bleed::after{content:'';position:absolute;inset:0;pointer-events:none;background:linear-gradient(180deg,transparent 40%,rgba(0,0,0,.75) 95%)}
.case-bleed .case-content{position:absolute;left:clamp(48px,5vw,100px);bottom:clamp(40px,5vw,80px);right:clamp(48px,5vw,100px);z-index:2;max-width:820px}
.case-bleed .case-title{text-shadow:0 2px 30px rgba(0,0,0,.6)}
.case-bleed .case-bl{flex-direction:row;flex-wrap:wrap;gap:8px 14px}
.case-bleed .case-bl li{padding:4px 12px;border-radius:999px;background:rgba(255,255,255,.12);backdrop-filter:blur(8px);font-size:clamp(12px,1vw,16px)}
.case-bleed .case-bl li::before{display:none}

.case-trio{display:flex;flex-direction:column;gap:clamp(24px,2.5vw,48px);padding:clamp(44px,5vw,90px) clamp(60px,7vw,140px);height:100%;justify-content:center}
.case-trio .trio-head{display:flex;flex-direction:column;gap:6px}
.case-trio .trio-cols{display:grid;grid-template-columns:1fr 1fr 1fr;gap:clamp(20px,2vw,36px)}
.case-trio .trio-col{border-top:2px solid rgba(255,255,255,.12);padding-top:14px;display:flex;flex-direction:column;gap:10px}
.case-trio .trio-col h4{font:700 clamp(14px,1.3vw,20px)/1.2 -apple-system,sans-serif;letter-spacing:-.01em;margin:0}
.case-trio .trio-col ul{list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:8px}
.case-trio .trio-col ul li{padding-left:18px;position:relative;color:rgba(240,244,255,.7);font-size:clamp(12px,1vw,16px);line-height:1.5}
.case-trio .trio-col ul li::before{content:'';position:absolute;left:0;top:.65em;width:5px;height:5px;border-radius:50%;background:var(--teal);opacity:.7}
.case-trio .trio-col:nth-child(2){border-top-color:rgba(124,58,237,.5)}
.case-trio .trio-col:nth-child(2) ul li::before{background:var(--purple)}
.case-trio .trio-col:nth-child(3){border-top-color:rgba(245,158,11,.5)}
.case-trio .trio-col:nth-child(3) ul li::before{background:var(--amber)}
```

## Step 2 — patch the build loop

Current build loop (near line 358 in `index.html`):

```js
sec.cases.forEach(c=>{
  const s=document.createElement('div');s.className=`slide case-slide${ac}`;s.dataset.type='case';...
  let imgHTML;
  if(c.img&&c.img.startsWith('IFRAME:')){ ... }
  else if(c.img&&c.img!=='MEDIA_CYCLER'){ ... }
  else { imgHTML=`<div class="media-cycler-mount" ...></div>`; }
  s.innerHTML=`<div class="case-image">${imgHTML}</div><div class="case-content">...`;
  deck.appendChild(s);allSlides.push(s);
});
```

Replace with a dispatch on `c.layout`:

```js
sec.cases.forEach(c=>{
  const layout=c.layout||'split-48';
  const cls={'split-48':'case-slide','split-50':'case-slide case-split','bleed':'case-slide case-bleed','trio':'case-slide case-trio'}[layout]||'case-slide';
  const s=document.createElement('div');s.className=`slide ${cls}${ac}`;s.dataset.type='case';s.dataset.year=sec.year;s.dataset.section=si;s.dataset.layout=layout;
  let imgHTML;
  if(c.img&&c.img.startsWith('IFRAME:')){
    const iframeSrc=c.img.slice(7);
    imgHTML=`<iframe src="${iframeSrc}" style="width:100%;height:100%;border:none;border-radius:18px" allow="autoplay;fullscreen;xr-spatial-tracking" allowfullscreen></iframe>`;
  } else if(c.img&&c.img!=='MEDIA_CYCLER'){
    imgHTML=`<img src="${c.img}" loading="lazy" style="border-radius:18px">`;
  } else {
    imgHTML=`<div class="media-cycler-mount" style="width:100%;height:100%"></div>`;
  }
  const ytag=`<div class="case-ytag">Case Study &middot; ${sec.lesson.short||''}</div>`;
  const title=`<h2 class="case-title">${c.title}</h2>`;
  const sub=c.subtitle?`<p class="case-sub">${c.subtitle}</p>`:'';
  let bodyHTML;
  if(layout==='trio'){
    // Bullets grouped by '---' dividers. First item in each group is the column heading.
    const groups=[];let cur=[];(c.bullets||[]).forEach(b=>{if(b==='---'){if(cur.length){groups.push(cur);cur=[];}}else{cur.push(b);}});if(cur.length)groups.push(cur);
    const cols=groups.slice(0,3).map(g=>`<div class="trio-col"><h4>${g[0]||''}</h4><ul>${g.slice(1).map(b=>`<li>${b.replace(/\n/g,'<br>')}</li>`).join('')}</ul></div>`).join('');
    bodyHTML=`<div class="trio-head">${ytag}${title}${sub}</div><div class="trio-cols">${cols}</div>`;
    s.innerHTML=bodyHTML;
  } else if(layout==='bleed'){
    const pills=(c.bullets||[]).map(b=>`<li>${b}</li>`).join('');
    s.innerHTML=`<div class="case-image">${imgHTML}</div><div class="case-content">${ytag}${title}${sub}${pills?`<ul class="case-bl">${pills}</ul>`:''}</div>`;
  } else {
    const bl=(c.bullets||[]).map(b=>`<li>${b.replace(/\n/g,'<br>')}</li>`).join('');
    s.innerHTML=`<div class="case-image">${imgHTML}</div><div class="case-content">${ytag}${title}${sub}<ul class="case-bl">${bl}</ul></div>`;
  }
  deck.appendChild(s);allSlides.push(s);
});
```

## Step 3 — use it in SECTIONS

```js
// In any chapter's cases:
{ layout:'bleed', title:"The Rehearsal That Saved the Set",
  subtitle:"A blocking tool became the decision tool.",
  img:'media/rehearsal/hero.jpg',
  bullets:['Quest 3','Unreal','Shot list','6 weeks'] },

{ layout:'trio', title:"Three Engines, Three Tradeoffs",
  subtitle:"Same brief, three tech stacks, three outcomes.",
  img:'', bullets:[
    'Unreal','Best-in-class lighting.','Compile times kill iteration.','Hero shots, cinematic capture.',
    '---',
    'Unity','Fastest prototype-to-headset.','Visual ceiling needs custom shaders.','Gameplay-first experiences.',
    '---',
    'WebXR','Zero-install onboarding.','Feature-detection jungle.','Marketing, one-off demos.',
  ]},
```

## Notes / caveats

- Existing slides keep working — no `layout` key ⇒ default `split-48` render, identical to current markup.
- `bleed` suppresses the `::before` dot and re-uses `.case-bl` as a pill row, so the media-cycler mount still works if you pass `img:'MEDIA_CYCLER'`.
- `trio` ignores `img` (the three columns ARE the content).
- `data-layout` is set on each `.slide` so keyframe annotations and the move-mode HUD can target layout-specific elements if you need to.
- Round-trip round-trip: `export_md.py` / `import_md.py` don't yet round-trip the `layout` field — we'd need a meta-block entry per-case. Worth adding only if you actually adopt the new layouts.
