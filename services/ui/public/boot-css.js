/**
 * Applies the main stylesheet once the document has parsed.
 *
 * The server emits it as `media="print"` so it does not block the first
 * paint: the boot shell it renders into #root is styled with inline `style`
 * attributes and needs nothing from this file. Flipping the media query
 * here applies it as soon as it has downloaded.
 *
 * This is a separate file rather than an inline `onload` handler because
 * the page is served with `script-src 'self'` — an inline handler never
 * runs, and the whole app renders unstyled.
 */
(function () {
  var links = document.querySelectorAll('link[data-main-css]');
  for (var i = 0; i < links.length; i++) links[i].media = 'all';
})();
