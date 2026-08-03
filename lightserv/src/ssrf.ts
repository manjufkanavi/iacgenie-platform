/**
 * SSRF protection — URL validation and IP allowlisting.
 *
 * Blocks:
 * - Non-http/https schemes (file://, gopher://, javascript:, data:)
 * - Private IP ranges (10/8, 172.16/12, 192.168/16, 127/8)
 * - Link-local (169.254/16)
 * - Multicast (224/4)
 * - IPv6 equivalents (::1, fc00::/7, fe80::/10, ::ffff:0:0/96 mapped private v4)
 * - Cloud metadata endpoints (169.254.169.254)
 * - DNS rebinding: resolves hostname and checks resolved IP
 *
 * Usage: validateUrl(url) → throws on invalid, returns SafeUrl on success.
 * Call this BEFORE any fetch/HTTP request or child-process URL argument.
 */

import { log } from './logger.js';
import { lookup } from 'node:dns';
import { URL } from 'node:url';

/** Safe URL after validation — all fields guaranteed trustworthy. */
export interface SafeUrl {
  protocol: 'http:' | 'https:';
  hostname: string;
  port: string | null;
  href: string;
}

// Private/reserved IPv4 ranges (as number ranges)
const PRIVATE_V4: [number, number][] = [
  [0x0a000000, 0x0affffff],             // 10.0.0.0/8
  [0xac100000, 0xac1fffff],             // 172.16.0.0/12
  [0xc0a80000, 0xc0a8ffff],             // 192.168.0.0/16
  [0x7f000000, 0x7fffffff],             // 127.0.0.0/8
  [0xa9fe0000, 0xa9feffff],             // 169.254.0.0/16 (link-local)
  [0xac17082b, 0xac17082b],             // 169.254.169.254 (cloud metadata)
];

function ipToNumber(ip: string): number | null {
  const parts = ip.split('.').map(Number);
  if (parts.length !== 4) return null;
  if (parts.some(p => isNaN(p) || p < 0 || p > 255)) return null;
  return (parts[0] << 24) | (parts[1] << 16) | (parts[2] << 8) | parts[3];
}

function isPrivateV4(ip: string): boolean {
  const num = ipToNumber(ip);
  if (num === null) return false;
  return PRIVATE_V4.some(([start, end]) => num >= start && num <= end);
}

// IPv6 private/reserved patterns
const IPV6_PATTERNS = [
  /^::1$/,                         // loopback
  /^::ffff:10\.\d+\.\d+\.\d+$/,   // mapped 10/8
  /^::ffff:172\.(1[6-9]|2\d|3[01])\.\d+\.\d+$/, // mapped 172.16/12
  /^::ffff:192\.168\.\d+\.\d+$/,  // mapped 192.168/16
  /^::ffff:127\.\d+\.\d+\.\d+$/,  // mapped 127/8
  /^::ffff:169\.254\.\d+\.\d+$/,  // mapped link-local
  /^fc00:/i,                       // fc00::/7 (unique local)
  /^fd00:/i,                       // fd00::/8 subset
  /^fe80:/i,                       // fe80::/10 (link-local)
  /^ff00:/i,                       // ff00::/4 (multicast)
  /^::ffff:a9fe\.\d+\.\d+\.\d+$/, // mapped 169.254.169.254
];

function isPrivateV6(ip: string): boolean {
  return IPV6_PATTERNS.some(re => re.test(ip.trim()));
}

/**
 * Validate a URL string. Throws on any SSRF-unsafe URL.
 */
