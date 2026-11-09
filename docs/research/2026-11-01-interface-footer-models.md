---
type: research
status: complete
date: 2026-11-01
---

# Interface footer models

## Scope

Research examples and a fit recommendation for adding About, API, and legal destinations to Marquise's public interface. No prototype or implementation was produced.

## Marquise context

The production app composes `MinimalExperience` from `web/packages/components`. Its page shell currently has no site-wide footer. The older discovery experience has a small footer with the Marquise wordmark, one local-purpose sentence, and a discovery link. The app also has an unused one-line `Footer` component. The current design keeps section explanations inside each view rather than adding a site-wide introduction, according to `web/design/332/decisions.md`.

The repository README links to the live API docs at `https://marquise-api.fly.dev/docs`. A browser fetch of that endpoint was unavailable during this research, so the destination is confirmed from project documentation rather than live inspection. The repository search did not find About, Terms, or Privacy destinations.

## Models

### Compact utility links

One small group of links, followed by a restrained attribution and legal line. Letterboxd's current homepage groups About, Pro, News, Apps, Help, Terms, API, and Contact together. Its bottom line carries copyright, film-data attribution, Privacy, and Cookies. This lets users find secondary destinations without turning the footer into another navigation page. [Letterboxd homepage](https://letterboxd.com/)

### Grouped directory

Several labeled columns divide links by audience or purpose, often including company, product, help, and legal. This works when a product has enough destinations to justify browsing the footer. Marquise currently has only a few known public destinations, so this model would add visual weight without much navigation value.

### Minimal legal strip

A short final row holds only copyright, privacy, and terms. It preserves a very quiet page but gives product information and developer access no obvious home. It can work if those destinations already live in the primary navigation or another persistent location.

### Split utility and attribution rows

The first row links to About, API documentation, help/contact, and policies. A second, quieter line contains copyright and required third-party credits. This is a useful compromise when legal and data credits need a clear place but should not compete with browsing.

## Fit for Marquise

The compact utility model is the best starting point. It matches the minimalist interface, is close to the existing older discovery footer, and supports the product's small number of secondary destinations. A short link row could include About, API docs, Contact, Terms, and Privacy. Copyright and any required data attribution can sit in a subdued line below.

Keep the API destination as a link to the dedicated API docs. TMDB's own developer documentation separates Guides and API Reference from the rest of its site navigation, which keeps technical detail out of a consumer interface footer. [TMDB developer FAQ](https://developer.themoviedb.org/docs/faq)

If Marquise displays TMDB data or images under a license that requires its standard attribution, TMDB says its attribution notice belongs in an About or Credits section. Confirm the applicable project terms before choosing exact wording or placement. [TMDB attribution requirements](https://developer.themoviedb.org/docs/faq#what-are-the-attribution-requirements)

A multi-column directory seems premature. The current interface's main job is browsing screenings, movies, and cinemas. A dense footer could compete with the poster and schedule content, while a single compact link group would expose the requested secondary pages at low visual cost.

## Sources

- Letterboxd homepage footer, live inspection on 2026-11-01: https://letterboxd.com/
- TMDB developer FAQ, API documentation navigation and attribution requirements: https://developer.themoviedb.org/docs/faq
- Marquise project README, API docs destination: `web/README.md`
- Marquise approved interface decisions: `web/design/332/decisions.md`
