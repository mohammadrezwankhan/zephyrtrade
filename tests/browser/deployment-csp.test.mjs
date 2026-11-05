import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
import { runtimeSecurity } from '../../scripts/runtime-security.mjs';

test('deployment meta CSP authorizes final script bytes after runtime patches', () => {
  const root = fileURLToPath(new URL('../../', import.meta.url));
  const parent = path.join(root, '.cloudflare');
  fs.mkdirSync(parent, { recursive: true });
  const staging = fs.mkdtempSync(path.join(parent, 'csp-regression-'));
  const output = path.join(staging, 'export');
  try {
    execFileSync(process.execPath, ['scripts/build-cloudflare.mjs'], {
      cwd: root,
      env: { ...process.env, CLOUDFLARE_OUTPUT_ROOT: output },
      stdio: 'pipe',
    });
    const html = fs.readFileSync(path.join(output, 'app/run/index.html'), 'utf8');
    const policy = /<meta\s+http-equiv="Content-Security-Policy"\s+content="([^"]+)"/i.exec(html)?.[1];
    assert.ok(policy, 'deployed runtime keeps its document CSP');
    const scriptSources = policy.split(';').find(directive => directive.trim().startsWith('script-src '));
    assert.ok(scriptSources);
    const security = runtimeSecurity(html);
    const original = runtimeSecurity(fs.readFileSync(path.join(root, 'ZephyrTrade-Champion.html'), 'utf8'));
    assert.notDeepEqual(security.inline_script_hashes, original.inline_script_hashes,
      'the configured browser-only patch changes executable script bytes');
    for (const hash of security.inline_script_hashes) {
      assert.ok(scriptSources.includes(hash), `document CSP must authorize final script ${hash}`);
    }
    assert.ok(!scriptSources.includes("'unsafe-inline'") && !scriptSources.includes("'unsafe-eval'"));
    const receipt = JSON.parse(fs.readFileSync(path.join(output, 'app-security-headers.json'), 'utf8'));
    assert.equal(receipt.document_sha256, security.document_sha256);
    assert.deepEqual(receipt.inline_script_hashes, security.inline_script_hashes);
  } finally {
    fs.rmSync(staging, { recursive: true, force: true });
  }
});
