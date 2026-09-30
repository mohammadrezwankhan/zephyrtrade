# Cloudflare browser edition

Public overview: <https://mktrade.co.business/>
Public application: <https://mktrade.co.business/run/>

The dedicated Cloudflare Pages project is `mktrade-zephyr` on the **Free** plan. `www.mktrade.co.business` redirects permanently to the apex while preserving paths and query strings.

Build the complete dedicated site with Node.js 24:

```sh
node scripts/build-domain.mjs
node scripts/check-domain.mjs
```

Upload the entire `.cloudflare/site` directory to `mktrade-zephyr`. `cloudflare-domain.json` defines its canonical address and project. The site includes an overview, methodology and About page, the browser runtime, a three-page sitemap, robots directives, structured data and matching app facts. Synthetic runtime screens and Pages aliases use noindex. No paid Worker, database, storage or provider integration is required.

The GitHub repository's visibility is independent of the public browser demo. Only the explicit browser export and public introduction are uploaded. No Git history, environment files, databases, server data, promotion drafts or private source tree is copied.

## Build and run

Use Node.js 24 and run from the repository root:

```sh
node scripts/build-cloudflare.mjs
node scripts/build-cloudflare.mjs --serve
```

The second command opens a loopback-only preview at `http://127.0.0.1:4179/`. Set `PORT` to change it. The deployable app directory is `.cloudflare/app`. The first command performs any required browser-export preparation automatically.

## Deployment contract

The app is mounted at `/apps/zephyrtrade/` in the dedicated Cloudflare Pages project `mklab-apps` on `mklab.co.technology`. **Do not upload this one app directory over the project's root:** a Pages deployment replaces the whole site. Run the Champion `_astra-control/mklab-migration/build-collection.mjs` builder to assemble all 37 apps, then upload its complete `dist` output. `khanlab.co.technology` and its `datacenter-twin-lab` project are reserved for Datacenter Twin Lab. Old `/apps/` URLs redirect to MKLab. Browser storage is scoped to each origin and is not transferred between domains.

The collection export remains available through `build-cloudflare.mjs`; the dedicated-domain builder leaves that output separate and writes `.cloudflare/site`. Do not upload either single-app output over the MKLab collection. Review `cloudflare-domain.json` before publishing another dedicated host. Domain aliases use Cloudflare zone Redirect Rules, because Pages `_redirects` handles path redirects.

## Search and AI-readable information

The introduction is complete HTML without JavaScript. It includes factual descriptions, usage steps, limitations, visible FAQs, canonical and sharing metadata, and matching `SoftwareApplication`, `WebPage` and breadcrumb structured data. `app.json` and `llms.txt` are optional plain public references. These files do not guarantee indexing, ranking or AI citations. Fictional runtime screens use `noindex,follow`; search engines can index the factual introduction.

The collection maintains the root sitemap and robots file. Canonical links identify the custom domain; the production pages.dev alias and preview URLs use noindex headers to avoid duplicate search results. No tracking, external AI calls or submission service is added.

## Browser scope

- The bundled snapshot is historical and synthetic; it does not show live prices or current forecasts.
- There are no real orders, brokers, accounts, or trading connections.
- The optional Python service is a local cross-check, not an automatic model retraining service or public backend.

The source runtime and numerical models retain their existing boundaries. Hosting a browser demo does not provide a Python/Node server, professional validation, live provider connections or production approval.

## Reproducibility

`cloudflare.json` contains the reviewed public facts and explicit input paths. The builder emits source revision and the final runtime SHA-256 in `app.json`, copies only allowlisted assets, rejects input symlinks and includes available notices. Its output is ignored by Git. Public text was prepared on 2026-09-30.

References: [Cloudflare direct upload](https://developers.cloudflare.com/pages/get-started/direct-upload/), [Google AI search guidance](https://developers.google.com/search/docs/appearance/ai-features), [structured-data policies](https://developers.google.com/search/docs/appearance/structured-data/sd-policies).
