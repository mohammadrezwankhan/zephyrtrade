import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {runtimeSecurity, runtimeHeaderBlock} from './runtime-security.mjs';

test('runtime CSP follows actual inline script bytes and normalizes HTML newlines', () => {
  const html = '<script>first\r\nline</script><script>second</script><script>third</script>';
  const result = runtimeSecurity(html);
  const hash = "'sha256-" + createHash('sha256').update('first\nline').digest('base64') + "'";
  for (const directive of ['script-src', 'script-src-elem']) {
    const policy = result.headers['Content-Security-Policy'].split('; ').find(s => s.startsWith(directive+' '));
    assert.ok(policy.includes(hash));
    assert.ok(!policy.includes('unsafe-inline'));
  }
  assert.notEqual(runtimeSecurity(html.replace('second','changed')).inline_script_hashes[1],result.inline_script_hashes[1]);
  assert.equal(result.document_sha256,createHash('sha256').update(html).digest('hex'));
  assert.match(runtimeHeaderBlock(html), /^\/run\/\*\n/);
});

test('changed runtime architecture and external scripts fail closed', () => {
  assert.throws(()=>runtimeSecurity('<script>one</script>'),/exactly three/);
  assert.throws(()=>runtimeSecurity('<script>one</script><script>two</script><script src="https://example.com/beacon.js"></script>'),/external script/);
});

test('standalone source carries no analytics script', () => {
  runtimeSecurity(fs.readFileSync(new URL('../ZephyrTrade-Champion.html',import.meta.url),'utf8'));
});
