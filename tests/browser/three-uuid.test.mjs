import assert from 'node:assert/strict';
import test from 'node:test';
import { MathUtils } from '../../assets/engineering-hero/v1/vendor/three/build/three.core.js';

const layouts = [
  {
    name: 'zero entropy bits',
    bytes: new Uint8Array(16),
    expected: '00000000-0000-4000-8000-000000000000',
  },
  {
    name: 'all entropy bits set',
    bytes: new Uint8Array(16).fill(255),
    expected: 'ffffffff-ffff-4fff-bfff-ffffffffffff',
  },
  {
    name: 'distinct bytes in every position',
    bytes: Uint8Array.from({ length: 16 }, (_, index) => index),
    expected: '00010203-0405-4607-8809-0a0b0c0d0e0f',
  },
];

for (const { name, bytes, expected } of layouts) {
  test(`Three UUID preserves its version, variant and byte layout for ${name}`, (t) => {
    t.mock.method(Math, 'random', () => {
      throw new Error('UUID generation must not use Math.random');
    });
    t.mock.method(globalThis.crypto, 'getRandomValues', (view) => {
      assert.ok(ArrayBuffer.isView(view));
      assert.equal(view.byteLength, 16);
      new Uint8Array(view.buffer, view.byteOffset, view.byteLength).set(bytes);
      return view;
    });

    assert.equal(MathUtils.generateUUID(), expected);
  });
}

test('Three UUID works with real WebCrypto without calling Math.random', (t) => {
  t.mock.method(Math, 'random', () => {
    throw new Error('UUID generation must not use Math.random');
  });

  assert.match(
    MathUtils.generateUUID(),
    /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
  );
});

test('Three UUID propagates entropy failure without an insecure fallback', (t) => {
  const failure = new Error('Secure entropy unavailable');
  let fallbackCalls = 0;
  t.mock.method(globalThis.crypto, 'getRandomValues', () => {
    throw failure;
  });
  t.mock.method(Math, 'random', () => {
    fallbackCalls += 1;
    return 0.5;
  });

  assert.throws(() => MathUtils.generateUUID(), (error) => error === failure);
  assert.equal(fallbackCalls, 0);
});

test('Three UUID fails when WebCrypto is missing without an insecure fallback', (t) => {
  const descriptor = Object.getOwnPropertyDescriptor(globalThis, 'crypto');
  assert.ok(descriptor);
  let fallbackCalls = 0;
  t.mock.method(Math, 'random', () => {
    fallbackCalls += 1;
    return 0.5;
  });

  try {
    Object.defineProperty(globalThis, 'crypto', { value: undefined, configurable: true });
    assert.throws(() => MathUtils.generateUUID());
    assert.equal(fallbackCalls, 0);
  } finally {
    Object.defineProperty(globalThis, 'crypto', descriptor);
  }
});
