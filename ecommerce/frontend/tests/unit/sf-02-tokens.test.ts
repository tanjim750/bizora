import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

function hexToRgb(hex: string): [number, number, number] {
  const clean = hex.replace('#', '');
  const num = parseInt(clean, 16);
  return [(num >> 16) & 255, (num >> 8) & 255, num & 255];
}

function relativeLuminance(r: number, g: number, b: number): number {
  const srgb = [r / 255, g / 255, b / 255].map((v) =>
    v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4),
  );
  return 0.2126 * srgb[0] + 0.7152 * srgb[1] + 0.0722 * srgb[2];
}

function contrastRatio(hex1: string, hex2: string): number {
  const [r1, g1, b1] = hexToRgb(hex1);
  const [r2, g2, b2] = hexToRgb(hex2);
  const l1 = relativeLuminance(r1, g1, b1);
  const l2 = relativeLuminance(r2, g2, b2);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

describe('SF-02 Design Tokens & Guard', () => {
  const tokensPath = path.resolve(process.cwd(), 'src/styles/tokens.css');
  const globalsPath = path.resolve(process.cwd(), 'src/app/globals.css');

  it('parses tokens.css and passes WCAG contrast checks for both light and dark themes', () => {
    expect(fs.existsSync(tokensPath), 'src/styles/tokens.css must exist').toBe(true);
    const content = fs.readFileSync(tokensPath, 'utf8');

    const rootMatch = content.match(/:root\s*\{([^}]+)\}/);
    expect(rootMatch, ':root block must be present').toBeTruthy();
    const rootBlock = rootMatch![1];

    const darkMatch = content.match(/\.dark\s*\{([^}]+)\}/);
    expect(darkMatch, '.dark block must be present').toBeTruthy();
    const darkBlock = darkMatch![1];

    function extractTokens(block: string): Record<string, string> {
      const tokens: Record<string, string> = {};
      const regex = /--aur-([\w-]+)\s*:\s*(#[0-9a-fA-F]{6})/g;
      let match;
      while ((match = regex.exec(block)) !== null) {
        tokens[match[1]] = match[2].toUpperCase();
      }
      return tokens;
    }

    const lightTokens = extractTokens(rootBlock);
    const darkTokens = extractTokens(darkBlock);

    for (const [themeName, tokens] of [
      ['light', lightTokens],
      ['dark', darkTokens],
    ] as const) {
      const required = [
        'bg',
        'surface',
        'surface-2',
        'fg',
        'fg-muted',
        'border',
        'border-strong',
        'accent',
        'accent-fg',
        'success',
        'danger',
        'warning',
        'focus',
      ];
      for (const req of required) {
        expect(tokens[req], `${themeName} token --aur-${req} must be present as hex`).toBeDefined();
      }

      const backgrounds = [tokens['bg'], tokens['surface'], tokens['surface-2']];
      const textColors = [
        'fg',
        'fg-muted',
        'accent',
        'success',
        'danger',
        'warning',
        'focus',
      ] as const;

      for (const textColorKey of textColors) {
        const hex = tokens[textColorKey];
        for (const bg of backgrounds) {
          const ratio = contrastRatio(hex, bg);
          expect(
            ratio,
            `${themeName} ${textColorKey} (${hex}) on ${bg} must have contrast >= 4.5 (got ${ratio.toFixed(2)})`,
          ).toBeGreaterThanOrEqual(4.5);
        }
      }

      // accent-fg on accent >= 4.5
      const accentRatio = contrastRatio(tokens['accent-fg'], tokens['accent']);
      expect(
        accentRatio,
        `${themeName} accent-fg on accent must have contrast >= 4.5 (got ${accentRatio.toFixed(2)})`,
      ).toBeGreaterThanOrEqual(4.5);

      // border-strong on bg and surface >= 3.0
      expect(
        contrastRatio(tokens['border-strong'], tokens['bg']),
        `${themeName} border-strong on bg must have contrast >= 3.0`,
      ).toBeGreaterThanOrEqual(3.0);
      expect(
        contrastRatio(tokens['border-strong'], tokens['surface']),
        `${themeName} border-strong on surface must have contrast >= 3.0`,
      ).toBeGreaterThanOrEqual(3.0);
    }
  });

  it('enforces token guard across all src/ files', () => {
    const srcDir = path.resolve(process.cwd(), 'src');

    function checkDir(dir: string) {
      const entries = fs.readdirSync(dir, { withFileTypes: true });
      for (const entry of entries) {
        const fullPath = path.join(dir, entry.name);
        if (entry.isDirectory()) {
          checkDir(fullPath);
        } else if (
          (entry.name.endsWith('.ts') ||
            entry.name.endsWith('.tsx') ||
            entry.name.endsWith('.css')) &&
          fullPath !== tokensPath
        ) {
          const text = fs.readFileSync(fullPath, 'utf8');

          expect(
            text.match(/#[0-9a-fA-F]{3,8}\b/),
            `File ${fullPath} contains raw hex color`,
          ).toBeNull();
          expect(text.match(/\brgba?\(/), `File ${fullPath} contains rgb/rgba()`).toBeNull();
          expect(text.match(/\bhsla?\(/), `File ${fullPath} contains hsl/hsla()`).toBeNull();
          expect(text.match(/\boklch\(/), `File ${fullPath} contains oklch()`).toBeNull();
          expect(
            text.match(/\b[a-z-]+-\[[^\]]*\d(px|rem|em|vh|vw|svh|dvh|%)\]/),
            `File ${fullPath} contains arbitrary tailwind value with units`,
          ).toBeNull();
        }
      }
    }

    checkDir(srcDir);
  });

  it('globals.css includes required setup rules', () => {
    expect(fs.existsSync(globalsPath), 'src/app/globals.css must exist').toBe(true);
    const content = fs.readFileSync(globalsPath, 'utf8');

    expect(content).toContain('--color-*: initial');
    expect(content).toContain('@custom-variant dark');
    expect(content).toContain('@utility pb-safe');
  });
});
