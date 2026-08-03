/**
 * LightSerp Email Service — SMTP2GO integration
 *
 * Handles transactional email sending via SMTP2GO API with HTML templates
 * for verification, password reset, and invitation flows.
 *
 * Adapted from TerraGenius iacgenie backend.
 *
 * Environment variables:
 *   SMTP2GO_API_KEY          SMTP2GO API key
 *   EMAIL_FROM_ADDRESS       Sender email address
 *   SMTP_SERVER              SMTP2GO server (default: mail.smtp2go.com)
 *   SMTP_PORT                SMTP2GO port (default: 2525)
 *   EMAIL_MAX_RETRIES        Max send retries (default: 3)
 *   EMAIL_RETRY_DELAY        Base retry delay in seconds (default: 1.0)
 *   SMTP2GO_SANDBOX          Enable sandbox mode (default: false)
 *   LIGHTSERP_URL            Frontend base URL for generating links
 */

import https from 'node:https';
import { log } from './logger.js';

// ── Configuration ─────────────────────────────────────────────────────

const SMTP2GO_API_KEY = process.env.SMTP2GO_API_KEY || '';
const EMAIL_FROM_ADDRESS = process.env.EMAIL_FROM_ADDRESS || 'noreply@lightserp.ai';
const SMTP_SERVER = process.env.SMTP_SERVER || 'mail.smtp2go.com';
const SMTP_PORT = parseInt(process.env.SMTP_PORT || '2525', 10);
const EMAIL_MAX_RETRIES = parseInt(process.env.EMAIL_MAX_RETRIES || '3', 10);
const EMAIL_RETRY_DELAY = parseFloat(process.env.EMAIL_RETRY_DELAY || '1.0');
const LIGHTSERP_URL = process.env.LIGHTSERP_URL || 'http://localhost:3071';

// ── Email Delivery Result ─────────────────────────────────────────────

interface EmailDeliveryResult {
  success: boolean;
  messageId?: string;
  errorMessage?: string;
  statusCode: number;
  timestamp: Date;
  retryCount: number;
}

// ── Email Templates (inline, brand-adapted to LightSerp) ──────────────

function getVerificationTemplate(
  verificationUrl: string,
  userName?: string
): string {
  const name = userName || 'there';
  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Verify Your Email - LightSerp</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
  <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
    <h1 style="color: white; margin: 0;">LightSerp</h1>
    <p style="color: white; margin: 5px 0 0;">Search &amp; Scrape MCP for AI Models</p>
  </div>
  <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
    <h2>Verify Your Email Address</h2>
    <p>Hello ${name},</p>
    <p>Thank you for signing up with LightSerp! Please verify your email address to complete your registration.</p>
    <div style="text-align: center; margin: 30px 0;">
      <a href="${verificationUrl}" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold;">Verify Email Address</a>
    </div>
    <p style="font-size: 14px; color: #666;">Or copy and paste this link into your browser:</p>
    <p style="font-size: 12px; color: #999; word-break: break-all;">${verificationUrl}</p>
    <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
    <p style="font-size: 12px; color: #999;">
      If you didn't create an account with LightSerp, please ignore this email.<br>
      This verification link will expire in 24 hours.
    </p>
  </div>
  <div style="text-align: center; padding: 20px; color: #999;">
    <p>LightSerp - Search &amp; Scrape MCP for AI Models</p>
  </div>
</body>
</html>`;
}

function getPasswordResetTemplate(
  resetUrl: string,
  userName?: string
): string {
  const name = userName || 'there';
  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Reset Your Password - LightSerp</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
  <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
    <h1 style="color: white; margin: 0;">LightSerp</h1>
    <p style="color: white; margin: 5px 0 0;">Search &amp; Scrape MCP for AI Models</p>
  </div>
  <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
    <h2>Reset Your Password</h2>
    <p>Hello ${name},</p>
    <p>We received a request to reset your password for your LightSerp account.</p>
    <div style="text-align: center; margin: 30px 0;">
      <a href="${resetUrl}" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold;">Reset Password</a>
    </div>
    <p style="font-size: 14px; color: #666;">Or copy and paste this link into your browser:</p>
    <p style="font-size: 12px; color: #999; word-break: break-all;">${resetUrl}</p>
    <div style="background: #fff3cd; padding: 15px; border-radius: 5px; margin-top: 20px;">
      <p style="color: #856404; margin: 0;"><strong>This link will expire in 2 hours.</strong></p>
    </div>
    <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
    <p style="font-size: 12px; color: #999;">
      If you didn't request a password reset, please ignore this email.<br>
      Your current password will remain unchanged.
    </p>
  </div>
  <div style="text-align: center; padding: 20px; color: #999;">
    <p>LightSerp - Search &amp; Scrape MCP for AI Models</p>
  </div>
</body>
</html>`;
}