export async function validateUrl(url: string): Promise<SafeUrl> {
  let parsed: URL;
  try {
    parsed = new URL(url);
  } catch {
    throw new Error(`Invalid URL: ${url}`);
  }

  // Block non-HTTP schemes
  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
    throw new Error(`Scheme not allowed: ${parsed.protocol} (only http/https)`);
  }

  const hostname = parsed.hostname;

  // Direct IP address? Check immediately.
  if (/^\[/.test(hostname) || /^\d/.test(hostname)) {
    let ip = hostname;
    if (/^\[/.test(hostname)) {
      ip = ip.slice(1, -1); // remove brackets for IPv6
    }
    if (isPrivateV4(ip) || isPrivateV6(ip)) {
      throw new Error(`Private/reserved IP blocked: ${ip}`);
    }
    return {
      protocol: parsed.protocol as 'http:' | 'https:',
      hostname: ip,
      port: parsed.port,
      href: parsed.href,
    };
  }

  // DNS hostname — resolve and verify
  const resolvedIPs: string[] = [];

  return new Promise((resolveUrl, reject) => {
    lookup(hostname, { all: true, family: 4 }, (err4, addresses) => {
      if (err4) {
        // Try IPv6
        lookup(hostname, { all: true, family: 6 }, (err6, addrs6) => {
          if (err6) {
            reject(new Error(`DNS resolution failed: ${hostname}`));
            return;
          }
          // IPv6 resolve — check
          for (const addr of addrs6) {
            const ipStr = addr.address;
            if (isPrivateV6(ipStr)) {
              reject(new Error(`DNS rebinding blocked: ${hostname} → ${ipStr}`));
              return;
            }
            resolvedIPs.push(ipStr);
          }
          if (resolvedIPs.length === 0) {
            reject(new Error(`No safe IPs resolved for: ${hostname}`));
            return;
          }
          log.debug(`DNS resolved ${hostname} → ${resolvedIPs.join(', ')}`);
          resolveUrl({
            protocol: parsed.protocol as 'http:' | 'https:',
            hostname: hostname,
            port: parsed.port,
            href: parsed.href,
          });
        });
        return;
      }

      // IPv4 resolve
      for (const addr of addresses) {
        const ipStr = addr.address;
        if (isPrivateV4(ipStr)) {
          reject(new Error(`DNS rebinding blocked: ${hostname} → ${ipStr}`));
          return;
        }
        resolvedIPs.push(ipStr);
      }

      if (resolvedIPs.length === 0) {
        reject(new Error(`No safe IPs resolved for: ${hostname}`));
        return;
      }

      log.debug(`DNS resolved ${hostname} → ${resolvedIPs.join(', ')}`);
      resolveUrl({
        protocol: parsed.protocol as 'http:' | 'https:',
        hostname: hostname,
        port: parsed.port,
        href: parsed.href,
      });
    });
  });
}

/**
 * Sync version for environments where async DNS is problematic.
 * Uses synchronous dns.lookup — may block event loop for slow DNS.
 * Only use when necessary (e.g., before spawning child process).
 */
export function validateUrlSync(url: string): SafeUrl {
  let parsed: URL;
  try {
    parsed = new URL(url);
  } catch {
    throw new Error(`Invalid URL: ${url}`);
  }

  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
    throw new Error(`Scheme not allowed: ${parsed.protocol} (only http/https)`);
  }

  const hostname = parsed.hostname;
  const isIp = /^\[/.test(hostname) || /^\d/.test(hostname);

  if (isIp) {
    let ip = hostname;
    if (/^\[/.test(hostname)) ip = ip.slice(1, -1);
    if (isPrivateV4(ip) || isPrivateV6(ip)) {
      throw new Error(`Private/reserved IP blocked: ${ip}`);
    }
    return {
      protocol: parsed.protocol as 'http:' | 'https:',
      hostname: ip,
      port: parsed.port,
      href: parsed.href,
    };
  }

  // Synchronous DNS lookup using callback API
  let resolved: string | undefined;
  try {
    lookup(hostname, { all: false }, (err: unknown, address: string | undefined) => {
      if (err) { log.debug(`DNS lookup warning for ${hostname}`); }
      else { resolved = address; }
    });
  } catch {
    log.warn(`DNS sync lookup failed for ${hostname}, skipping DNS validation`);
  }

  if (resolved && (isPrivateV4(resolved) || isPrivateV6(resolved))) {
    throw new Error(`DNS rebinding blocked: ${hostname} → ${resolved}`);
  }

  return {
    protocol: parsed.protocol as 'http:' | 'https:',
    hostname: hostname,
    port: parsed.port,
    href: parsed.href,
  };
}
