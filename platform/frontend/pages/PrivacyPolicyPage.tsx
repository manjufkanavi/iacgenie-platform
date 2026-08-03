
import React from 'react';

const PrivacyPolicyPage: React.FC = () => {
  return (
    <div className="bg-white dark:bg-slate-950 py-16 text-gray-900 dark:text-slate-100 transition-colors duration-200">
        <div className="max-w-4xl mx-auto px-4">
          <div className="mb-8 text-center">
            <h1 className="text-4xl font-extrabold text-gray-900 dark:text-white sm:text-5xl">Privacy Policy</h1>
            <p className="mt-2 text-gray-600 dark:text-slate-400">Effective Date: October 26, 2023</p>
          </div>

          <div className="prose prose-lg max-w-none space-y-6 text-gray-700 dark:text-slate-300
                          prose-h2:text-gray-900 dark:prose-h2:text-white prose-h2:font-bold prose-h2:text-2xl
                          prose-h3:text-brand-primary prose-h3:font-semibold prose-h3:text-xl
                          prose-a:text-brand-primary hover:prose-a:text-brand-primary/80
                          prose-strong:text-gray-900 dark:prose-strong:text-white">
            <p>
              Welcome to IaCGenie ("we," "our," or "us"). We are committed to protecting your privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our platform.
            </p>

            <h2>1. Information We Collect</h2>
            <p>We may collect information about you in a variety of ways. The information we may collect on the platform includes:</p>
            
            <h3>Personal Data</h3>
            <ul>
                <li><strong>Account Information:</strong> When you register for an account, we collect your name and email address.</li>
                <li><strong>Contact Information:</strong> We may collect your email to send you service-related notices.</li>
            </ul>

            <h3>Derivative and Usage Data</h3>
            <ul>
                <li><strong>Deployment Data:</strong> We collect and store information related to your infrastructure generations and deployments, including prompts, generated code files, and deployment logs. This is essential for the platform's functionality.</li>
                <li><strong>Cloud Credentials:</strong> To deploy on your behalf, we require you to provide cloud provider credentials (e.g., AWS IAM keys, GCP service account JSON). These are securely stored in an encrypted vault and are used solely for deployment actions you initiate.</li>
                <li><strong>Usage Information:</strong> We collect your IP address, browser type, operating system, and access times to monitor and improve our service.</li>
            </ul>

            <h2>2. How We Use Your Information</h2>
            <p>Having accurate information about you permits us to provide you with a smooth, efficient, and customized experience. Specifically, we may use information collected about you via the platform to:</p>
            <ul>
                <li>Create and manage your account.</li>
                <li>Generate code and perform deployments as requested.</li>
                <li>Email you regarding your account or deployments.</li>
                <li>Monitor and analyze usage and trends to improve your experience.</li>
                <li>Prevent fraudulent transactions, monitor against theft, and protect against criminal activity.</li>
                <li>Respond to product and customer service requests.</li>
            </ul>

            <h2>3. Disclosure of Your Information</h2>
            <p>We do not share your information with third parties except in the situations described below:</p>
            <ul>
                <li><strong>Third-Party Service Providers:</strong> We may share your information with third parties that perform services for us or on our behalf, including payment processing (e.g., Razorpay) and repository hosting (e.g., GitHub, GitLab), but only if you choose to connect these services.</li>
                <li><strong>By Law or to Protect Rights:</strong> If we believe the release of information about you is necessary to respond to legal process, to investigate or remedy potential violations of our policies, or to protect the rights, property, and safety of others.</li>
            </ul>

            <h2>4. Security of Your Information</h2>
            <p>
              We use administrative, technical, and physical security measures to help protect your personal information. All sensitive data, such as cloud credentials and secrets, are encrypted at rest using industry-standard encryption protocols. Access to this data is strictly limited based on the principle of least privilege.
            </p>

            <h2>5. Your Rights and Choices</h2>
            <h3>Data Access and Deletion</h3>
            <p>
              You may at any time review or change the information in your account or terminate your account. Upon your request to terminate your account, we will deactivate or delete your account and information from our active databases. However, some information may be retained in our files to prevent fraud, troubleshoot problems, assist with any investigations, and/or comply with legal requirements.
            </p>

            <h3>Cookie Policy</h3>
            <p>
                We use essential cookies to manage user sessions and authentication. We do not use third-party tracking or advertising cookies.
            </p>

            <h2>6. Contact Us</h2>
            <p>
                If you have questions or comments about this Privacy Policy, or to request access to or deletion of your data, please contact us at: <a href="mailto:privacy@iacgenie.ai">privacy@iacgenie.ai</a>.
            </p>
          </div>
        </div>
    </div>
  );
};

export default PrivacyPolicyPage;