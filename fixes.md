# Site Fixes

Open items for conleytutoring.com, ordered by impact.
Paths are relative to this directory (`conleytutoring/`).
Line numbers in the open items were last re-checked on 2026-08-20; completed items keep the numbers they were written against.

---

## Tier 1 — Critical

### 1. No Open Graph image or URL

- [x] Add `og:image` and `og:url` to the head.

**Where:** `public/index.html:10-13`

**Problem:** `og:title`, `og:description`, and `og:type` are set, but `og:image` and `og:url` are missing.
Sharing the link in iMessage, WhatsApp, or Facebook produces a gray box with no picture.

**Why it matters:** Parent-to-parent referral is the main growth channel.
The existing testimonial is a relative recommending Luke to their circle, which is exactly the moment a blank preview costs a click.

**Fix:** Create a 1200x630 share image, add it to `public/`, and reference it with an absolute URL.
Add `twitter:card` set to `summary_large_image` while in there.

**Status (2026-08-19):** Done.

- `public/og-image.jpg` — 1200x630, 97 KB.
  A split card: brand mark and wordmark, the headline "Coding & game development tutoring for kids of any age" with the site's green-to-blue gradient on the last phrase, the "Online over Zoom" and "Free intro call" meta row, and the headshot as a circle on the right in the same crop the About card uses.
- `public/index.html:14-29` — `og:url`, `og:site_name`, `og:locale`, `og:image`, `og:image:secure_url`, `og:image:type`, `og:image:width`, `og:image:height`, `og:image:alt`, then `twitter:card` set to `summary_large_image` with matching `twitter:title`, `twitter:description`, `twitter:image`, and `twitter:image:alt`.
  The explicit width and height let Facebook and LinkedIn lay out the card on first scrape instead of falling back to a small preview until they fetch the image.

