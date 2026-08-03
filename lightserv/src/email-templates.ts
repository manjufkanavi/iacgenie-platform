/**
 * Shared email templates for LightSerp.
 * Eliminates duplication across auth.ts and email-service.ts.
 * Template strings use {{variable}} placeholders.
 */

interface TemplateVars {
  [key: string]: string;
}

const BASE_HEAD = `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{title}}</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
  <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
    <h1 style="color: white; margin: 0;">LightSerp</h1>
    <p style="color: white; margin: 5px 0 0;">Search &amp; Scrape MCP for AI Models</p>
  </div>`;

const BASE_FOOTER = `<div style="text-align: center; padding: 20px; color: #999;">
  <p>LightSerp - Search &amp; Scrape MCP for AI Models</p>
</div>
</body>
</html>`;

function compile(template: string, vars: TemplateVars): string {
  return template.replace(/\{\{(\w+)\}\}/g, (_match: string, key: string) => {
    return vars[key] !== undefined ? String(vars[key]) : '';
  });
}

export function buildVerificationEmail(verificationUrl: string, userName?: string): string {
  const name = userName || 'there';
  return compile(
    `${BASE_HEAD}
  <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
    <h2>Verify Your Email Address</h2>
    <p>Hello {{name}},</p>
    <p>Thank you for signing up with LightSerp! Please verify your email address to complete your registration.</p>
    <div style="text-align: center; margin: 30px 0;">
      <a href="{{url}}" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold;">Verify Email Address</a>
    </div>
    <p style="font-size: 14px; color: #666;">Or copy and paste this link into your browser:</p>
    <p style="font-size: 12px; color: #999; word-break: break-all;">{{url}}</p>
    <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
    <p style="font-size: 12px; color: #999;">
      If you didn't create an account with LightSerp, please ignore this email.<br>
      This verification link will expire in 24 hours.
    </p>
  </div>
  ${BASE_FOOTER}`,
    { title: 'Verify Your Email - LightSerp', name, url: verificationUrl }
  );
}

export function buildWelcomeEmail(userName: string, email: string, lightSerpUrl: string): string {
  return compile(
    `${BASE_HEAD}
  <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
    <h2>Welcome to LightSerp, {{name}}!</h2>
    <p>Your email has been verified and your account is now fully active.</p>
    <p>You can now use LightSerp to power your AI agents with real-time search and web scraping capabilities.</p>
    <div style="text-align: center; margin: 30px 0;">
      <a href="{{appUrl}}" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold;">Get Started</a>
    </div>
    <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
    <p style="font-size: 12px; color: #999;">
      Account: {{email}}<br>
      If you have any questions, feel free to reach out.
    </p>
  </div>
  ${BASE_FOOTER}`,
    { title: 'Welcome to LightSerp', name: userName, email, appUrl: lightSerpUrl }
  );
}

export function buildPasswordResetEmail(resetUrl: string, userName: string): string {
  const name = userName || 'there';
  return compile(
    `${BASE_HEAD}
  <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
    <h2>Reset Your Password</h2>
    <p>Hello {{name}},</p>
    <p>We received a request to reset your password for your LightSerp account.</p>
    <div style="text-align: center; margin: 30px 0;">
      <a href="{{url}}" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold;">Reset Password</a>
    </div>
    <p style="font-size: 14px; color: #666;">Or copy and paste this link into your browser:</p>
    <p style="font-size: 12px; color: #999; word-break: break-all;">{{url}}</p>
    <div style="background: #fff3cd; padding: 15px; border-radius: 5px; margin-top: 20px;">
      <p style="color: #856404; margin: 0;"><strong>This link will expire in 2 hours.</strong></p>
    </div>
    <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
    <p style="font-size: 12px; color: #999;">
      If you didn't request a password reset, please ignore this email.<br>
      Your current password will remain unchanged.
    </p>
  </div>
  ${BASE_FOOTER}`,
    { title: 'Reset Your Password - LightSerp', name, url: resetUrl }
  );
}
