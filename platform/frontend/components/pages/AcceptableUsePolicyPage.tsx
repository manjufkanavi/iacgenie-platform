
import React from 'react';

const AcceptableUsePolicyPage: React.FC = () => {
    return (
        <div className="bg-white dark:bg-slate-950 py-16 sm:py-24 text-gray-900 dark:text-slate-100 transition-colors duration-200">
            <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="mb-8 text-center">
                    <h1 className="text-4xl font-extrabold text-gray-900 dark:text-white sm:text-5xl">Acceptable Use Policy</h1>
                    <p className="mt-2 text-gray-600 dark:text-slate-400">Last Updated: October 27, 2023</p>
                </div>

                <div className="prose prose-lg max-w-none space-y-6 text-gray-700 dark:text-slate-300
                                prose-h2:text-gray-900 dark:prose-h2:text-white prose-h2:font-bold prose-h2:text-2xl
                                prose-p:leading-relaxed
                                prose-ul:list-disc prose-ul:pl-6 prose-li:my-1
                                prose-a:text-brand-primary hover:prose-a:text-brand-primary/80
                                ">
                    <p>
                        This Acceptable Use Policy ("AUP") outlines the rules and guidelines for using the iacgenie platform ("Service"). This policy is designed to protect our Service, our users, and the wider community from harm and abuse. By using our Service, you agree to this AUP.
                    </p>
                    
                    <h2>Prohibited Activities</h2>
                    <p>
                        Users of iacgenie may not engage in the following activities:
                    </p>
                    <ul>
                        <li>
                            <strong>Illegal Activities:</strong> Using the Service to conduct, promote, or facilitate any illegal activity.
                        </li>
                        <li>
                            <strong>Malicious Content:</strong> Generating, storing, or deploying code that contains viruses, malware, trojans, or any other harmful or destructive content.
                        </li>
                        <li>
                            <strong>Security Violations:</strong> Attempting to violate the security of the Service or any other network, computer, or communications system. This includes, but is not limited to, unauthorized access, vulnerability scanning, or penetration testing.
                        </li>
                        <li>
                            <strong>Denial of Service (DoS):</strong> Using the Service to execute or be the target of a denial of service attack.
                        </li>
                        <li>
                            <strong>Resource Abuse:</strong> Consuming an excessive amount of system resources, such as CPU, memory, or network bandwidth, that disrupts the service for other users. This includes automated or scripted behavior intended to overuse the platform's generation or deployment capabilities beyond reasonable limits.
                        </li>
                        <li>
                            <strong>Spam and Unsolicited Messages:</strong> Using the Service to send spam or other unsolicited commercial messages.
                        </li>
                        <li>
                            <strong>Resale of Service:</strong> Reselling or redistributing the Service without our express written permission.
                        </li>
                    </ul>

                    <h2>Enforcement</h2>
                    <p>
                        We reserve the right to investigate any violation of this AUP. We may, at our sole discretion, suspend or terminate access to the Service for users who violate this policy. We may also report any illegal activities to law enforcement authorities.
                    </p>

                    <h2>Reporting Violations</h2>
                    <p>
                        To report a violation of this AUP, please contact us at <a href="mailto:abuse@iacgenie.ai">abuse@iacgenie.ai</a>.
                    </p>
                </div>
            </div>
        </div>
    );
};

export default AcceptableUsePolicyPage;