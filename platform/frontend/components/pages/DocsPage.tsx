import React, { useState, useEffect, useRef } from 'react';
import CodeBlock from '../ui/CodeBlock';

const DOC_SECTIONS = [
    { id: 'getting-started', title: 'Getting Started' },
    { id: 'authentication', title: 'Authentication' },
    { id: 'generating-infra', title: 'Generating Infrastructure' },
    { id: 'deployments', title: 'Deployments' },
    { id: 'project-settings', title: 'Project Settings' },
    { id: 'team-rbac', title: 'Team & RBAC' },
    { id: 'cli-usage', title: 'CLI Usage' },
    { id: 'api-reference', title: 'API Reference' },
    { id: 'webhooks', title: 'Webhooks' },
    { id: 'rate-limiting', title: 'Rate Limiting' },
    { id: 'error-handling', title: 'Error Handling' },
    { id: 'billing-plans', title: 'Billing & Plans' },
    { id: 'security-compliance', title: 'Security & Compliance' },
];

const DocsPage: React.FC = () => {
    const [activeSection, setActiveSection] = useState(DOC_SECTIONS[0].id);
    const sectionRefs = useRef<(HTMLElement | null)[]>([]);

    useEffect(() => {
        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        setActiveSection(entry.target.id);
                    }
                });
            },
            { rootMargin: `-100px 0px -80% 0px`, threshold: 0 }
        );

        const currentRefs = sectionRefs.current;
        currentRefs.forEach((ref) => {
            if (ref) observer.observe(ref);
        });

        return () => {
            currentRefs.forEach((ref) => {
                if (ref) observer.unobserve(ref);
            });
        };
    }, []);
    
    const assignRef = (el: HTMLElement | null, index: number) => {
        sectionRefs.current[index] = el;
    };

    const DocsContent = () => (
        <article className="prose prose-lg max-w-none 
                            prose-h2:font-bold prose-h2:text-3xl prose-h2:mb-4 prose-h2:pb-2 prose-h2:border-b prose-h2:border-slate-200 dark:prose-h2:border-slate-600
                            prose-h3:text-orange-600 prose-h3:font-semibold prose-h3:text-xl
                            prose-a:text-orange-600 hover:prose-a:text-orange-500
                            prose-strong:text-slate-900 dark:prose-strong:text-slate-50 prose-ul:list-disc prose-ul:pl-6 prose-li:my-1
                            prose-code:bg-orange-100 prose-code:text-orange-600 prose-code:rounded prose-code:px-1.5 prose-code:py-0.5 prose-code:font-mono prose-code:text-sm
                            prose-p:leading-relaxed text-slate-700 dark:text-slate-200">
            
            <div className="mb-8">
                <p className="text-sm font-semibold text-orange-600">Iacgenie Documentation</p>
                <h1 className="text-5xl font-extrabold text-slate-900 dark:text-slate-50 tracking-tight">Documentation</h1>
                <p className="text-slate-500 dark:text-slate-400">Last updated: January 2025</p>
            </div>
            
            <section id="getting-started" ref={el => assignRef(el, 0)}>
                <h2>Getting Started</h2>
                <p>Welcome to Iacgenie! This guide will walk you through the core concepts and features of the platform.</p>
                <h3>What is Iacgenie?</h3>
                <p>Iacgenie is an AI-powered platform that accelerates cloud infrastructure development. It translates natural language prompts into production-ready Infrastructure-as-Code (IaC), supporting OpenTofu, Docker, and Kubernetes across major cloud providers like AWS, GCP, and Azure.</p>
                <h3>Key Features</h3>
                <ul>
                    <li><strong>Natural Language to IaC:</strong> Describe your needs in English; get high-quality code.</li>
                    <li><strong>Multi-Cloud & Multi-Tool:</strong> Support for AWS, GCP, Azure, OpenTofu, Docker, and Kubernetes.</li>
                    <li><strong>Direct Deployment:</strong> Deploy generated code directly to your cloud accounts.</li>
                    <li><strong>Git Integration:</strong> Push code to your GitHub, GitLab, or Bitbucket repositories.</li>
                    <li><strong>Team Collaboration:</strong> Invite team members and manage access with RBAC.</li>
                    <li><strong>CLI & API Access:</strong> Automate your workflows with our powerful CLI and REST API.</li>
                    <li><strong>Webhook Integration:</strong> Real-time notifications and external service integration.</li>
                </ul>
            </section>

            <section id="authentication" ref={el => assignRef(el, 1)}>
                <h2>Authentication</h2>
                <p>Iacgenie provides a comprehensive authentication system using Firebase Authentication with dedicated API endpoints for user authentication and token verification.</p>
                
                <h3>Authentication Endpoints</h3>
                <p>Use our dedicated authentication endpoints to authenticate users and verify tokens:</p>
                
                <h4>POST /auth/token</h4>
                <p>Authenticate a user with email and password.</p>
                <CodeBlock language="bash" code={
`curl -X POST http://localhost:8000/auth/token \\
  -H "Content-Type: application/json" \\
  -d '{"email": "user@example.com", "password": "userpassword123"}'`
                } />
                
                <h4>POST /auth/token/verify</h4>
                <p>Verify a Firebase ID token and get user information.</p>
                <CodeBlock language="bash" code={
`curl -X POST http://localhost:8000/auth/token/verify \\
  -H "Content-Type: application/json" \\
  -d '{"token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."}'`
                } />
                
                <h4>GET /auth/health</h4>
                <p>Check the health of the authentication service.</p>
                <CodeBlock language="bash" code="curl -X GET http://localhost:8000/auth/health" />
                
                <h3>Authentication Methods</h3>
                <ul>
                    <li><strong>Firebase Authentication:</strong> Primary authentication method using Firebase ID tokens.</li>
                    <li><strong>Email/Password:</strong> Standard login using Firebase Auth via our /auth/token endpoint.</li>
                    <li><strong>Google Login:</strong> Use your Google account for seamless SSO.</li>
                    <li><strong>SAML 2.0 SSO:</strong> For enterprise customers, we support integration with providers like Okta and Azure AD.</li>
                </ul>
                
                <h3>API Authentication</h3>
                <p>For programmatic access via the CLI or REST API, you can generate API keys from your user settings page. Treat these keys like passwords and keep them secure.</p>
                
                <h3>Firebase Token Usage</h3>
                <p>Most API endpoints require Firebase authentication. Include your Firebase ID token in the Authorization header:</p>
                <CodeBlock language="http" code="Authorization: Bearer <your-firebase-token>" />
                <p><strong>Note:</strong> Firebase tokens expire after 1 hour. Your application should handle token refresh automatically.</p>
                
                <h3>Example Authentication Flow</h3>
                <CodeBlock language="javascript" code={
`// 1. Authenticate user
const authResponse = await fetch('/auth/token', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'userpassword123'
  })
});

const authData = await authResponse.json();
if (authData.success) {
  const token = authData.data.token;
  
  // 2. Use token for API requests
  const response = await fetch('/api/generate', {
    headers: {
      'Authorization': \`Bearer \${token}\`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(generationRequest)
  });
}`
                } />
                
                <h3>Error Handling</h3>
                <p>Authentication endpoints return standardized error responses:</p>
                <CodeBlock language="json" code={
`{
  "success": false,
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "The email or password provided is incorrect.",
    "statusCode": 401,
    "details": {},
    "timestamp": "2025-01-06T17:00:00.000Z"
  }
}`
                } />
                
                <h4>Common Error Codes</h4>
                <ul>
                    <li><code>INVALID_CREDENTIALS</code>: Wrong email or password</li>
                    <li><code>ACCOUNT_DISABLED</code>: User account has been disabled</li>
                    <li><code>RATE_LIMITED</code>: Too many failed login attempts</li>
                    <li><code>INVALID_TOKEN</code>: Token is invalid or expired</li>
                    <li><code>NETWORK_ERROR</code>: Firebase service unavailable</li>
                    <li><code>INTERNAL_ERROR</code>: Server error</li>
                </ul>
            </section>
            
            <section id="generating-infra" ref={el => assignRef(el, 2)}>
                <h2>Generating Infrastructure</h2>
                <p>The core of Iacgenie is the Generator. Here's how to create infrastructure from a simple prompt.</p>
                <h3>Writing Effective Prompts</h3>
                <p>Be specific and clear. Include the cloud provider, services, and key configurations.</p>
                <blockquote>"Create a public S3 bucket for website hosting in us-east-1 with versioning enabled and a default index.html document."</blockquote>
                <h3>Configuration Options</h3>
                <ol>
                    <li><strong>Select AI Model:</strong> Choose from models like Gemini 2.5 Flash, GPT-4, or Mistral.</li>
                    <li><strong>Choose Provider:</strong> Select AWS, GCP, or Azure.</li>
                    <li><strong>Set Output Type:</strong> Choose OpenTofu, Dockerfile, or Kubernetes YAML.</li>
                </ol>
                <p>After generation, you can preview the code in the editor, download it as a ZIP file, or push it directly to a connected Git repository.</p>
            </section>
            
            <section id="deployments" ref={el => assignRef(el, 3)}>
                <h2>Deployments</h2>
                <p>Deploy your generated infrastructure directly from the Iacgenie UI or CLI.</p>
                <h3>Deployment Modes</h3>
                <ul>
                    <li><strong>OpenTofu:</strong> We run <code>terraform plan</code> and <code>terraform apply</code> in a secure, sandboxed environment.</li>
                    <li><strong>Docker:</strong> Deploys a container to a specified host using Docker Compose.</li>
                    <li><strong>Kubernetes:</strong> Applies YAML manifests or Helm charts to a configured cluster.</li>
                </ul>
                <h3>Managing Deployments</h3>
                <p>On the Deployments page, you can:</p>
                <ul>
                    <li>View live logs for `plan` and `apply` stages.</li>
                    <li>Access outputs, such as public IP addresses or DNS names.</li>
                    <li>Redeploy a previous configuration with a single click.</li>
                    <li>View deployment history and statuses (Success, Failed, Running).</li>
                </ul>
            </section>
            
            <section id="project-settings" ref={el => assignRef(el, 4)}>
                 <h2>Project Settings</h2>
                <p>Each project has its own configurable settings.</p>
                 <ul>
                    <li><strong>Project Info:</strong> Rename your project or update its description.</li>
                    <li><strong>Cloud Credentials:</strong> Securely add and manage credentials for AWS, GCP, or Azure. Keys are encrypted at rest.</li>
                    <li><strong>Git Integration:</strong> Connect to a GitHub, GitLab, or Bitbucket repository to push generated code.</li>
                    <li><strong>Environment Variables:</strong> Manage secrets and environment variables for your deployments.</li>
                </ul>
            </section>
            
             <section id="team-rbac" ref={el => assignRef(el, 5)}>
                <h2>Team & RBAC</h2>
                <p>Collaborate with your team by inviting them to your projects and assigning roles.</p>
                 <h3>Project Permissions Matrix</h3>
                <div className="overflow-x-auto">
                    <table className="min-w-full border border-slate-300 dark:border-slate-500">
                        <thead>
                            <tr className="bg-slate-50 dark:bg-slate-700/50">
                                <th className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-left">Permission</th>
                                <th className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">Owner</th>
                                <th className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">Admin</th>
                                <th className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">Editor</th>
                                <th className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">Viewer</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2">View project</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">✅</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">✅</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">✅</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">✅</td>
                            </tr>
                            <tr>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2">Generate code</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">✅</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">✅</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">✅</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">❌</td>
                            </tr>
                            <tr>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2">Deploy infrastructure</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">✅</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">✅</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">✅</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">❌</td>
                            </tr>
                            <tr>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2">Manage team members</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">✅</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">✅</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">❌</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">❌</td>
                            </tr>
                            <tr>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2">Update project settings</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">✅</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">✅</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">❌</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">❌</td>
                            </tr>
                            <tr>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2">Delete project</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">✅</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">❌</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">❌</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">❌</td>
                            </tr>
                            <tr>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2">Manage billing</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">✅</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">❌</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">❌</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">❌</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <p>You can invite new members via email from the Project Settings page.</p>
            </section>

            <section id="cli-usage" ref={el => assignRef(el, 6)}>
                <h2>CLI Usage</h2>
                <p>Automate everything with the <code>iac-cli</code> tool.</p>
                <h3>Installation</h3>
                <CodeBlock language="shell" code="npm install -g @iacgenie/cli" />
                <h3>Authentication</h3>
                <p>Log in with your Firebase token or API key.</p>
                <CodeBlock language="shell" code="iac login --firebase-token <your-token>" />
                <h3>Common Commands</h3>
                <CodeBlock language="shell" code={
`# Generate code from a prompt
iac generate "Create a serverless function in AWS"

# Deploy the last generated code
iac deploy

# List all your projects
iac projects:list

# Get project details
iac projects:get <project-id>

# List deployments
iac deployments:list <project-id>`
                } />
                <h3>Configuration File</h3>
                <p>Your authentication details are stored in <code>~/.iac-cli/config.yaml</code>.</p>
                <CodeBlock language="yaml" code={
`firebase_token: <your-firebase-token>
base_url: https://api.iacgenie.ai
default_project: <project-id>`
                } />
            </section>
            
             <section id="api-reference" ref={el => assignRef(el, 7)}>
                <h2>API Reference</h2>
                <p>Integrate Iacgenie into your own applications using our REST API.</p>
                <h3>Base URL</h3>
                <p>Production: <code>https://api.iacgenie.ai</code><br/>
                Development: <code>http://localhost:8000</code></p>
                
                <h3>Authentication</h3>
                <p>Include your Firebase ID token in the Authorization header as a Bearer token.</p>
                <CodeBlock language="http" code="Authorization: Bearer <your-firebase-token>" />
                
                <h3>Response Format</h3>
                <p>All API responses follow a standardized format:</p>
                <CodeBlock language="json" code={
`{
  "success": true,
  "message": "Operation completed successfully",
  "data": { ... },
  "timestamp": "2025-01-06T17:00:00.000Z"
}`
                } />
                
                <h3>Error Response Format</h3>
                <CodeBlock language="json" code={
`{
  "success": false,
  "error": {
    "message": "Error description",
    "code": "ERROR_CODE",
    "statusCode": 400,
    "details": { ... },
    "timestamp": "2025-01-06T17:00:00.000Z"
  }
}`
                } />
                
                <h3>Generate Code</h3>
                <p><strong>POST</strong> <code>/api/generate</code></p>
                <CodeBlock language="json" code={
`{
  "prompt": "An S3 bucket with read-only public access.",
  "model": "gpt-4",
  "provider": "openai",
  "project_id": "optional-project-id"
}`
                } />
                
                <h3>Get Generation Status</h3>
                <p><strong>GET</strong> <code>/api/generate/status/{'{job_id}'}</code></p>
                <CodeBlock language="json" code={
`{
  "job_id": "uuid",
  "status": "completed",
  "logs": [...],
  "code": [...]
}`
                } />
                
                <h3>Deploy Infrastructure</h3>
                <p><strong>POST</strong> <code>/api/deploy</code></p>
                <CodeBlock language="json" code={
`{
  "job_id": "generation-job-id",
  "project_name": "my-project"
}`
                } />
                
                <h3>List Projects</h3>
                <p><strong>GET</strong> <code>/api/projects/</code></p>
                
                <h3>Get Project</h3>
                <p><strong>GET</strong> <code>/api/projects/{'{project_id}'}/</code></p>
                
                <h3>Create Project</h3>
                <p><strong>POST</strong> <code>/api/projects/</code></p>
                <CodeBlock language="json" code={
`{
  "name": "My Infrastructure Project",
  "description": "Production infrastructure for web application"
}`
                } />
                
                <h3>Model Configurations</h3>
                <p><strong>GET</strong> <code>/api/model-configs/{'{project_id}'}/</code> - List model configs<br/>
                <strong>POST</strong> <code>/api/model-configs/{'{project_id}'}/</code> - Create model config<br/>
                <strong>PUT</strong> <code>/api/model-configs/{'{project_id}'}/{'{config_id}'}/</code> - Update model config<br/>
                <strong>DELETE</strong> <code>/api/model-configs/{'{project_id}'}/{'{config_id}'}/</code> - Delete model config</p>
                
                <h3>Team Members</h3>
                <p><strong>GET</strong> <code>/api/team-members/{'{project_id}'}/</code> - List team members<br/>
                <strong>POST</strong> <code>/api/team-members/{'{project_id}'}/</code> - Add team member<br/>
                <strong>PUT</strong> <code>/api/team-members/{'{project_id}'}/{'{member_id}'}/</code> - Update team member<br/>
                <strong>DELETE</strong> <code>/api/team-members/{'{project_id}'}/{'{member_id}'}/</code> - Remove team member</p>
                
                <h3>Webhooks</h3>
                <p><strong>GET</strong> <code>/api/webhooks/</code> - List webhooks<br/>
                <strong>POST</strong> <code>/api/webhooks/</code> - Create webhook<br/>
                <strong>POST</strong> <code>/api/webhooks/receive</code> - Receive webhook (public endpoint)</p>
                
                <h3>Health Checks</h3>
                <p><strong>GET</strong> <code>/api/health</code> - Overall health<br/>
                <strong>GET</strong> <code>/api/database/health</code> - Database health<br/>
                <strong>GET</strong> <code>/api/models/health</code> - AI models health</p>
            </section>
            
            <section id="webhooks" ref={el => assignRef(el, 8)}>
                <h2>Webhooks</h2>
                <p>Iacgenie AI supports comprehensive webhook functionality for real-time notifications and external integrations.</p>
                
                <h3>Webhook Types</h3>
                <ul>
                    <li><strong>Outgoing Webhooks:</strong> Send notifications to external services when events occur</li>
                    <li><strong>Incoming Webhooks:</strong> Receive webhooks from external services (GitHub, Slack, etc.)</li>
                </ul>
                
                <h3>Supported Event Types</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <h4>Generation Events</h4>
                        <ul>
                            <li><code>generation.started</code> - Code generation initiated</li>
                            <li><code>generation.completed</code> - Code generation finished successfully</li>
                            <li><code>generation.failed</code> - Code generation failed</li>
                        </ul>
                    </div>
                    <div>
                        <h4>Deployment Events</h4>
                        <ul>
                            <li><code>deployment.started</code> - Deployment initiated</li>
                            <li><code>deployment.completed</code> - Deployment finished successfully</li>
                            <li><code>deployment.failed</code> - Deployment failed</li>
                        </ul>
                    </div>
                    <div>
                        <h4>Project Events</h4>
                        <ul>
                            <li><code>project.created</code> - New project created</li>
                            <li><code>project.updated</code> - Project updated</li>
                            <li><code>project.deleted</code> - Project deleted</li>
                        </ul>
                    </div>
                    <div>
                        <h4>Team Events</h4>
                        <ul>
                            <li><code>team.member.added</code> - Team member added</li>
                            <li><code>team.member.removed</code> - Team member removed</li>
                            <li><code>team.member.updated</code> - Team member role updated</li>
                        </ul>
                    </div>
                </div>
                
                <h3>Webhook Security</h3>
                <p>All outgoing webhooks include HMAC signature verification for security:</p>
                <CodeBlock language="http" code={
`X-Iacgenie-Signature: sha256=abc123...
X-Iacgenie-Timestamp: 1640995200`
                } />
                
                <h3>Retry Logic</h3>
                <p>Webhook delivery includes automatic retry with exponential backoff:</p>
                <ul>
                    <li><strong>Initial Retry:</strong> 1 minute after failure</li>
                    <li><strong>Exponential Backoff:</strong> 2x, 4x, 8x, 16x intervals</li>
                    <li><strong>Maximum Retries:</strong> 5 attempts</li>
                    <li><strong>Dead Letter Queue:</strong> Failed webhooks stored for manual review</li>
                </ul>
                
                <h3>Incoming Webhook Support</h3>
                <p>Iacgenie can receive webhooks from external services:</p>
                <ul>
                    <li><strong>GitHub:</strong> Repository events, pull requests, deployments</li>
                    <li><strong>Slack:</strong> Command responses, interactive messages</li>
                    <li><strong>Generic:</strong> Any HTTP POST webhook</li>
                </ul>
                
                <h3>Webhook Payload Example</h3>
                <CodeBlock language="json" code={
`{
  "event": "generation.completed",
  "timestamp": "2025-01-06T17:00:00.000Z",
  "data": {
    "generation_id": "gen_123",
    "project_id": "proj_456",
    "prompt": "Create an S3 bucket",
    "model": "gpt-4",
    "provider": "openai",
    "files_count": 3,
    "status": "completed"
  },
  "metadata": {
    "user_id": "user_789",
    "webhook_id": "webhook_abc"
  }
}`
                } />
            </section>
            
            <section id="rate-limiting" ref={el => assignRef(el, 9)}>
                <h2>Rate Limiting</h2>
                <p>API endpoints are protected by rate limiting to ensure fair usage and prevent abuse.</p>
                
                <h3>Rate Limit Tiers</h3>
                <div className="overflow-x-auto">
                    <table className="min-w-full border border-slate-300 dark:border-slate-500">
                        <thead>
                            <tr className="bg-slate-50 dark:bg-slate-700/50">
                                <th className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-left">Endpoint Category</th>
                                <th className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">Requests/Hour</th>
                                <th className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">Window</th>
                                <th className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-left">Description</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2">Health Checks</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">1,000</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">1 hour</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2">System health monitoring</td>
                            </tr>
                            <tr>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2">CRUD Operations</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">100</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">1 hour</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2">Standard API operations</td>
                            </tr>
                            <tr>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2">Code Generation</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">30</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">1 hour</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2">AI-powered code generation</td>
                            </tr>
                            <tr>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2">Deployments</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">20</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">1 hour</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2">Infrastructure deployments</td>
                            </tr>
                            <tr>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2">Webhook Operations</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">50</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">1 hour</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2">Webhook management</td>
                            </tr>
                            <tr>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2">Admin Operations</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">10</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2 text-center">1 hour</td>
                                <td className="border border-slate-300 dark:border-slate-500 px-4 py-2">Administrative functions</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                
                <h3>Rate Limit Headers</h3>
                <p>All API responses include rate limit information in headers:</p>
                <CodeBlock language="http" code={
`X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640998800
Retry-After: 3600`
                } />
                
                <h3>Rate Limit Exceeded Response</h3>
                <CodeBlock language="json" code={
`{
  "success": false,
  "error": {
    "message": "Rate limit exceeded",
    "code": "RATE_LIMIT_EXCEEDED",
    "statusCode": 429,
    "details": {
      "limit": 100,
      "remaining": 0,
      "reset_time": 1640998800,
      "retry_after": 3600
    },
    "timestamp": "2025-01-06T17:00:00.000Z"
  }
}`
                } />
            </section>
            
            <section id="error-handling" ref={el => assignRef(el, 10)}>
                <h2>Error Handling</h2>
                <p>Iacgenie API provides comprehensive error handling with detailed error codes and messages.</p>
                
                <h3>HTTP Status Codes</h3>
                <ul>
                    <li><strong>200 OK:</strong> Request successful</li>
                    <li><strong>201 Created:</strong> Resource created successfully</li>
                    <li><strong>400 Bad Request:</strong> Invalid request parameters</li>
                    <li><strong>401 Unauthorized:</strong> Authentication required or invalid</li>
                    <li><strong>403 Forbidden:</strong> Insufficient permissions</li>
                    <li><strong>404 Not Found:</strong> Resource not found</li>
                    <li><strong>409 Conflict:</strong> Resource conflict (e.g., duplicate name)</li>
                    <li><strong>422 Unprocessable Entity:</strong> Validation errors</li>
                    <li><strong>429 Too Many Requests:</strong> Rate limit exceeded</li>
                    <li><strong>500 Internal Server Error:</strong> Server error</li>
                    <li><strong>503 Service Unavailable:</strong> Service temporarily unavailable</li>
                </ul>
                
                <h3>Error Codes</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <h4>Authentication Errors</h4>
                        <ul>
                            <li><code>AUTH_REQUIRED</code> - Authentication required</li>
                            <li><code>AUTH_INVALID</code> - Invalid credentials</li>
                            <li><code>AUTH_EXPIRED</code> - Token expired</li>
                            <li><code>AUTH_INSUFFICIENT_PERMISSIONS</code> - Insufficient permissions</li>
                        </ul>
                    </div>
                    <div>
                        <h4>Validation Errors</h4>
                        <ul>
                            <li><code>VALIDATION_ERROR</code> - Request validation failed</li>
                            <li><code>MISSING_REQUIRED_FIELD</code> - Required field missing</li>
                            <li><code>INVALID_FORMAT</code> - Invalid data format</li>
                            <li><code>DUPLICATE_RESOURCE</code> - Resource already exists</li>
                        </ul>
                    </div>
                    <div>
                        <h4>Resource Errors</h4>
                        <ul>
                            <li><code>RECORD_NOT_FOUND</code> - Resource not found</li>
                            <li><code>RESOURCE_CONFLICT</code> - Resource conflict</li>
                            <li><code>RESOURCE_LOCKED</code> - Resource is locked</li>
                            <li><code>RESOURCE_DELETED</code> - Resource was deleted</li>
                        </ul>
                    </div>
                    <div>
                        <h4>System Errors</h4>
                        <ul>
                            <li><code>INTERNAL_ERROR</code> - Internal server error</li>
                            <li><code>DB_CONNECTION_ERROR</code> - Database connection error</li>
                            <li><code>EXTERNAL_SERVICE_ERROR</code> - External service error</li>
                            <li><code>SERVICE_UNAVAILABLE</code> - Service unavailable</li>
                        </ul>
                    </div>
                </div>
                
                <h3>Handling Empty States</h3>
                <p>When no resources are found, the API returns an empty array or appropriate empty state:</p>
                <CodeBlock language="json" code={
`{
  "success": true,
  "message": "No resources found",
  "data": [],
  "timestamp": "2025-01-06T17:00:00.000Z"
}`
                } />
                
                <h3>Race Condition Handling</h3>
                <p>The API handles race conditions through:</p>
                <ul>
                    <li><strong>Optimistic Locking:</strong> Version-based conflict detection</li>
                    <li><strong>Idempotency Keys:</strong> Prevent duplicate operations</li>
                    <li><strong>Atomic Operations:</strong> Database-level transaction safety</li>
                    <li><strong>Retry Logic:</strong> Automatic retry for transient failures</li>
                </ul>
            </section>
            
            <section id="billing-plans" ref={el => assignRef(el, 11)}>
                <h2>Billing & Plans</h2>
                <p>Iacgenie offers flexible pricing plans to fit your infrastructure needs.</p>
                <h3>Free Tier</h3>
                <ul>
                    <li><strong>Generations:</strong> 10 per month</li>
                    <li><strong>Deployments:</strong> 5 per month</li>
                    <li><strong>Team Members:</strong> 2 users</li>
                    <li><strong>Projects:</strong> 3 projects</li>
                    <li><strong>Storage:</strong> 1GB</li>
                </ul>
                <h3>Pro Plan ($29/month)</h3>
                <ul>
                    <li><strong>Generations:</strong> 100 per month</li>
                    <li><strong>Deployments:</strong> 50 per month</li>
                    <li><strong>Team Members:</strong> 10 users</li>
                    <li><strong>Projects:</strong> Unlimited</li>
                    <li><strong>Storage:</strong> 10GB</li>
                    <li><strong>Priority Support:</strong> Email support</li>
                </ul>
                <h3>Enterprise Plan (Custom)</h3>
                <ul>
                    <li><strong>Generations:</strong> Unlimited</li>
                    <li><strong>Deployments:</strong> Unlimited</li>
                    <li><strong>Team Members:</strong> Unlimited</li>
                    <li><strong>Projects:</strong> Unlimited</li>
                    <li><strong>Storage:</strong> Unlimited</li>
                    <li><strong>Priority Support:</strong> 24/7 phone and email support</li>
                    <li><strong>SAML SSO:</strong> Enterprise authentication</li>
                    <li><strong>Custom Integrations:</strong> Dedicated support for custom workflows</li>
                </ul>
            </section>
            
            <section id="security-compliance" ref={el => assignRef(el, 12)}>
                <h2>Security & Compliance</h2>
                <p>Iacgenie is built with enterprise-grade security and compliance in mind.</p>
                <h3>Data Security</h3>
                <ul>
                    <li><strong>Encryption at Rest:</strong> All data is encrypted using AES-256</li>
                    <li><strong>Encryption in Transit:</strong> TLS 1.3 for all communications</li>
                    <li><strong>API Keys:</strong> Securely hashed and stored</li>
                    <li><strong>Cloud Credentials:</strong> Encrypted before storage</li>
                </ul>
                <h3>Authentication & Authorization</h3>
                <ul>
                    <li><strong>Firebase Auth:</strong> Industry-standard authentication</li>
                    <li><strong>Role-Based Access Control:</strong> Granular permissions</li>
                    <li><strong>Multi-Factor Authentication:</strong> Optional MFA support</li>
                    <li><strong>Session Management:</strong> Secure session handling</li>
                </ul>
                <h3>Compliance</h3>
                <ul>
                    <li><strong>SOC 2 Type II:</strong> Security and availability controls</li>
                    <li><strong>GDPR:</strong> Data protection and privacy compliance</li>
                    <li><strong>HIPAA:</strong> Healthcare data protection (Enterprise only)</li>
                    <li><strong>ISO 27001:</strong> Information security management</li>
                </ul>
                <h3>Infrastructure Security</h3>
                <ul>
                    <li><strong>Cloud Security:</strong> Deployed on secure cloud infrastructure</li>
                    <li><strong>Network Security:</strong> VPC isolation and security groups</li>
                    <li><strong>Monitoring:</strong> 24/7 security monitoring and alerting</li>
                    <li><strong>Incident Response:</strong> Rapid response to security incidents</li>
                </ul>
            </section>
        </article>
    );

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-700/50 dark:bg-slate-950 transition-colors duration-200">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <div className="lg:grid lg:grid-cols-12 lg:gap-8">
                    {/* Sidebar */}
                    <aside className="lg:col-span-3">
                        <nav className="sticky top-24 space-y-1">
                            {DOC_SECTIONS.map((section) => (
                                <a
                                    key={section.id}
                                    href={`#${section.id}`}
                                    className={`block px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                                        activeSection === section.id
                                            ? 'bg-orange-100 text-orange-700 border-r-2 border-orange-500 dark:bg-orange-950/40 dark:text-orange-400'
                                            : 'text-slate-600 dark:text-slate-300 dark:text-slate-400 hover:text-orange-600 dark:hover:text-orange-400 hover:bg-orange-50 dark:hover:bg-orange-950/10'
                                    }`}
                                    onClick={(e) => {
                                        e.preventDefault();
                                        document.getElementById(section.id)?.scrollIntoView({ behavior: 'smooth' });
                                    }}
                                >
                                    {section.title}
                                </a>
                            ))}
                        </nav>
                    </aside>

                    {/* Main content */}
                    <main className="lg:col-span-9">
                        <div className="bg-white dark:bg-slate-900 rounded-lg shadow-sm border border-slate-200 dark:border-slate-600 dark:border-slate-800 p-8">
                            <DocsContent />
                        </div>
                    </main>
                </div>
            </div>
        </div>
    );
};

export default DocsPage;