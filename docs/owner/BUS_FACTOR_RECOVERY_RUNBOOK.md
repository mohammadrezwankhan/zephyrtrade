# Recovery runbook

Recovery has three different subjects: source and research inputs, browser scenario assumptions, and published static artifacts. Restore each using its own identity. Do not equate a recovered HTML file with recovered training data or a user's browser notebook.

## 1. Recover a verifiable source checkout

Obtain the repository through the established GitHub access path and record the commit/tree. For this documentation snapshot the source is `29abf5d8bd6f05b1f0c027d8753f4837840215dc`, tree `83a0b69f4e8eabe81c103d0923910f17cb48b98d`. Confirm license, CFF, security policy, dependency manifests, source/test code and expected retained data. A working-directory copy without a matching complete tree is not a proved restoration.

```sh
git clone https://github.com/mohammadrezwankhan/zephyrtrade.git zephyr-recovery
cd zephyr-recovery
git checkout --detach 29abf5d8bd6f05b1f0c027d8753f4837840215dc
git status --short
git rev-parse HEAD HEAD^{tree}
```

These are recovery instructions, not a new remote mutation or an execution claim. If this historic commit is unavailable, retain the observed failure and recover an authorized verified archive rather than assigning its identity to different bytes.

## 2. Recover research reproducibility

Follow [setup](../developer/SETUP_AND_REPRODUCIBILITY.md) in a new environment and a new output directory. The tree includes retained Phase 2/Phase 3 prediction CSVs, provenance and farm metadata; original full raw/processed tables and trained estimators are not all retained. `scripts/build_app.make_snapshot()` can reconcile the saved test data without training. A new bounded smoke produces new raw/processed/results and must not overwrite the archive. [scripts/build_app.py:87–211](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/scripts/build_app.py#L87-L211) [scripts/smoke_research.py:18–75](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/scripts/smoke_research.py#L18-L75)

For a full rerun, retain the synthetic configuration, seed, exact package/interpreter versions, timezone, input/output hashes and explicit Phase 2/3 settings. `run_manifest.json` records four selected summary/provenance hashes and paths, not every output. A regenerated scaler is not a recovered trained-forecast model. Do not load untrusted joblib/pickle objects; rebuild trusted preprocessing from declared inputs instead. [src/zephyrtrade/pipeline.py:91–172](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/pipeline.py#L91-L172) [src/zephyrtrade/preprocessing.py:264–335](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/preprocessing.py#L264-L335)

Check the independent analytical fixtures and parity criteria before comparing historical economic metrics. Byte differences can arise from compression metadata or numerical libraries; report both byte identity and numerical comparison tolerances. Never relabel a new seed/environment result as the original archive.

## 3. Recover scenario assumptions

Export schema 1 JSON from the original browser origin before clearing storage, changing host or upgrading a browser profile. Saved assumptions use `zephyr-scenarios-v1`; view preferences and theme use different keys. The application has no cloud synchronization or multiuser backup service. Import into the intended current app and verify the inputs, duration and recalculated result. The imported `calculated` section is not trusted. [src/zephyrtrade/web/app.js:514–524](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/web/app.js#L514-L524) [src/zephyrtrade/web/app.js:537–546](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/web/app.js#L537-L546) [src/zephyrtrade/web/app.js:580–611](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/web/app.js#L580-L611)

The UI holds up to 20 saved scenarios. If a storage write fails, it should retain prior committed state; use JSON export as the fallback. Keep a previous export before deleting a scenario or changing its assumptions. A cleared browser origin without exported files may have no recovery path. Do not promise restoration of unsaved in-memory drafts.

## 4. Recover the local service

Run `zephyr-app --no-browser` in the clean environment. If port 8765 is occupied, use another allowed port such as 8766. Verify `/api/health` and a fictional fixture; keep the service on loopback. There is no broker credential, production database or remote forecasting process to restore for this native service. The app's Host/Origin checks and bounded concurrency do not authenticate people. [src/zephyrtrade/app.py:102–137](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/app.py#L102-L137) [src/zephyrtrade/app.py:317–349](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/src/zephyrtrade/app.py#L317-L349)

## 5. Recover documentation/publication

The canonical Markdown and `docs/reference/chapters.json` rebuild the handbook with its isolated renderer. Preserve the source Markdown, original figures and CSP; regenerate HTML and check freshness. The established Pages workflow uploads `docs`. Dedicated/collection browser builds are separate artifacts with declared canonical routes and runtime hash metadata. Use the [release playbook](../maintainer/CI_CD_AND_RELEASE_PLAYBOOK.md) to relate source, build and deployment instead of assuming the repository's latest commit is live. [.github/workflows/deploy-dashboard.yml](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/.github/workflows/deploy-dashboard.yml) [cloudflare.json](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/cloudflare.json) [cloudflare-domain.json](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/cloudflare-domain.json)

The existing traceability workflow uses `MKLAB_REGISTRY_SSH_KEY` only in eligible non-PR source-observation work and the `MKLAB_TRACEABILITY_ACTIVE` variable to enable that bridge. Secret values must be recovered through the authorized owner/provider channel, never documentation, chat or public issue logs. The ordinary local scientific app needs no API credential. Changing a registry observation is not deployment of the app. [.github/workflows/mklab-traceability-sync.yml:38–70](https://github.com/mohammadrezwankhan/zephyrtrade/blob/29abf5d8bd6f05b1f0c027d8753f4837840215dc/.github/workflows/mklab-traceability-sync.yml#L38-L70)

## Recovery acceptance record

Record recovered source/tree, archive and dependency identities; restoration commands and failures; passed numerical/HTTP fixtures; browser export/import and native-origin acceptance where a browser can actually run; and published artifact/deployment/content evidence. Keep unavailable evidence visible. The 2026-11-19 worker's Chromium launch was blocked, so a future recovery drill must obtain that browser evidence on a capable environment rather than cite this run as proof.