The share image is not hand-drawn, it is rendered from `assets/og-card.html` by headless Chrome at 2x and downsampled to 1200x630.
That template carries the regeneration commands in a comment at the top and copies its colors and brand mark from `public/index.html`.
(2026-08-20: the meta row changed from "NYC in-person & Zoom" to "Online over Zoom" when in-person tutoring came off the site, and the card was re-rendered. Only that row's pixels moved; the rest of the image is unchanged.)
It lives outside `public/`, so wrangler does not serve it — verified as a 404.
The point is that the card stays editable: changing the headline is a text edit and a re-render, not an image-editor round trip.

Verified against `wrangler dev` on Node 22: `/og-image.jpg` returns 200 `image/jpeg`, the served bytes hash-match the repo file, the served image measures 1200x630, and all seventeen tags reach the served HTML.
The item 11 JSON-LD still parses with its three `@graph` nodes.

The card renders the headshot from the full-resolution original.
Item 2 has since moved that original to `assets/headshot-source.jpg` and repointed this template at it, so the share image is still built from full-resolution pixels rather than from the compressed avatar.
Re-rendering after that change produced a byte-identical `og-image.jpg`, so nothing here regressed.

---

### 2. `headshot.jpg` is 922 KB

- [x] Compress and resize the headshot.

**Where:** `public/headshot.jpg`, used as a CSS background at `public/index.html:305`

**Problem:** The image is 922 KB but renders as a circle at most ~350px wide.
It accounts for roughly 95% of total page weight.

**Why it matters:** It is the image a parent waits on when loading the site on a phone over cellular.

**Fix:** Resize to about 700px square for 2x, then compress to 40-60 KB.
Consider serving WebP with a JPEG fallback.

**Status (2026-08-19):** Done.

- `public/headshot.webp` — 700x700, 70 KB. The image essentially every current browser gets.
- `public/headshot.jpg` — 700x700, 89 KB. Fallback only.
- `assets/headshot-source.jpg` — the untouched 1200x1600 original, 901 KB, moved out of `public/` so wrangler stops serving it. Verified as a 404.
- `assets/build-headshot.py` — rebuilds both outputs from that source.
- `public/index.html:407-425` — the `.avatar` rule.

Page weight for a first-time visitor goes from 957 KB to 126 KB, a drop of 87%.
The headshot was 94% of the page and is now 56% of a much smaller page.
There are no fonts or other external requests, so those two numbers are the whole page.

Three things did the work, and only the first is what the item asked for.

The crop is now baked into the file.
The old CSS positioned a 1200x1600 portrait with `background-size: 100%; background-position: 50% 30%` inside a square box, which means the visible band was source rows 120 to 1320 — exactly 1200 tall.
Every row outside that band was downloaded and never painted.
`build-headshot.py` cuts that 1200x1200 square directly, so the served file is all visible pixels.
The derivation is written out in the script's docstring, because the framing is now a build-time constant rather than something you can nudge in CSS.

The corners outside the circle are blurred.
`border-radius: 50%` clips them, so about 21% of a square image is never painted, and encoding that region as sharp foliage was costing real bytes.
They are blurred rather than filled flat because a hard edge at the circle boundary is itself expensive to encode.
This is invisible by construction — the clip removes exactly the region that was changed.

`.avatar` gained `max-width: 360px`.
This is the one visual change and it is worth a look.
The two-column layout gives the avatar ~355px, but below the 860px breakpoint the card goes full width, so on a tablet at 859px the circle was rendering at 761px — larger than the design anywhere else, and it made 700px less than a 1x asset at that width.
The cap only engages between roughly 458px and 859px of viewport width.
Phones are unaffected: at a 430px viewport the avatar is 332px, already under the cap.
Desktop is unaffected: 355px is under the cap too.

**On the 40-60 KB target:** it lands at 70 KB instead, and the gap is the photo, not the encoder.
The background is a Brooklyn street — foliage, brownstones, parked cars, a wrought-iron fence — and that high-frequency detail is expensive at any quality setting.
At 1:1, which is already twice the size it is ever painted at, q74 is indistinguishable from the original; so is q68, which would only buy 6 KB.
Reaching 50 KB would mean dropping below 700px and giving up 2x sharpness on a face.
Blurring the photographic background would get there comfortably and would arguably look better as a headshot, but that changes how the photo looks and is a call for Luke, not a compression decision.

Verified against `wrangler dev` on Node 22: `/headshot.webp` returns 200 `image/webp` and `/headshot.jpg` returns 200 `image/jpeg`, both 700x700, both hash-matching the repo files.
`/assets/headshot-source.jpg`, `/assets/build-headshot.py`, and `/headshot-source.jpg` all return 404.
The framing was checked numerically rather than by eye: against the old CSS crop the new file differs by a mean of 2.1/255 inside the circle, and shifting the crop by a single source row triples that error, which confirms the offset is right.
Re-rendering `og-image.jpg` afterward produced a byte-identical file, so item 1 is intact.

---

### 3. No analytics

- [ ] Add Cloudflare Web Analytics.

**Where:** `public/index.html`, plus `wrangler.jsonc:13`

**Problem:** `observability` is enabled on the Worker, which gives request-level data, but nothing tracks whether visitors click through to Calendly.

**Why it matters:** The booking funnel drives a $150/hr business and there is currently no visibility into where it leaks.

**Fix:** Add the Cloudflare Web Analytics beacon.
It is free, privacy-friendly, and a single script tag.

---

### 4. No favicon

- [x] Add a favicon and `rel="icon"` link.

**Where:** `public/index.html` head; no icon file existed in `public/`

**Problem:** There is no `rel="icon"` tag and no icon asset, so browsers show a default blank page icon.

**Fix:** Reuse the inline brand-mark SVG at `public/index.html:531-535` (listed as `:407-411` before items 1 and 2 shifted line numbers) as `public/favicon.svg`.
Add a PNG fallback for older browsers and an `apple-touch-icon`.

**Status (2026-08-20):** Done.

- `public/favicon.svg` — the header's turtle-graphics arrowhead on its rounded tile, 406 bytes.
  The path, its 1.6 stroke, and the `rx="11"` tile are the header mark's, unchanged.
- `public/favicon.ico` — 16, 32, and 48 px frames in one file, 4.4 KB.
- `public/apple-touch-icon.png` — 180x180, opaque, 4.5 KB.
- `public/index.html:10-15` — the three link tags.
- `assets/build-icons.py` — builds all three from one set of constants.
- `assets/check-icons.py` — verifies the raster path against a real SVG renderer.

The header is untouched.
A modern browser fetches only the 406-byte SVG; the ICO is for browsers that cannot read it, and the PNG only downloads if someone adds the site to an iOS home screen.

**The one deliberate departure from the header: the colors are inverted.**
The header draws a green arrowhead on the pale `--brand-tint` tile, which reads fine at 34 CSS px next to the wordmark.
A favicon is 16 px against browser chrome that is white in light mode and near-black in dark mode, and `#e2f7e6` simply disappears into the light one — the tile would vanish and leave a small green triangle floating where every other tab shows a solid mark.
So the tile takes the solid `--brand` green and the arrowhead is knocked out in white.
Same silhouette, same two brand colors, legible on either chrome.
The mark is also scaled to 74% of the tile height, against roughly 59% in the header, because an icon has to carry a whole tile on its own rather than sit in a row next to a wordmark.

`favicon.ico` rather than the plain PNG the item asked for.
It is the same fallback, in the format the browsers that need a fallback actually request — every one of them asks for `/favicon.ico` by name whether or not it is linked, so this also removes a 404 the site was serving on every cold visit.
The `sizes="32x32"` on the ICO link is what keeps Chrome from preferring it over the SVG.

`apple-touch-icon.png` is deliberately square and opaque rather than rounded like the other two.
iOS applies its own squircle mask, so pre-rounded corners would show as transparent notches inside that mask, and iOS discards alpha, so a transparent file can composite to black.
Its arrowhead is scaled to 62% instead of 74% to stay inside the mask's safe area.

**On the build.** Pillow has no vector renderer and the machine has no `rsvg-convert` or ImageMagick, so `build-icons.py` defines the geometry once as constants and generates both the SVG text and the bitmaps from them — they cannot drift apart, because neither is the source.
The catch is that the bitmap path reproduces `stroke-linejoin="round"` by hand (a filled polygon, one line per edge, a disc at each vertex) at 16x supersampling, which is only correct as long as it matches what a browser does with the SVG.
That is what `check-icons.py` is for: it renders the served `favicon.svg` in headless Chrome at 512 px and diffs it against the same call the PNGs come from.
Current agreement is a mean absolute difference of 0.44/255, with the 0.3% of pixels that differ by more than 32 confined to antialiased edges.
Note for whoever runs it: headless Chrome writes the screenshot but does not always exit here — its updater keeps the process alive — so the script waits on the file and then terminates the process rather than waiting on exit.

Verified against `wrangler dev` on Node 22: `/favicon.svg` returns 200 `image/svg+xml`, `/favicon.ico` returns 200 `image/vnd.microsoft.icon`, `/apple-touch-icon.png` returns 200 `image/png`, and all three hash-match the repo files.
`/assets/build-icons.py` and `/assets/check-icons.py` return 404.
All three link tags reach the served HTML and the item 11 JSON-LD still parses with its three `@graph` nodes.

This unblocks the `logo` half of item 11, which is now also done.

---

## Tier 2 — Trust and conversion

### 5. The About card is half-built

- [x] Add the name, role, and credentials list to the About card.

**Where:** Markup at `public/index.html:821-823`; unused CSS at `public/index.html:437-441`

**Problem:** The CSS defines `.about-card h3`, `.role`, and a full `.credlist` with checkmark icons, but the card contains only the avatar.
It renders as a large sticky card holding a photo and a lot of empty space.

**Why it matters:** The three strongest credentials — NYC high school CS teacher, professional software engineer, and 1:1 aide for children with autism — are buried mid-paragraph where a skimming parent misses them.
The design clearly anticipated this checklist; the markup just never got written.

**Fix:** Populate the card with the name, a role line, and a `.credlist` of the three credentials.

**Status (2026-08-20):** Done.

- `public/index.html:826-845` — the card contents: name, role line, and the three credentials as a `.credlist`.
- `public/index.html:418-425` — a new `.about-who` wrapper rule; the `max-width: 360px` cap moved onto it from `.avatar`.
- `public/index.html:441` — `.about-card h3` is now `.about-card h2`, plus the margin that separates the name from the circle.

The credential wording matches the item 11 `Person` node exactly, so the page and its structured data say the same three things.
The checkmark is the same path, stroke and join as the hero meta row's, at the 18px the `.credlist svg` rule already specified.
The prose column is untouched — it still tells the same story in sentences, which is the point: the card is the skimmable version of it.

**The heading is an `h2`, not the `h3` the CSS named.**
This is the one departure worth a look.
The About section has no heading of its own — the prose opens with an `.eyebrow` span and goes straight into paragraphs — so the nearest heading above this card is the hero `h1`.
An `h3` there would have made the document's only heading-level skip, `h1` straight to `h3`, in a file where every other section runs `h2` then `h3`.
Since "Luke Conley" is in substance the About section's heading, `h2` is both the correct level and an honest description of the section, and it costs one character in the selector.
The rendered size is unchanged: the rule still sets `font-size: 1.25rem`, which beats the UA default either way.

**The 360px cap moved from `.avatar` to the block as a whole.**
Item 2 capped the circle so it would not balloon to full width once the card goes single-column below 860px.
With text under it that cap had to cover the text too, or a tablet at 859px would have shown a 360px circle centred over credential lines running the full 763px of card.
So `.about-who` carries the cap and the auto margins, `.avatar` is plain `width: 100%` inside it, and the circle, the name, the role and the three list items share one left edge at every width.
Measured: those five left edges agree to within 0.5px at 320, 390, 430, 600, 768, 859, 860, 1000 and 1280px.
The circle itself did not move — checked against a copy rolled back to the old rule (cap on `.avatar`, no wrapper, no text), the two agree to the hundredth of a pixel at all of those widths plus 458, where the cap starts engaging.

The avatar lost its `role="img" aria-label="Luke Conley"`.
The label was the only way a screen reader got the name; now the name is the heading directly beneath it, and repeating it would announce "Luke Conley" twice in a row.
A `div` with a CSS background is already ignored without those attributes, so removing them is the whole fix.

Verified against `wrangler dev` on Node 22, by driving a headless Chrome at nine widths from 320 to 1280: no horizontal overflow, nothing escaping the card's padding box, the avatar still square, the icons still 18px, the heading order now stepping 1 → 2 with no skip, and the `.about-who` block never wider than its cap.
The sticky card is at most 604px tall, so with `top: 90px` it needs 694px of viewport height — inside a 720px laptop.
Items 1, 4, 9 and 11 are intact — seventeen og/twitter tags, three icon links, three `aria-roledescription="slide"` groups with exactly two remaining `role="tab"` attributes, and the JSON-LD still parsing with its three `@graph` nodes.
`check-bookbar.py` still passes all eight runs against the served site.

**Not done:** the prose still repeats the three credentials in its second paragraph, and the two now sit side by side on desktop.
Whether that reads as reinforcement or as repetition is a copy call for Luke, not a markup one.

---

### 6. No answers to practical parent questions

- [X] Add an FAQ section.

**Where:** New section, likely between `#approach` and `#book`

**Problem:** The page covers who Luke is, what the method is, and what it costs, but not the logistics.

**Missing answers:**

- How long is a typical session, and how often?
- What makes this different from other math tutoring?
- What is the cancellation policy?
- What does my kid need — computer, browser, headphones?


**Why it matters:** These are the questions a parent needs settled before booking at this price point.

---

### 7. Only one testimonial

- [ ] Collect and add two more testimonials.

**Where:** `public/index.html:843-861`

**Problem:** The single testimonial is strong but singular.

**Why it matters:** Two or three reviews shift the impression from "a nice review" to "a pattern."

**Note:** `algie_photo.png` sits unused in the repo root, and `.tcard .who .pfp` is styled at `public/index.html:466-470` but never rendered.
Worth wiring up when the testimonial section is revisited.

---

## Tier 3 — Accessibility and polish

Note: the reduced-motion handling is already thorough.
It freezes the SMIL animations on a settled frame, disables carousel autoplay, and skips the reveal transitions.
The items below are the remaining gaps.

### 8. Carousel has no pause control

- [x] Add a visible pause/play button to the carousel.

**Where:** `public/index.html:737-750` (the controls row) and `public/index.html:968-1024` (the auto-advance script)

**Problem:** The carousel auto-advances every 5.2 seconds.
Hover and focus pause it, but neither is available to a touch user who has not set an OS reduced-motion preference.

**Why it matters:** This is a WCAG 2.2.2 (Pause, Stop, Hide) miss.
The copy sells patience and meeting kids where they are, so a moving element a parent cannot stop is off-message.

**Status (2026-08-20):** Done.

- `public/index.html:794-799` — the button, first in the controls row.
- `public/index.html:306-312` and `:326-331` — the controls-row grid and the two icon states.
- `public/index.html:1113-1200` — the carousel script: one `paused` flag, a `setPaused` that owns the button and both kinds of motion, and hover/focus demoted to a plain `stop`.

**The button stops the drawings too, not just the auto-advance.**
This is slightly wider than the item as written, and it is the part worth a second look.
The slide rotation is the obvious moving thing, but each example also draws itself in an endless SMIL loop — the turtle crawls, the laser fires, the squares fade in and out, forever.
Under SC 2.2.2 those loops are the same kind of problem as the rotation, and a control that froze the carousel while the turtle kept crawling would be a pause button that visibly does not pause the card.
The reduced-motion path already froze them, so the machinery existed; the button just calls it.
Hover and focus deliberately do *not* freeze the drawings — they suspend the timer only, because a card that lurches to a halt under a passing cursor is worse than one that keeps drawing.

**Reduced motion now chooses the starting state rather than disabling the control.**
It used to be a hard gate: `restart()` checked `reduce` and never started a timer.
Now `reduce` only seeds `paused`, so a visitor with that preference lands on a still card showing a Play button, and can start it if they want to watch.
That is one state variable instead of two overlapping ones, and it means the same button is meaningful in both directions for every visitor.

**The control row is a three-column grid now.**
It was `justify-content: space-between` over prev, dots, next, which centred the dots exactly because the two end buttons are the same width.
A fourth item breaks that, and the button is `hidden` without JS, so auto-placement would have shifted the dots depending on whether a script ran.
Explicit `grid-column` on each of the three cells — play/pause left, dots centre, prev and next paired right — holds the dots at dead centre either way.
Measured at 0.00px off centre with JS on and with JS off, at 360, 390, 430 and 900px.
The row's height is unchanged at 32px.

Three smaller decisions:

The button ships `hidden` in the markup and the carousel script unhides it.
With JS off nothing auto-advances, so a play/pause control would be a dead button; this way it simply is not there.
That needed an explicit `.cbtn[hidden] { display: none; }`, because `.cbtn` sets `display: inline-grid` and an author rule beats the UA rule for `[hidden]`.

The accessible name changes with the state — "Pause the examples" and "Play the examples" — rather than a fixed name plus `aria-pressed`.
That is the media-player convention, and it keeps the name saying the same thing the icon says.

Stepping through slides by hand does not resume a stopped carousel.
`go()` calls `restart()`, which now consults `paused`, so prev, next and the dots stay usable while the card is stopped — which is the point of stopping it.

Verified against `wrangler dev` on Node 22, by driving a headless Chrome at 360, 390, 430 and 900px and watching the card for 6.4 seconds after each click — longer than one 5.2s period, so "did not advance" means the interval is really gone rather than that the sample landed inside one.
Playing: the slide advances and the SMIL clock gains 6.4s.
Paused: neither moves, and stepping with prev, next or a dot leaves it that way.
Resumed: both run again.
The 390px reduced-motion run does the same sequence inverted, starting stopped.
Unlike item 12's booking bar, this did not get a checked-in checker — it is one flag and two calls, and a script to watch it was more machinery than the behaviour warrants.

Items 1, 4, 9 and 11 are intact — seventeen og/twitter tags, three icon links, three `aria-roledescription="slide"` groups with exactly two remaining `role="tab"` attributes, and the JSON-LD still parsing with its three `@graph` nodes.
`check-bookbar.py` still passes all eight runs against the served site.

**Not done:** the dots are still 9px with 8px between them, which is under the WCAG 2.5.8 target-size floor on a phone.
That is item 9's territory and can be fixed with no visual change at all, by growing each dot's hit area behind it.

---

### 9. Carousel dots claim to be tabs but control nothing

- [x] Either wire up the tab semantics or drop to plain buttons.

**Where:** `public/index.html:706-709` (was listed as `:615-619` before the item 11 JSON-LD shifted line numbers)

**Problem:** The dots carry `role="tab"` inside a `role="tablist"`, but have no `aria-controls` and the slides are not `tabpanel`s.
A screen reader announces a tab interface that does not exist.

**Fix:** Add `aria-controls` and `role="tabpanel"` with IDs on each slide, or remove the tab roles and use labelled buttons.

**Status (2026-08-17):** Done, via the second option — the tab roles are gone.

The card already declares `role="group" aria-roledescription="carousel"` and has prev/next buttons, so a slide picker is the pattern it was actually built as.
Wiring real tabs would have meant adding roving tabindex and arrow-key handling, duplicating the Approach-tabs widget lower in the file, and a selection that moves on its own every 5.2 seconds fights the tab model.

- `.carousel-dots` is now `role="group"` so its `aria-label="Choose an example"` still has an element that can take a name.
- The dots are plain buttons labelled `Show example N of 3: <name>`, with `aria-current="true"` on the one whose slide is on screen.
  The old labels were bare nouns like "Spiral", which did not say the control did anything.
- Each `.slide` got `role="group" aria-roledescription="slide"` with an `N of 3` label, so the carousel roledescription on the card is no longer dangling over unlabelled divs.
  That was slightly outside the letter of this item, but it is the other half of the same broken-semantics problem.
- The JS `show()` now sets and removes `aria-current` instead of writing `aria-selected` on every advance.

CSS keyed off `.cdot.is-active`, not `aria-selected`, so the visuals are unchanged.
The genuine tab widget at `public/index.html:775-776` was left alone; it has proper `aria-controls` and `tabpanel`s.

Verified against `wrangler dev` on Node 22: the served HTML has three `aria-roledescription="slide"` groups and exactly two remaining `role="tab"` attributes, both belonging to the Approach tabs.

---

### 10. Stray 20px indent in the hero meta row

- [x] Delete the empty span.

**Where:** `public/index.html:522` (was listed as `:433` before the item 11 JSON-LD shifted line numbers)

**Problem:** An empty `<span aria-hidden="true"></span>` sits as the first child of `.hero-meta`.
That container is a flex row with `gap: 1.25rem`, so the zero-width span still contributes a gap.

**Result:** The first item in that row is pushed 20px right of the headline, lede, and buttons stacked above it.

**Fix:** Delete the span.

**Status (2026-08-17):** Done.
The empty span is gone, so `.hero-meta` now starts flush with the headline, lede, and buttons above it.

---

### 11. Missing `robots.txt`, `sitemap.xml`, and JSON-LD

- [x] Add all three.
- [x] Add `image` and `logo` to the JSON-LD once the item 1 and item 4 assets exist.
- [ ] Submit the sitemap in Google Search Console.

**Where:** `public/`

**Problem:** None of the three exist.

**Why it matters:** A `LocalBusiness` or `Person` JSON-LD block is what surfaces the site in local results for searches like "coding tutor Bushwick."

**Status (2026-08-17):** All three now exist.

- `public/robots.txt` — allow-all with a `Sitemap:` pointer.
- `public/sitemap.xml` — the single URL `https://conleytutoring.com/`, `lastmod` 2026-08-17.
- `public/index.html:41-127` — a `@graph` with three nodes.
  A combined `LocalBusiness` + `EducationalOrganization` node carrying a Brooklyn/NY address, `areaServed`, `priceRange`, and an `OfferCatalog` for the $150 online service.
  (2026-08-20: in-person tutoring came off the site, so the $250 offer is gone, `priceRange` is now a single number, and the seven `areaServed` neighborhoods — a travel radius, sourced from the rates note that no longer exists — were replaced by the United States. That last one is the piece worth a second look: it trades local-search reach for the online service's actual reach.)
  A `Person` node for Luke Conley, linked as `founder`.
  A `WebSite` node.

A `rel="canonical"` link was added directly above the JSON-LD so the sitemap URL and the page agree.
That was outside the scope of this item.

Verified against `wrangler dev`: `/robots.txt` returns 200 `text/plain`, `/sitemap.xml` returns 200 `application/xml`, and the JSON-LD parses and reaches the served HTML.
Note that `wrangler dev` requires Node 22; the repo default of Node 18 cannot run it.

**Update (2026-08-20):** The `image` and `logo` sub-item is done.
The `#business` node now carries `"image": "https://conleytutoring.com/og-image.jpg"` (item 1) and `"logo": "https://conleytutoring.com/favicon.svg"` (item 4), which is what Google treats as required for local rich results.
Both were blocked on assets that now exist, so this was two lines rather than a piece of work of its own.

`aggregateRating` was deliberately omitted.
There is one self-hosted testimonial, and marking that up risks a manual action from Google.
Revisit alongside item 7.

The sitemap also does nothing until it is submitted in Google Search Console, which is an off-repo step.

---

### 12. No CTA in the mobile header

- [x] Reconsider hiding the header CTA on small screens.

**Where:** `public/index.html:233-234`

**Problem:** `.header-cta` is hidden below 640px.

**Result:** Once a parent scrolls past the hero on a phone, there is no persistent way to book until they reach the bottom CTA band.

**Fix:** Show a compact version of the button in the sticky header on mobile, or add a small sticky bottom bar.

**Status (2026-08-20):** Done, via the second option — a sticky bottom bar.

- `public/index.html:215-225` — `.header-cta` and `.book-bar` now trade places across one `min-width: 640px` query, so exactly one of them can ever be on screen.
- `public/index.html:530-558` — the `.book-bar` rules.
- `public/index.html:1001-1007` — the bar itself: one full-width primary button, "Book a free intro call", with the same calendar icon the bottom CTA band uses.
- `public/index.html:1029-1051` — the script that tucks it away.
- `assets/check-bookbar.py` — drives a real Chrome over the DevTools Protocol and checks the whole thing at seven widths.

**The header option was measured first and rejected on arithmetic, not taste.**
At a 320px viewport `.wrap` is 280px wide.
The brand is 200.5px of that, so a button gets 63.5px after the flex gap — nothing fits.
Hiding the `Code · Math · Game Dev` tagline shortens the brand to 169.7px, which leaves 94.3px, and that is still short: "Book a free call" needs 137.3px and even "Book a call" needs 106.7px.
Only a bare "Book" (68.2px) fits, and dropping "free" — the word the hero, the CTA band, and the OG card all lead with — on the narrowest and most common phones is a bad trade for the one item on this list that is explicitly about the booking funnel.
Shrinking the type and the gap to buy the ~12px gets there with about 7px to spare, which is not enough slack to survive a system-font substitution, since the page loads no webfonts and renders in SF on iOS and Roboto on Android.
Left as-is, the button simply pushed the wordmark onto two lines and made the sticky header *taller* on a phone (84.2px against 74.7px), which is the opposite of the point.

The bar sidesteps all of it: full viewport width means the label is the real one, and it sits in the thumb zone.

**It hides whenever a real CTA is already on screen.**
An IntersectionObserver watches two gates — `.hero-actions` and `#book .cta-band` — and the bar is visible exactly when neither is.
So it never covers the hero's own buttons on first paint, and it never stacks a duplicate over the bottom CTA band.
The observer runs at every width even though CSS only shows the bar under 640px, so rotating a tablet across the boundary reveals an already-correct state rather than a stale one.

Three details that are easy to get wrong and are worth knowing about:

The bar defaults to *visible* in CSS and the script hides it, not the other way around, so it still works with JS off.
The cost is that the opening state has to be applied without animating, which is what the `is-animated` class is for — transitions are switched on one frame after the observer's first reading.

Tucking uses `visibility: hidden` alongside the transform.
A button moved off-screen by a transform is still focusable and still in the accessibility tree, so without it a phone keyboard user could tab into an invisible button.
The visibility flip is delayed until the slide finishes on the way out and is immediate on the way in, which works because a transition is read from the state being moved *to*.

That delay needed its own reduced-motion rule.
The global `prefers-reduced-motion` block zeroes `transition-duration` but not `transition-delay`, so the transform would snap while visibility still waited 250ms.
`.book-bar` drops its transition entirely under that query.

**On the checker.** The gating is behaviour, not geometry, so nothing static can see it.
`check-bookbar.py` launches headless Chrome with a debugging port, emulates a phone with `Emulation.setDeviceMetricsOverride` — headless clamps `--window-size` to a 500px minimum, so 320px is unreachable any other way — then scrolls to five element-anchored stops and reads the bar at each.
It asserts the contract rather than hardcoded positions: the bar is on screen exactly when no gate is, plus no horizontal overflow, no label overflow, a >=44px touch target, the bar seated on the viewport floor, the bar on top at its own centre, and the footer never obscured.
A final guard fails the run if the stops never exercised both states, so it cannot pass vacuously.
It runs the 640px boundary from both sides and repeats one width with `prefers-reduced-motion: reduce`, since that is now a separate code path.

Two notes for whoever runs it next.
Chrome rejects the DevTools websocket with a 403 unless the `Origin` header is suppressed, and the page sets `scroll-behavior: smooth`, so every scroll in the probe is explicitly `behavior: 'instant'` — a `position: fixed` bar does not move while the page is still gliding, so a naive settle check reads as finished and samples the wrong scroll position.

Verified against `wrangler dev` on Node 22: all eight runs pass against the served site, and `/assets/check-bookbar.py` returns 404.
Items 1, 4, and 11 are intact — seventeen og/twitter tags, three icon links, and the JSON-LD still parsing with its three `@graph` nodes.
Page height is unchanged at every width, so nothing here moved the layout.

**Not done:** the bar is a phone-width element and the desktop header CTA is untouched.
Whether the tagline should also come out of the header on phones is now an independent question rather than a prerequisite, and it would shave about 12px off the sticky header's height.
