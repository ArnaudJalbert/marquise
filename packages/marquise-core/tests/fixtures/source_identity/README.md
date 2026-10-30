# Captured source evidence

Captured on 2026-10-30. Tests replay these files over loopback HTTP and never fetch providers.

- `carrie-schedule.html`: the Carrie `gMovieData` entry from `https://omniwebticketing6.com/cinematheque/?schdate=2026-10-30`. Other films, scripts and ticketing UI were removed.
- `carrie-index.html`: the unmodified ticket modal and film card for Carrie from `https://www.cinematheque.qc.ca/en/cinema/`. The card's modal target links the cinema page to dated ticket performance 14321. No title matching is involved.
- `carrie-detail.html`: the labelled film facts grid from `https://www.cinematheque.qc.ca/en/cinema/carrie/`. Navigation, synopsis, biography and related films were removed. The labels and facts retain the captured provider markup.
- `la-bola-negra.html`: the `movieDetails` object from the `__NEXT_DATA__` script at `https://www.cineplex.com/movie/la-bola-negra`. Other Next.js data was removed. The provider director field is `Javier Calvo and Javier Ambrossi `.

A temporary browser-compatible research client obtained the Cinémathèque capture because ordinary HTTP received a Cloudflare challenge. No extra runtime dependency was added. A challenge, missing page, unlinked card or network failure keeps the ticketing facts as the import fallback.
