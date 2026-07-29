// Tạo biểu tượng PWA (PNG) từ favicon.svg
// Sử dụng sharp để render SVG thành các kích thước cần thiết:
//   - pwa-192x192.png        (biểu tượng thường)
//   - pwa-512x512.png        (biểu tượng thường)
//   - pwa-maskable-512x512.png (biểu tượng maskable, có đệm 10% an toàn)
//   - apple-touch-icon.png   (180x180 cho iOS)

import sharp from "sharp";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const publicDir = resolve(__dirname, "..", "public");
const svgPath = resolve(publicDir, "favicon.svg");

const svgBuffer = readFileSync(svgPath);

// Màu nền tối cho biểu tượng maskable (khớp với background_color trong manifest)
const MASKABLE_BG = "#0f172a";

// Kích thước canvas cho maskable: 512x512, vẽ SVG ở 80% (đệm ~10% mỗi bên)
const MASKABLE_SIZE = 512;
const SVG_RENDER_SIZE = Math.round(MASKABLE_SIZE * 0.8); // 409
const OFFSET = Math.round((MASKABLE_SIZE - SVG_RENDER_SIZE) / 2); // 51

async function generateStandardIcons() {
  // Biểu tượng 192x192
  await sharp(svgBuffer, { density: 384 })
    .resize(192, 192)
    .png()
    .toFile(resolve(publicDir, "pwa-192x192.png"));
  console.log("Đã tạo pwa-192x192.png");

  // Biểu tượng 512x512
  await sharp(svgBuffer, { density: 512 })
    .resize(512, 512)
    .png()
    .toFile(resolve(publicDir, "pwa-512x512.png"));
  console.log("Đã tạo pwa-512x512.png");
}

async function generateMaskableIcon() {
  // Tạo nền tối kích thước đầy đủ, sau đó composite SVG đã resize lên giữa canvas
  const svgResized = await sharp(svgBuffer, { density: 512 })
    .resize(SVG_RENDER_SIZE, SVG_RENDER_SIZE)
    .png()
    .toBuffer();

  await sharp({
    create: {
      width: MASKABLE_SIZE,
      height: MASKABLE_SIZE,
      channels: 4,
      background: MASKABLE_BG,
    },
  })
    .composite([{ input: svgResized, top: OFFSET, left: OFFSET }])
    .png()
    .toFile(resolve(publicDir, "pwa-maskable-512x512.png"));
  console.log("Đã tạo pwa-maskable-512x512.png (đệm an toàn 10%)");
}

async function generateAppleTouchIcon() {
  // apple-touch-icon 180x180 — nền tối để khớp giao diện tối
  const svgResized = await sharp(svgBuffer, { density: 360 })
    .resize(144, 144) // 80% của 180
    .png()
    .toBuffer();

  await sharp({
    create: {
      width: 180,
      height: 180,
      channels: 4,
      background: MASKABLE_BG,
    },
  })
    .composite([{ input: svgResized, top: 18, left: 18 }])
    .png()
    .toFile(resolve(publicDir, "apple-touch-icon.png"));
  console.log("Đã tạo apple-touch-icon.png (180x180)");
}

async function main() {
  console.log("Bắt đầu tạo biểu tượng PWA từ favicon.svg...");
  await generateStandardIcons();
  await generateMaskableIcon();
  await generateAppleTouchIcon();
  console.log("Hoàn tất tạo biểu tượng PWA.");
}

main().catch((err) => {
  console.error("Lỗi khi tạo biểu tượng PWA:", err);
  process.exit(1);
});
