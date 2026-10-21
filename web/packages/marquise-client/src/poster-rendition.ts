/**
 * Per-host allowlist that swaps known-hosted poster URLs for a smaller
 * rendition. Only hosts whose resizing contract is confirmed belong here;
 * the original URL is always returned unchanged for anything else, so a
 * wrong guess can only cost bandwidth, never break the image.
 */
// Covers 150 px grid tiles at 3x DPR; detail-page posters get 450/200 ~2x.
const RENDITION_WIDTH = 450;

export function posterRenditionUrl(
  posterUrl: string | null | undefined,
): string | null | undefined {
  if (!posterUrl) return posterUrl;
  let url: URL;
  try {
    url = new URL(posterUrl);
  } catch {
    return posterUrl;
  }
  if (url.protocol !== "https:") return posterUrl;

  // img.cinemacinema.ca serves originals up to 60 MB; its Cloudflare front
  // resizes on request via /cdn-cgi/image/.
  if (url.hostname === "img.cinemacinema.ca" && !url.pathname.startsWith("/cdn-cgi/")) {
    url.pathname = `/cdn-cgi/image/width=${RENDITION_WIDTH},quality=80,format=auto${url.pathname}`;
    return url.href;
  }

  // TMDB encodes the rendition in the path; w500 is plenty for poster tiles.
  if (url.hostname === "image.tmdb.org") {
    const size = /^\/t\/p\/(original|w(\d+))\//.exec(url.pathname)?.[1];
    if (size && (size === "original" || Number(size.slice(1)) > 500)) {
      url.pathname = url.pathname.replace(`/t/p/${size}/`, "/t/p/w500/");
      return url.href;
    }
  }

  return posterUrl;
}
