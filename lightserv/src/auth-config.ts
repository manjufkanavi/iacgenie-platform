/**
 * Authentication configuration — centralized env vars.
 *
 * SECURITY: No default fallbacks for sensitive values.
 * If JWT_SECRET is missing, the feature fails gracefully.
 */

export const config = {
  JWT_SECRET: process.env.JWT_SECRET,
  KEYCLOAK_URL: process.env.KEYCLOAK_URL ?? 'http://iacgenie-keycloak:8080',
  KEYCLOAK_REALM: process.env.KEYCLOAK_REALM ?? 'lightserp',
  KEYCLOAK_CLIENT_ID: process.env.KEYCLOAK_CLIENT_ID ?? 'lightserp-api',
  KEYCLOAK_CLIENT_SECRET: process.env.KEYCLOAK_CLIENT_SECRET ?? '',
  KEYCLOAK_ADMIN_USER: process.env.KEYCLOAK_ADMIN_USER ?? '',
  KEYCLOAK_ADMIN_PASSWORD: process.env.KEYCLOAK_ADMIN_PASSWORD ?? '',
  LIGHTSERP_URL: process.env.LIGHTSERP_URL ?? 'http://localhost:3071',
  CORS_ORIGIN: process.env.CORS_ORIGIN ?? '',
  KC_TIMEOUT: 5000,
  MIN_PASSWORD_LENGTH: 8,
  VERIFICATION_TOKEN_EXPIRY: 24 * 60 * 60,
  SMTP2GO_API_KEY: process.env.SMTP2GO_API_KEY ?? '',
  EMAIL_FROM: process.env.EMAIL_FROM_ADDRESS ?? 'noreply@lightserp.ai',
  SMTP_SERVER: process.env.SMTP_SERVER ?? 'mail.smtp2go.com',
  SMTP_PORT: parseInt(process.env.SMTP_PORT ?? '2525', 10),
  EMAIL_TIMEOUT: parseInt(process.env.EMAIL_TIMEOUT ?? '10000', 10),
};

export function isJwtConfigured(): boolean {
  return config.JWT_SECRET !== undefined && config.JWT_SECRET.length > 0;
}

export function isKeycloakConfigured(): boolean {
  const hasClientSecret = config.KEYCLOAK_CLIENT_SECRET.length > 0;
  const hasAdminCreds = config.KEYCLOAK_ADMIN_USER.length > 0 && config.KEYCLOAK_ADMIN_PASSWORD.length > 0;
  return hasClientSecret || hasAdminCreds;
}
