import test from 'node:test';
import assert from 'node:assert/strict';
import {extractStaticPageText, hasAnchorUnder} from '../../scripts/html-document.mjs';

const source='https://example.test/';
/** @param {string} body */
const document=body=>`<!doctype html><html><head><title>Wind &amp; power</title></head><body>${body}</body></html>`;

test('visible text respects browser HTML parsing and preserves complete anchor destinations',()=>{
  const html=document('<main id="main"><p>Power <strong>offer</strong> &amp; risk</p><a href="/guide?x=1&amp;y=2">Read <em>guide</em></a></main ignored>');
  assert.equal(extractStaticPageText(html,source),'### Wind & power\nSource: https://example.test/\n\nPower offer & risk\nRead guide (/guide?x=1&y=2)');
});

test('comment markup cannot replace the document main or title',()=>{
  const html='<!--<title>Fake</title><main id="main">Fake</main>-->'+document('<main id="main"><p>Actual text</p></main>');
  assert.equal(extractStaticPageText(html,source),'### Wind & power\nSource: https://example.test/\n\nActual text');
});

test('script, style and inert template contents are absent from visible page text',()=>{
  const html=document('<main id="main"><p>Visible</p><script>window.hidden=true</script><style>body{color:red}</style><template>Hidden template</template><p>End</p></main>');
  assert.equal(extractStaticPageText(html,source),'### Wind & power\nSource: https://example.test/\n\nVisible\nEnd');
});

test('encoded tag text remains text in the plain-text export',()=>{
  const html=document('<main id="main"><p>&lt;script&gt; is text &amp; stays visible</p></main>');
  const expected='### Wind & power\nSource: https://example.test/\n\n<script> is text & stays visible';
  const exported=extractStaticPageText(html,source);
  // Static node:assert equality compares plain text; neither argument is rendered.
  // nosemgrep: javascript.lang.security.audit.unknown-value-with-script-tag.unknown-value-with-script-tag
  assert.equal(exported,expected);
});

test('noscript fallback is absent when document scripting is enabled',()=>{
  const html=document('<main id="main"><p>Visible</p><noscript><p>Hidden fallback</p></noscript><p>End</p></main>');
  assert.equal(extractStaticPageText(html,source),'### Wind & power\nSource: https://example.test/\n\nVisible\nEnd');
});

test('a foreign SVG title cannot supply a missing HTML document title',()=>{
  assert.throws(()=>extractStaticPageText('<svg><title>Chart</title></svg><main id="main">Data</main>',source),/title/);
});

test('ambiguous main elements are rejected',()=>{
  assert.throws(()=>extractStaticPageText(document('<main id="main">One</main><main id="main">Two</main>'),source),/main/);
});

test('link directory checks compare parsed origin and path boundaries',()=>{
  const root='https://khanlab.co.technology/apps/';
  assert.equal(hasAnchorUnder('<a href="https://khanlab.co.technology/apps/zephyr/">App</a>',root,source),true);
  assert.equal(hasAnchorUnder('<a href="/apps/zephyr/">App</a>',root,root),true);
  for(const href of [
    'https://evil.test/?next=https://khanlab.co.technology/apps/',
    'https://khanlab.co.technology@evil.test/apps/',
    'https://khanlab.co.technology.evil.test/apps/',
    'https://khanlab.co.technology/apps-other/',
    'https://khanlab.co.technology/apps/../elsewhere/',
  ])assert.equal(hasAnchorUnder(`<a href="${href}">App</a>`,root,source),false,href);
});

test('comment and script text do not become document anchors',()=>{
  const root='https://khanlab.co.technology/apps/';
  const html=`<!--<a href="${root}">Fake</a>--><script>const text='<a href="${root}">Fake</a>';</script>`;
  assert.equal(hasAnchorUnder(html,root,source),false);
});

test('SVG anchor destinations include modern href and legacy xlink href',()=>{
  const root='https://khanlab.co.technology/apps/';
  assert.equal(hasAnchorUnder('<svg><a href="https://khanlab.co.technology/apps/old/">Old</a></svg>',root,source),true);
  assert.equal(hasAnchorUnder('<svg><a xlink:href="https://khanlab.co.technology/apps/old/">Old</a></svg>',root,source),true);
  assert.equal(hasAnchorUnder('<svg><a xlink:href="https://khanlab.co.technology/apps/old/" href="https://example.test/current/">Current</a></svg>',root,source),false);
  assert.equal(hasAnchorUnder('<svg><a href="https://khanlab.co.technology/apps/old/" xlink:href="https://example.test/current/">Old</a></svg>',root,source),true);
});
