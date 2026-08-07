/**
 * OpenBao / HashiCorp Vault Client
 *
 * A secure client for interacting with OpenBao (or HashiCorp Vault) using
 * token-based authentication.
 *
 * All KV-v2 paths follow the pattern:
 *   - Read/Write: /v1/{mount}/data/{secret_path}
 *   - List:       /v1/{mount}/metadata/{secret_path}/
 */

export class OpenBaoConnectionError extends Error {
  constructor(
    public readonly url: string,
    message: string
  ) {
    super(`OpenBaoConnectionError [${url}]: ${message}`);
    this.name = 'OpenBaoConnectionError';
  }
}

export class SecretNotFoundError extends Error {
  constructor(public readonly path: string) {
    super(`SecretNotFoundError: Secret at path '${path}' not found.`);
    this.name = 'SecretNotFoundError';
  }
}

export interface OpenBaoClientOptions {
  token?: string;
  addr?: string;
  mountPath?: string;
}

/**
 * Secret Store Client for secure API interactions with OpenBao or HashiCorp Vault.
 * Supports:
 * - Token-based authentication
 * - Secret CRUD operations via KV-v2 engine
 */
export class OpenBaoClient {
  private token: string;
  private addr: string;
  private mountPath: string;

  /**
   * Initialize the OpenBao client.
   * If options are not provided, it falls back to OPENBAO_TOKEN, OPENBAO_ADDR,
   * and OPENBAO_MOUNT_PATH (default: iacgenie/kv) environment variables.
   */
  constructor(options?: OpenBaoClientOptions) {
    this.token = options?.token ?? process.env.OPENBAO_TOKEN ?? '';
    this.addr = options?.addr ?? process.env.OPENBAO_ADDR ?? '';
    this.mountPath = options?.mountPath ?? process.env.OPENBAO_MOUNT_PATH ?? 'iacgenie/kv';

    // Remove trailing slashes
    this.addr = this.addr.replace(/\/+$/, '');
    this.mountPath = this.mountPath.replace(/^\/+|\/+$/g, '');
  }

  /**
   * Check if the client has minimal configuration (addr and token).
   */
  public isConfigured(): boolean {
    return Boolean(this.addr && this.token);
  }

  /**
   * Helper to execute fetch with retry logic and exponential backoff.
   */
  private async fetchWithRetry(
    url: string,
    options: RequestInit,
    retries = 3,
    backoff = 500
  ): Promise<Response> {
    try {
      const response = await fetch(url, options);

      // Retry on 429 and 50x errors
      const retryStatusCodes = [429, 500, 502, 503, 504];
      if (retryStatusCodes.includes(response.status) && retries > 0) {
        await new Promise((resolve) => setTimeout(resolve, backoff));
        return this.fetchWithRetry(url, options, retries - 1, backoff * 2);
      }

      return response;
    } catch (error) {
      if (retries > 0) {
        await new Promise((resolve) => setTimeout(resolve, backoff));
        return this.fetchWithRetry(url, options, retries - 1, backoff * 2);
      }
      throw new OpenBaoConnectionError(url, error instanceof Error ? error.message : String(error));
    }
  }

  private buildUrl(path: string): string {
    return `${this.addr}/v1/${path}`;
  }

  private kvDataPath(secretPath: string): string {
    const cleanPath = secretPath.replace(/^\/+/, '');
    return `${this.mountPath}/data/${cleanPath}`;
  }

  private kvMetadataPath(secretPath: string): string {
    const cleanPath = secretPath.replace(/^\/+/, '');
    return `${this.mountPath}/metadata/${cleanPath}`;
  }

  private getHeaders(): HeadersInit {
    return {
      'X-Vault-Token': this.token,
      'Content-Type': 'application/json',
    };
  }

  /**
   * Read a secret from the KV-v2 secret store.
   * @param path The logical secret path
   * @returns The secret data dict
   * @throws SecretNotFoundError if the secret doesn't exist
   * @throws OpenBaoConnectionError if the connection fails
   */
  public async readSecret(path: string): Promise<Record<string, any>> {
    if (!this.isConfigured()) return {};

    const url = this.buildUrl(this.kvDataPath(path));
    
    const response = await this.fetchWithRetry(url, {
      method: 'GET',
      headers: this.getHeaders(),
    });

    if (response.status === 404) {
      throw new SecretNotFoundError(path);
    }

    if (!response.ok) {
      throw new OpenBaoConnectionError(url, `HTTP ${response.status}: ${await response.text()}`);
    }

    const json = await response.json();
    return json?.data?.data || {};
  }

  /**
   * Write a secret to the KV-v2 secret store.
   * @param path The logical secret path
   * @param data The secret data to write
   * @returns The response from the secret store
   */
  public async writeSecret(path: string, data: Record<string, any>): Promise<Record<string, any>> {
    if (!this.isConfigured()) return {};

    const url = this.buildUrl(this.kvDataPath(path));
    
    const response = await this.fetchWithRetry(url, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({ data }),
    });

    if (!response.ok) {
      throw new OpenBaoConnectionError(url, `HTTP ${response.status}: ${await response.text()}`);
    }

    return response.json();
  }

  /**
   * List secret keys at a given path using the KV-v2 LIST method.
   * @param path The logical path prefix
   * @returns A list of key names at the given path
   */
  public async listSecrets(path: string): Promise<string[]> {
    if (!this.isConfigured()) return [];

    const url = this.buildUrl(this.kvMetadataPath(path));
    
    // LIST method is natively supported by fetch using a custom method string
    const response = await this.fetchWithRetry(url, {
      method: 'LIST',
      headers: this.getHeaders(),
    });

    if (response.status === 404) {
      return [];
    }

    if (!response.ok) {
      throw new OpenBaoConnectionError(url, `HTTP ${response.status}: ${await response.text()}`);
    }

    const json = await response.json();
    return json?.data?.keys || [];
  }

  /**
   * Check the health status of the OpenBao cluster.
   */
  public async healthCheck(): Promise<boolean> {
    if (!this.isConfigured()) return false;

    const url = this.buildUrl('sys/health');
    try {
      const response = await this.fetchWithRetry(url, {
        method: 'GET',
        // Health check usually doesn't require a token, but passing it doesn't hurt
        headers: this.getHeaders(),
      });
      // 200 = initialized, unsealed, and active
      // 429 = unsealed and standby
      // 472 = disaster recovery mode replication secondary and active
      // 473 = performance standby
      return response.ok || [429, 472, 473].includes(response.status);
    } catch {
      return false;
    }
  }
}
