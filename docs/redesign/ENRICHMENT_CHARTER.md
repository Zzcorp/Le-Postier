# Enrichment charter — polish the ORIGINAL design in place

The owner restored the original design after a full redesign went too far. The instruction now:
« half way — same format, better icons, no childish emojis, improved styling and UX ». This charter
is the law for every enrichment edit. When in doubt: DON'T.

## Absolutely unchanged (touching these = failure)

- **Backgrounds and palette**: body `#1a1208` dark brown, the ochre header gradient
  (`rgba(181,96,11,.98) → rgba(160,80,8,.98)`), dark dropdown/mobile panels, all existing section
  backgrounds. Zero new background colors.
- **Layout and format**: every page keeps its structure, grid, section order, sizes. No element
  moves, appears, or disappears (except emoji ornaments, below).
- **Behavior**: all JS logic, click flows, popups, zoom, likes, forms, endpoints — byte-identical
  semantics. Only presentation-layer touches.
- **French copy**: unchanged (except copy that IS an emoji ornament).
- **Fonts**: the existing stack ("Bookman Old Style", Georgia, serif). Do not add webfonts.

## Required improvements

1. **Emoji ornaments → inline SVG icons.** Every emoji used as UI decoration (🖱️ 🎬 ❤️ ✉️ 📮 ⭐ 🔍
   ✨ 🐟 arrows, sparkles, dust/particle emoji animations, etc.) is replaced by a clean inline SVG
   glyph — Feather style: `viewBox="0 0 24 24"`, `fill="none"`, `stroke="currentColor"`,
   `stroke-width="2"`, `stroke-linecap="round"`, `stroke-linejoin="round"`, `aria-hidden="true"`,
   sized 16–20px via width/height attributes, inheriting the text color. If an emoji ornament has no
   meaningful glyph replacement (floating fish/sparkle ambient animations), REMOVE it cleanly
   (remove its markup+CSS+JS interval). Emojis that are DATA stay (e.g. country-flag emojis in
   admin analytics).
2. **Raster UI icons → SVG** where a PNG/JPG is used as a small interface glyph (burger_icon.png,
   close_icon.png/jpg, Loupe_icone.png, gallerie_icone.png, fleche/arrow PNGs…): replace the <img>
   with an equivalent inline SVG at the same size and color treatment. Brand/content images
   (Samathey logo, stamps, postcard art, Carte_Membre, decor photos) stay as they are.
3. **Consistency polish, within the existing look**: unify border-radius (pick the value already
   dominant in that file), unify box-shadow style (soft dark, no harsh pure-black spread),
   unify transition durations (150–250ms ease) on existing hover states, align button/input
   padding within a page. Use ONLY colors already present in the file.
4. **UX finish**: visible `:focus-visible` outline (2px, the ochre `#B5600B` family already in use)
   on interactive elements; `cursor:pointer` where missing; `loading="lazy" decoding="async"` on
   below-fold `<img>` where missing; `aria-label` on icon-only buttons; touch targets nudged to
   ≥40px via padding (without changing visual size perceptibly — padding+negative margin allowed).
5. **Dead weight**: remove CSS rules/JS intervals that only served removed emoji ornaments.

## Validation for every edited file

- Templates: parse with the Django 5.2 engine (project venv `./.venv/Scripts/python.exe`).
- JS files: `node --check`.
- No new external requests, no new files except nothing — all edits in place.