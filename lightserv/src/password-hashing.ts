/**
 * Password hashing using argon2id (modern, memory-hard, recommended by OWASP).
 *
 * Replaces the old SHA-256 approach (hashPassword / verifyPassword).
 *
 * Migration note: existing SHA-256 passwords remain in the DB until the user
 * logs in — at which point they are re-hashed with argon2id (transparent upgrade).
 */

import argon2 from 'argon2';

const ARGO2_COST = 2;
const ARGO2_MEM = 64;
const ARGO2_PAR = 1;

export async function hashPasswordPlain(password: string): Promise<string> {
  return argon2.hash(password, {
    type: argon2.argon2id,
    memoryCost: ARGO2_MEM,
    timeCost: ARGO2_COST,
    parallelism: ARGO2_PAR,
  });
}

export async function verifyPasswordPlain(password: string, hash: string): Promise<boolean> {
  try {
    return await argon2.verify(hash, password);
  } catch {
    return false;
  }
}

/**
 * Check if a hash looks like an argon2 hash (starts with $argon2id$ or $argon2i$).
 */
export function isArgon2Hash(hash: string): boolean {
  return hash.startsWith('$argon2id$') || hash.startsWith('$argon2i$');
}

/**
 * Check if a hash looks like the old SHA-256 format (128 hex chars = 64 salt + 64 hash).
 */
export function isSha256Hash(hash: string): boolean {
  return /^[0-9a-f]{128}$/i.test(hash);
}
