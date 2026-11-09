// jsdom has no media queries: tests run at desktop width unless they stub `matchMedia`.
globalThis.matchMedia = (query: string) =>
  ({
    matches: false,
    media: query,
    addEventListener() {},
    removeEventListener() {},
  }) as unknown as MediaQueryList;
