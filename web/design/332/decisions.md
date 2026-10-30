# Approved prototype decisions, October 30, 2026

Arnaud approved the interactive prototype in PR #339: “Ok I am happy with this prototype”. This record and issues #331 through #338 describe the reviewed direction. Prototype approval does not establish production integration, release readiness, or permission to deploy.

## Navigation and discovery

- Screenings, Movies, and Cinemas are separate views. Their navigation links stay visible throughout the experience and highlight the selected section.
- Screenings opens on today's Montréal listings with date/title controls and a four-column desktop, two-column mobile poster grid. There is no redundant Screenings heading.
- Movies shows catalogue entries by default from the movies endpoint, independently of screening dates. Its full-width search has an accessible name, no visible label, and no surrounding box. Selecting a result opens movie detail.
- Cinemas lists venues and opens a venue page using the shared grid with the cinema fixed.
- Each view has a collapsed “About this section” containing a short explanation and an example. Screenings explains planning Monday through Friday next week; Movies explains checking whether a wanted film screens soon; Cinemas explains checking a favorite venue. There is no separate site-wide introduction.

## Filters and preview

- Date shortcuts highlight when their complete range matches the selection. Filters stays beside Today, Tomorrow, and This weekend when opened. Its bounded panel overlays the page, with a compact Clear filters button in a footer row.
- Daily time uses two handles sharing the midnight-to-midnight scale, whole-hour steps, floor rounding, and no crossing. The full-day range is unrestricted.
- Language display and filters use source acronyms such as VO, VOA, VOF, VOSTF, VOSTA, and VF.
- The compact next-three-screenings preview floats below the card and over later posters without reflowing the grid. It has no “Next screenings” heading or leftover heading space.
- Keep actual booking links; missing links remain plain text. Local sample links are explicitly fictional.

## Movie schedule

- A small poster and compact metadata lead into the schedule. Movie-page filters are independent of listing filters.
- Dates run horizontally across the top. By date is the default: each column independently stacks the cinemas that have showtimes that day. It does not force placeholder cinemas or dashes.
- Optional By cinema keeps those date columns and places cinemas in rows. The cinema-name column stays fixed. The alternate stacked layout was removed.
- Show one to four dates, default four. Arrows move exactly one date. Today returns to the current Montréal day. Navigation requests the new server date window, including all pages within that window.
- Animate explicit date changes only. Do not animate initial load/refresh or move cinema-name cells. Honor reduced motion.
- Human-readable ranges read like “Friday October 30th to Monday November 2nd”. Underline the dates, not “to”; omit “to” for a single date.
- Keep Filters, Group by, Today, and Days together. Date columns have visible vertical separators, inset horizontal lines, side padding, neutral hover highlights, and consistent cinema-group alignment.
- Dune's sample schedule has 25 screenings each day across seven cinemas over two weeks. Other fixtures cover sparse schedules, including one screening. All six normal fixture films have local posters; runtime missing-poster handling remains available.

## Production ownership

| Issue | Work |
| --- | --- |
| #331 | Updated parent specification |
| #332 | Approved prototype and evidence |
| #333 | Separate navigation views and real API browsing, including catalogue movies |
| #334 | Movie schedule layouts, date navigation, filters, complete requested windows |
| #335 | Shared screening filters, slider, shortcuts, and filter overlay |
| #336 | Bounded automatic pagination and navigation restoration for both browse modes |
| #337 | Cinema directory and fixed-cinema pages |
| #338 | Integrated production verification and current browser evidence |
