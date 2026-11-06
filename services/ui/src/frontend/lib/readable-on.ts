/**
 * Choosing label text a brand colour can actually be read against.
 *
 * A deployment sets its own primary colour, and the label on top of
 * it was taken from the page's foreground — near-black on a dark
 * blue in the light theme, near-white on a light blue in the dark
 * one. Both are the same colour twice, and the most prominent
 * button in the interface failed to meet the contrast bar in either.
 */

const LIGHT = '#ffffff';
const DARK = '#0f1117';

function channels(colour: string): [number, number, number] | null {
  const hex = colour.trim().replace(/^#/, '');
  const full =
    hex.length === 3
      ? hex
          .split('')
          .map((c) => c + c)
          .join('')
      : hex;
  if (!/^[0-9a-f]{6}$/i.test(full)) return null;
  return [
    parseInt(full.slice(0, 2), 16),
    parseInt(full.slice(2, 4), 16),
    parseInt(full.slice(4, 6), 16),
  ];
}

function luminance(rgb: [number, number, number]): number {
  const [r, g, b] = rgb.map((value) => {
    const channel = value / 255;
    return channel <= 0.03928 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** How far apart two colours are, 1 (identical) to 21 (black on white). */
export function contrastRatio(a: string, b: string): number {
  const first = channels(a);
  const second = channels(b);
  if (!first || !second) return 1;
  const [lighter, darker] = [luminance(first), luminance(second)].sort((x, y) => y - x);
  return (lighter + 0.05) / (darker + 0.05);
}

/** Whichever of light or dark text reads better on this background. */
export function readableOn(background: string): string {
  if (!channels(background)) return LIGHT;
  return contrastRatio(LIGHT, background) >= contrastRatio(DARK, background)
    ? LIGHT
    : DARK;
}
