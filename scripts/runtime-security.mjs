// Generate CSP from final hosted HTML, after all runtime transforms.
import {createHash} from 'node:crypto';

export function runtimeSecurity(html) {
  const normalized = html.replace(/^\uFEFF/, '').replace(/\r\n?/g, '\n');
  const scripts = [...normalized.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script\s*>/gi)];
  if (scripts.length !== 3 || scripts.some(match => /\bsrc\s*=/i.test(match[1]))) {
    throw Error('Expected exactly three inline runtime scripts and no external script');
  }
  const hashes = scripts.map(match => "'sha256-" + createHash('sha256').update(match[2]).digest('base64') + "'");
  const scriptPolicy = "'self' " + [...new Set(hashes)].join(' ');
  const headers = {
    'Content-Security-Policy': [
      "default-src 'self'", `script-src ${scriptPolicy}`, `script-src-elem ${scriptPolicy}`,
      "style-src 'self' 'unsafe-inline'", "img-src 'self' data: blob:", "font-src 'self'",
      "connect-src 'self'", "worker-src 'self' blob:", "object-src 'none'",
      "base-uri 'self'", "frame-ancestors 'none'", "form-action 'self'",
    ].join('; '),
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains; preload',
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
  };
  return {document_sha256: createHash('sha256').update(html).digest('hex'), inline_script_hashes: hashes, external_script_sources: [], headers};
}

export function runtimeHeaderBlock(html) {
  return '/run/*\n' + Object.entries(runtimeSecurity(html).headers)
    // Shared framing/referrer/permissions headers already apply through /*.
    .filter(([name]) => ['Content-Security-Policy', 'Strict-Transport-Security'].includes(name))
    .map(([name, value]) => `  ${name}: ${value}\n`).join('');
}
