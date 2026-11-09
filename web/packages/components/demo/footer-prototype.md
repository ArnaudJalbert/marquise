# Compact footer prototype

Build a portable HTML review artifact from `web/`:

```sh
pnpm prototype:footer
```

Open `web/packages/components/demo-dist/footer/index.html` directly. The generated file embeds all poster assets and needs no server, package installation, or backend. Hash routes keep information pages and browser Back working when opened as a file.

This is one agreed design, rather than a set of competing variants. It follows the current minimalist layout but does not run the production application. The scope is the compact footer, header Info navigation, responsive wrapping, and About, Contact, Terms, and Privacy page layouts.

Try the Info menu with mouse and keyboard, Escape, each footer link, browser Back, and a narrow window. API docs is an external link in the same tab. About includes draft coverage, booking, and source-credit copy. Contact uses an explicitly labeled reserved example address. Terms and Privacy are visibly marked placeholders.

Listings, dates, and cinemas are review fixtures. Search filters the four sample films. Date shortcuts change the displayed selection, with no schedule queries. Real pagination, booking, and production data are outside this prototype.

No production entry point imports these files. The artifact is generated under the already ignored `demo-dist/` directory. Keep this throwaway source separate from any later production implementation.
