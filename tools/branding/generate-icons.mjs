import sharp from "sharp";
import { fileURLToPath } from "node:url";

const source = new URL("../../services/web/public/icon.svg", import.meta.url);
for (const [name, size] of [
  ["apple-touch-icon.png", 180],
  ["icon-192.png", 192],
  ["icon-512.png", 512],
]) {
  const output = new URL("../../services/web/public/" + name, import.meta.url);
  await sharp(fileURLToPath(source)).resize(size, size).png().toFile(fileURLToPath(output));
  console.log(name + ": " + size + "x" + size);
}
