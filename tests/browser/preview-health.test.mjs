import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { test } from 'node:test';

test('standalone preview identifies itself without advertising Python', async (t) => {
  const server = spawn(process.execPath, ['scripts/preview-demo.mjs'], {
    env: { ...process.env, PORT: '0' },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  t.after(() => server.kill());
  const [chunk] = await once(server.stdout, 'data');
  const address = String(chunk).match(/http:\/\/127\.0\.0\.1:\d+/)?.[0];
  assert.ok(address, 'preview must report its loopback address');
  const health = await fetch(`${address}/api/health`);
  assert.equal(health.status, 200);
  assert.deepEqual(await health.json(), { service: 'zephyrtrade-preview' });
  assert.equal((await fetch(`${address}/api/health`, { method: 'HEAD' })).status, 200);
  assert.equal((await fetch(`${address}/api/optimize`)).status, 404);
  assert.equal((await fetch(`${address}/api/health`, { method: 'POST' })).status, 405);
});
