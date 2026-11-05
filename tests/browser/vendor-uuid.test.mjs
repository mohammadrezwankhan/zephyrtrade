import assert from 'node:assert/strict';
import test from 'node:test';
import { MathUtils, Object3D } from '../../assets/engineering-hero/v1/vendor/three/build/three.core.js';

test('scene UUIDs stay distinct when Math.random is predictable', (t) => {
  t.mock.method(Math, 'random', () => 0);
  const identifiers = Array.from({ length: 32 }, () => new Object3D().uuid);

  assert.equal(new Set(identifiers).size, identifiers.length);
  for (const identifier of identifiers) {
    assert.match(identifier, /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
  }
});

test('UUID formatting preserves secure entropy and version and variant bits', (t) => {
  t.mock.method(globalThis.crypto, 'getRandomValues', (words) => {
    words.set([0x33221100, 0x77665544, 0xbbaa9988, 0xffeeddcc]);
    return words;
  });
  t.mock.method(Math, 'random', () => 0);

  assert.equal(MathUtils.generateUUID(), '00112233-4455-4677-8899-aabbccddeeff');
});

test('UUID generation propagates entropy failures without an insecure fallback', (t) => {
  const unavailable = new Error('Secure entropy is unavailable');
  t.mock.method(globalThis.crypto, 'getRandomValues', () => {
    throw unavailable;
  });

  assert.throws(() => MathUtils.generateUUID(), unavailable);
});
