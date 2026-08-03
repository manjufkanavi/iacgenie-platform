
import React from 'react';

const TermsOfServicePage: React.FC = () => {
    return (
        <div className="bg-white dark:bg-slate-950 py-16 sm:py-24 text-gray-900 dark:text-slate-100 transition-colors duration-200">
            <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="mb-8 text-center">
                    <h1 className="text-4xl font-extrabold text-gray-900 dark:text-white sm:text-5xl">Terms of Service</h1>
                    <p className="mt-2 text-gray-600 dark:text-slate-400">Last Updated: October 27, 2023</p>
                </div>

                <div className="prose prose-lg max-w-none space-y-6 text-gray-700 dark:text-slate-300
                                prose-h2:text-gray-900 dark:prose-h2:text-white prose-h2:font-bold prose-h2:text-2xl
                                prose-h3:text-brand-primary prose-h3:font-semibold prose-h3:text-xl
                                prose-a:text-brand-primary hover:prose-a:text-brand-primary/80
                                prose-strong:text-gray-900 dark:prose-strong:text-white">
                    <p>
                        Please read these Terms of Service ("Terms", "Terms of Service") carefully before using the IaCGenie website and services (the "Service") operated by IaCGenie Inc. ("us", "we", or "our").
                    </p>

                    <h2>1. Agreement to Terms</h2>
                    <p>
                        By using our Service, you agree to be bound by these Terms. If you disagree with any part of the terms, then you may not access the Service.
                    </p>

                    <h2>2. Accounts</h2>
                    <p>
                        When you create an account with us, you must provide us information that is accurate, complete, and current at all times. Failure to do so constitutes a breach of the Terms, which may result in immediate termination of your account on our Service.
                    </p>

                    <h2>3. Acceptable Use</h2>
                    <p>
                        You agree not to use the Service for any purpose that is illegal or prohibited by these Terms. You agree not to use the Service in any manner that could damage, disable, overburden, or impair the Service. Refer to our Acceptable Use Policy for more details.
                    </p>

                    <h2>4. Intellectual Property</h2>
                    <p>
                        The Service and its original content (excluding content provided by users), features, and functionality are and will remain the exclusive property of IaCGenie Inc. and its licensors.
                    </p>

                    <h2>5. Termination</h2>
                    <p>
                        We may terminate or suspend your account immediately, without prior notice or liability, for any reason whatsoever, including without limitation if you breach the Terms.
                    </p>
                    
                    <h2>6. Limitation of Liability</h2>
                    <p>
                        In no event shall IaCGenie Inc., nor its directors, employees, partners, agents, suppliers, or affiliates, be liable for any indirect, incidental, special, consequential or punitive damages, including without limitation, loss of profits, data, use, goodwill, or other intangible losses, resulting from your access to or use of or inability to access or use the Service.
                    </p>

                    <h2>7. Changes to Terms</h2>
                    <p>
                        We reserve the right, at our sole discretion, to modify or replace these Terms at any time. We will try to provide at least 30 days' notice prior to any new terms taking effect.
                    </p>

                    <h2>8. Contact Us</h2>
                    <p>
                        If you have any questions about these Terms, please contact us at <a href="mailto:legal@iacgenie.ai">legal@iacgenie.ai</a>.
                    </p>
                </div>
            </div>
        </div>
    );
};

export default TermsOfServicePage;