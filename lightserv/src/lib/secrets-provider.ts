import { log } from '../logger.js';
import { OpenBaoClient, SecretNotFoundError } from './openbao-client.js';

export interface PostgresConfig {
  host?: string;
  port?: number;
  username?: string;
  password?: string;
}

export interface RedisConfig {
  host?: string;
  port?: number;
  password?: string;
  url?: string;
}

export interface MinioConfig {
  endpoint?: string;
  accessKey?: string;
  secretKey?: string;
}

export interface SearxngConfig {
  secret?: string;
  port?: number;
}

export interface ApiConfig {
  apiSecret?: string;
  apiUrl?: string;
}

export interface SmtpConfig {
  apiKey?: string;
  server?: string;
  port?: number;
  fromAddress?: string;
}

export interface KeycloakConfig {
  url?: string;
  realm?: string;
  clientId?: string;
  clientSecret?: string;
  adminUser?: string;
  adminPassword?: string;
  dbPassword?: string;
}

/**
 * A high-level secrets provider that wraps the OpenBao client.
 */
class SecretsProvider {
  private client: OpenBaoClient;
  private cache: Map<string, any> = new Map();
  private lastFetchTime: number = 0;
  private ttlMs: number;
  private initialized: boolean = false;

  constructor(ttlMinutes = 5) {
    this.client = new OpenBaoClient();
    this.ttlMs = ttlMinutes * 60 * 1000;
  }

  /**
   * Initialize on first call (lazy singleton pattern).
   * Fetches all required secrets from OpenBao on init.
   */
  public async initialize(): Promise<void> {
    if (this.initialized && (Date.now() - this.lastFetchTime) < this.ttlMs) {
      return;
    }

    if (!this.client.isConfigured()) {
      log.warn('OpenBao is not configured. Falling back to environment variables for secrets.');
      this.initialized = true;
      return;
    }

    try {
      log.info('Fetching secrets from OpenBao...');
      
      const paths = [
        'lightserp/kv/data/postgres',
        'lightserp/kv/data/redis',
        'lightserp/kv/data/minio',
        'lightserp/kv/data/searxng',
        'lightserp/kv/data/api',
        'lightserp/kv/data/keycloak',
        'lightserp/kv/data/smtp',
        'lightserp/kv/data/jwt'
      ];

      for (const path of paths) {
        try {
          // Adjust path because OpenBaoClient auto-adds /data/ suffix
          // so if the raw KV v2 path is lightserp/kv/data/postgres
          // and mount is lightserp/kv, the readSecret arg is just 'postgres'
          // We assume OPENBAO_MOUNT_PATH="lightserp/kv" or similar
          // The requirements provided full KV paths. Let's just extract the secret name.
          const secretName = path.split('/').pop() || path;
          
          const data = await this.client.readSecret(secretName);
          this.cache.set(secretName, data);
        } catch (err) {
          if (err instanceof SecretNotFoundError) {
            log.warn(`Secret not found in OpenBao for path: ${path}`);
          } else {
            log.error(`Error fetching secret ${path} from OpenBao:`, err);
          }
        }
      }

      this.lastFetchTime = Date.now();
      this.initialized = true;
      log.info('Successfully fetched and cached secrets from OpenBao.');
    } catch (error) {
      log.error('Failed to initialize SecretsProvider from OpenBao:', error);
      // Fallback to env vars will happen naturally when the cache is empty
      this.initialized = true;
    }
  }

  /**
   * Ensure provider is initialized before fetching.
   */
  private async ensureInitialized(): Promise<void> {
    if (!this.initialized || (Date.now() - this.lastFetchTime) >= this.ttlMs) {
      await this.initialize();
    }
  }

  public async getPostgresConfig(): Promise<PostgresConfig> {
    await this.ensureInitialized();
    const data = this.cache.get('postgres') || {};
    return {
      host: data.host || process.env.POSTGRES_HOST,
      port: data.port ? parseInt(data.port, 10) : process.env.POSTGRES_PORT ? parseInt(process.env.POSTGRES_PORT, 10) : undefined,
      username: data.username || process.env.POSTGRES_USER,
      password: data.password || process.env.POSTGRES_PASSWORD,
    };
  }

  public async getRedisConfig(): Promise<RedisConfig> {
    await this.ensureInitialized();
    const data = this.cache.get('redis') || {};
    return {
      host: data.host || process.env.REDIS_HOST,
      port: data.port ? parseInt(data.port, 10) : process.env.REDIS_PORT ? parseInt(process.env.REDIS_PORT, 10) : undefined,
      password: data.password || process.env.REDIS_PASSWORD,
      url: data.url || process.env.REDIS_URL,
    };
  }

  public async getMinioConfig(): Promise<MinioConfig> {
    await this.ensureInitialized();
    const data = this.cache.get('minio') || {};
    return {
      endpoint: data.endpoint || process.env.MINIO_ENDPOINT,
      accessKey: data.access_key || process.env.MINIO_ACCESS_KEY,
      secretKey: data.secret_key || process.env.MINIO_SECRET_KEY,
    };
  }

  public async getSearxngConfig(): Promise<SearxngConfig> {
    await this.ensureInitialized();
    const data = this.cache.get('searxng') || {};
    return {
      secret: data.secret || process.env.SEARXNG_SECRET,
      port: data.port ? parseInt(data.port, 10) : process.env.SEARXNG_PORT ? parseInt(process.env.SEARXNG_PORT, 10) : undefined,
    };
  }

  public async getApiConfig(): Promise<ApiConfig> {
    await this.ensureInitialized();
    const data = this.cache.get('api') || {};
    return {
      apiSecret: data.api_secret || process.env.API_SECRET,
      apiUrl: data.api_url || process.env.API_URL,
    };
  }

  public async getSmtpConfig(): Promise<SmtpConfig> {
    await this.ensureInitialized();
    const data = this.cache.get('smtp') || {};
    return {
      apiKey: data.api_key || process.env.SMTP_API_KEY,
      server: data.server || process.env.SMTP_SERVER,
      port: data.port ? parseInt(data.port, 10) : process.env.SMTP_PORT ? parseInt(process.env.SMTP_PORT, 10) : undefined,
      fromAddress: data.from_address || process.env.SMTP_FROM_ADDRESS,
    };
  }

  public async getJwtSecret(): Promise<string | undefined> {
    await this.ensureInitialized();
    const data = this.cache.get('jwt') || {};
    return data.secret || process.env.JWT_SECRET;
  }

  public async getKeycloakConfig(): Promise<KeycloakConfig> {
    await this.ensureInitialized();
    const data = this.cache.get('keycloak') || {};
    return {
      url: data.url || process.env.KEYCLOAK_URL,
      realm: data.realm || process.env.KEYCLOAK_REALM,
      clientId: data.client_id || process.env.KEYCLOAK_CLIENT_ID,
      clientSecret: data.client_secret || process.env.KEYCLOAK_CLIENT_SECRET,
      adminUser: data.admin_user || process.env.KEYCLOAK_ADMIN,
      adminPassword: data.admin_password || process.env.KEYCLOAK_ADMIN_PASSWORD,
      dbPassword: data.db_password || process.env.KEYCLOAK_DB_PASSWORD,
    };
  }
}

export const secrets = new SecretsProvider();
