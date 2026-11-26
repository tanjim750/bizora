import fs from 'node:fs';
import path from 'node:path';
import sharp from 'sharp';

const force = process.argv.includes('--force');

const productsFile = path.resolve('src/mocks/fixtures/products.json');
const productsData = JSON.parse(fs.readFileSync(productsFile, 'utf-8'));
const products = productsData.items;

const outProductsDir = path.resolve('public/mock/products');
const outEditorialDir = path.resolve('public/mock/editorial');
fs.mkdirSync(outProductsDir, { recursive: true });
fs.mkdirSync(outEditorialDir, { recursive: true });

function escapeXml(str) {
  return str.replace(/[<>&'"]/g, (c) => {
    switch (c) {
      case '<':
        return '&lt;';
      case '>':
        return '&gt;';
      case '&':
        return '&amp;';
      case "'":
        return '&apos;';
      case '"':
        return '&quot;';
      default:
        return c;
    }
  });
}

function makeSvg({ width, height, gradientType, color, text }) {
  let gradientDefs = '';
  if (gradientType === 1) {
    // vertical: color -> #ECE6DC
    gradientDefs = `
      <linearGradient id="g" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stop-color="${color}"/>
        <stop offset="100%" stop-color="#ECE6DC"/>
      </linearGradient>`;
  } else if (gradientType === 2) {
    // reversed vertical: #ECE6DC -> color
    gradientDefs = `
      <linearGradient id="g" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stop-color="#ECE6DC"/>
        <stop offset="100%" stop-color="${color}"/>
      </linearGradient>`;
  } else {
    // 45 degree: color -> #ECE6DC
    gradientDefs = `
      <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="${color}"/>
        <stop offset="100%" stop-color="#ECE6DC"/>
      </linearGradient>`;
  }

  return `
<svg width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" xmlns="http://www.w3.org/2000/svg">
  <defs>${gradientDefs}</defs>
  <rect width="${width}" height="${height}" fill="url(#g)"/>
  <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" font-family="Georgia, serif" font-size="64" letter-spacing="8" fill="#1C1A17" fill-opacity="0.55">${escapeXml(text)}</text>
</svg>`;
}

async function renderImage(svgStr, destPath) {
  if (fs.existsSync(destPath) && !force) {
    return false;
  }
  const buffer = Buffer.from(svgStr);
  await sharp(buffer).jpeg({ quality: 82 }).toFile(destPath);
  return true;
}

let writtenCount = 0;
let skippedCount = 0;

for (const prod of products) {
  const firstSwatch = prod.swatches?.[0]?.swatch || '#ECE6DC';
  const text = prod.name.toUpperCase();

  const configs = [
    { num: 1, grad: 1 },
    { num: 2, grad: 2 },
    { num: 3, grad: 3 },
  ];

  for (const cfg of configs) {
    const filename = `${prod.slug}-${cfg.num}.jpg`;
    const dest = path.join(outProductsDir, filename);
    const svg = makeSvg({
      width: 1600,
      height: 2000,
      gradientType: cfg.grad,
      color: firstSwatch,
      text,
    });
    const written = await renderImage(svg, dest);
    if (written) {
      console.log(`[wrote] public/mock/products/${filename}`);
      writtenCount++;
    } else {
      skippedCount++;
    }
  }
}

// Editorial images
const editorialConfigs = [
  {
    name: 'hero.jpg',
    width: 2400,
    height: 1600,
  },
  {
    name: 'workshop.jpg',
    width: 1600,
    height: 2000,
  },
];

for (const ed of editorialConfigs) {
  const dest = path.join(outEditorialDir, ed.name);
  const svg = makeSvg({
    width: ed.width,
    height: ed.height,
    gradientType: 1,
    color: '#B5694A',
    text: 'AURELO',
  });
  const written = await renderImage(svg, dest);
  if (written) {
    console.log(`[wrote] public/mock/editorial/${ed.name}`);
    writtenCount++;
  } else {
    skippedCount++;
  }
}

console.log(
  `\nDone. Written: ${writtenCount}, Skipped: ${skippedCount}, Total target: ${products.length * 3 + 2}`,
);
