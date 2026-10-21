# Optional local assets

The procedural scene needs no models, image textures or HDRI files here.
Font binaries are intentionally not distributed. Provision your own licensed same-origin fonts and configure `src/font-assets.js` to enforce branded typography.
Generated MP4 and poster files are created under `artifacts/` and copied to the built `dist/` root by `npm run stage-media`, after full QA passes.
