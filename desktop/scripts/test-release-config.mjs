import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = fileURLToPath(new URL(".", import.meta.url));
const manifest = readFileSync(join(scriptDir, "../src-tauri/Cargo.toml"), "utf8");
const features = manifest.split(/^\[features\]\s*$/m)[1]?.split(/^\[/m)[0] ?? "";
const defaults = features.match(/^default\s*=\s*\[([^\]]*)\]/m)?.[1] ?? "";

assert.match(defaults, /"custom-protocol"/, "release builds must load packaged frontend assets by default");
assert.match(features, /^custom-protocol\s*=\s*\[\s*"tauri\/custom-protocol"\s*\]/m);
console.log("Release config test passed: the app enables Tauri's packaged custom protocol by default.");