function getWelcomeTemplate(userName: string, email: string): string {
  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Welcome to LightSerp</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
  <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
    <h1 style="color: white; margin: 0;">LightSerp</h1>
    <p style="color: white; margin: 5px 0 0;">Search &amp; Scrape MCP for AI Models</p>
  </div>
  <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
    <h2>Welcome to LightSerp, ${userName}!</h2>
    <p>Your account has been successfully created.</p>
    <p>You can now use LightSerp to power your AI agents with real-time search and web scraping capabilities.</p>
    <div style="text-align: center; margin: 30px 0;">
      <a href="${LIGHTSERP_URL}" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold;">Get Started</a>
    </div>
    <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
    <p style="font-size: 12px; color: #999;">
      Account: ${email}<br>
      If you have any questions, feel free to reach out.
    </p>
  </div>
  <div style="text-align: center; padding: 20px; color: #999;">
    <p>LightSerp - Search &amp; Scrape MCP for AI Models</p>
  </div>
</body>
</html>`;
}

// ── SMTP2GO API Email Sending ────────────────────────────────────────

function smtp2goSend(
  to: string,
  subject: string,
  htmlBody: string
): Promise<EmailDeliveryResult> {
  return new Promise((resolve) => {
    const payload = JSON.stringify({
      to: [to],
      sender: EMAIL_FROM_ADDRESS,
      subject: subject,
      html_body: htmlBody,
    });

    const options = {
      hostname: SMTP_SERVER,
      port: SMTP_PORT,
      path: '/api/v3/email/send',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Smtp2go-Api-Key': SMTP2GO_API_KEY,
        'Content-Length': Buffer.byteLength(payload),
      },
    };

    const EMAIL_TIMEOUT = parseInt(process.env.EMAIL_TIMEOUT || '10000', 10);

    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        try {
          const result = JSON.parse(data);
          log.debug(`[SMTP2GO] Status ${res.statusCode}: ${JSON.stringify(result)}`);

          // SMTP2GO returns success with status 200 and data.succeeded > 0
          if (res.statusCode === 200 && result.data?.succeeded && result.data.succeeded > 0) {
            resolve({
              success: true,
              messageId: result.data?.messages?.[0]?.message_id,
              statusCode: res.statusCode ?? 0,
              timestamp: new Date(),
              retryCount: 0,
            });
          } else {
            const errMsg = result.message || result.errors?.[0] || `HTTP ${res.statusCode ?? 0}`;
            resolve({
              success: false,
              errorMessage: errMsg,
              statusCode: res.statusCode ?? 0,
              timestamp: new Date(),
              retryCount: 0,
            });
          }
        } catch {
          resolve({
            success: false,
            errorMessage: `Failed to parse SMTP2GO response: ${data}`,
            statusCode: res.statusCode ?? 0,
            timestamp: new Date(),
            retryCount: 0,
          });
        }
      });
    });

    req.on('error', (err) => {
      log.error(`[SMTP2GO] Request failed: ${err.message}`);
      resolve({
        success: false,
        errorMessage: err.message,
        statusCode: 0,
        timestamp: new Date(),
        retryCount: 0,
      });
    });

    req.on('timeout', () => {
      log.warn('[SMTP2GO] Request timed out after ' + EMAIL_TIMEOUT + 'ms');
      req.destroy();
      resolve({
        success: false,
        errorMessage: 'Request timed out',
        statusCode: 0,
        timestamp: new Date(),
        retryCount: 0,
      });
    });
    req.setTimeout(EMAIL_TIMEOUT);

    req.write(payload);
    req.end();
  });
}

// ── Email Validation ─────────────────────────────────────────────────

function validateEmail(email: string): { valid: boolean; error?: string } {
  if (!email || !email.trim()) {
    return { valid: false, error: 'Email is required' };
  }
  const trimmed = email.trim();
  const pattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
  if (!pattern.test(trimmed)) {
    return { valid: false, error: `Invalid email format: ${trimmed}` };
  }
  if (trimmed.length > 254) {
    return { valid: false, error: 'Email address too long' };
  }
  if (trimmed.length < 3) {
    return { valid: false, error: 'Email address too short' };
  }
  return { valid: true };
}

// ── Retry Logic ──────────────────────────────────────────────────────

async function sendWithRetry(
  toEmail: string,
  subject: string,
  htmlContent: string,
  attempt = 0
): Promise<EmailDeliveryResult> {
  const result = await smtp2goSend(toEmail, subject, htmlContent);
  result.retryCount = attempt + 1;

  if (result.success) {
    log.info(`Email sent successfully to ${toEmail}`);
    return result;
  }

  log.warn(`Email attempt ${attempt + 1} failed: ${result.errorMessage}`);

  if (attempt < EMAIL_MAX_RETRIES) {
    const delay = EMAIL_RETRY_DELAY * Math.pow(2, attempt);
    log.info(`Retrying in ${delay}s...`);
    await new Promise((r) => setTimeout(r, delay * 1000));
    return sendWithRetry(toEmail, subject, htmlContent, attempt + 1);
  }

  log.error(`All email delivery attempts failed for ${toEmail}`);
  return result;
}

// ── Public API ────────────────────────────────────────────────────────

interface SendEmailOptions {
  to: string;
  subject: string;
  htmlBody: string;
}

interface SendTemplateOptions {
  to: string;
  userName?: string;
}

async function sendEmail({ to, subject, htmlBody }: SendEmailOptions): Promise<EmailDeliveryResult> {
  const validation = validateEmail(to);
  if (!validation.valid) {
    return {
      success: false,
      errorMessage: `Email validation failed: ${validation.error}`,
      statusCode: 400,
      timestamp: new Date(),
      retryCount: 0,
    };
  }

  if (!SMTP2GO_API_KEY) {
    log.warn(`SMTP2GO_API_KEY not configured. Would send to ${to}`);
    return {
      success: true,
      errorMessage: 'Email service not configured (dry-run mode)',
      statusCode: 0,
      timestamp: new Date(),
      retryCount: 0,
    };
  }

  return sendWithRetry(to, subject, htmlBody);
}

async function sendVerificationEmail({
  to,
  userName,
  verificationUrl,
}: SendTemplateOptions & { verificationUrl: string }): Promise<EmailDeliveryResult> {
  const subject = 'Verify Your Email - LightSerp';
  const htmlBody = getVerificationTemplate(verificationUrl, userName);
  return sendEmail({ to, subject, htmlBody });
}

async function sendPasswordResetEmail({
  to,
  userName,
  resetUrl,
}: SendTemplateOptions & { resetUrl: string }): Promise<EmailDeliveryResult> {
  const subject = 'Reset Your Password - LightSerp';
  const htmlBody = getPasswordResetTemplate(resetUrl, userName);
  return sendEmail({ to, subject, htmlBody });
}

async function sendWelcomeEmail({
  to,
  userName,
}: SendTemplateOptions & { userName: string }): Promise<EmailDeliveryResult> {
  const subject = 'Welcome to LightSerp!';
  const htmlBody = getWelcomeTemplate(userName, to);
  return sendEmail({ to, subject, htmlBody });
}

function isConfigured(): boolean {
  return !!SMTP2GO_API_KEY;
}

// ── Export ────────────────────────────────────────────────────────────

export {
  sendEmail,
  sendVerificationEmail,
  sendPasswordResetEmail,
  sendWelcomeEmail,
  isConfigured,
  validateEmail,
  type EmailDeliveryResult,
  type SendEmailOptions,
};
