import assert from 'node:assert/strict';
import test from 'node:test';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import App from '../.test-build/App.js';
import { myAivanEntryUrl } from '../.test-build/lib/myAivan.js';

test('uses the exact configured MyAivan entry and preserves its approved path and port', () => {
  for (const url of ['https://myaivan.example:9100/app', 'https://myaivan.example:8443/team/app', 'http://localhost:8123/app']) {
    assert.equal(myAivanEntryUrl(url), url);
  }
});

test('fails closed for absent, relative, unsafe, or credential-bearing configuration', () => {
  for (const value of [undefined, '', ' ', '/app', '//myaivan.example/app', 'javascript:alert(1)', 'data:text/html,hello', 'ftp://myaivan.example/app', 'https://user:secret@myaivan.example/app', 'https://myaivan.example/app?api_key=secret', 'https://myaivan.example/app#token', 'https://myaivan.example/app', 'http://myaivan.example/app', 'https://myaivan.example:443/app', 'http://myaivan.example:443/app']) {
    assert.equal(myAivanEntryUrl(value), null, String(value));
  }
});

test('unconfigured entry shows an actionable status with no invented destination', () => {
  const html = renderToStaticMarkup(createElement(App));
  assert.match(html, /role="status"/);
  assert.match(html, /MyAivan is not configured/);
  assert.doesNotMatch(html, /href=|Platform loading/);
});

test('entry remains an ordinary repeatable navigation with MyAivan owning login and approval', () => {
  const props = { myAivanUrl: 'https://myaivan.example:9100/app' };
  const first = renderToStaticMarkup(createElement(App, props));
  assert.equal(renderToStaticMarkup(createElement(App, props)), first);
  assert.match(first, /href="https:\/\/myaivan.example:9100\/app"/);
  assert.match(first, /referrerPolicy="no-referrer"/);
  assert.match(first, /Open MyAivan/);
  assert.match(first, /human confirmation/);
  assert.doesNotMatch(first, /iframe|target=|password|api_key|token|tenant_id/);
});
