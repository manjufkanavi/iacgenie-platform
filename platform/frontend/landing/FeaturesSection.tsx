import React from 'react';
import FeatureCard from './FeatureCard';

interface Feature {
  icon: React.ReactNode;
  title: string;
  description: string;
  benefits?: string[];
  color?: 'blue' | 'purple' | 'orange' | 'green';
}

const FeaturesSection: React.FC = () => {
  const features: Feature[] = [
    {
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/>
        </svg>
      ),
      title: 'Multi-Cloud Support',
      description: 'Generate infrastructure for AWS, Google Cloud Platform, and Azure from a single interface.',
      benefits: ['Unified configuration', 'No vendor lock-in', 'Multi-region deployments'],
      color: 'blue'
    },
    {
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10"/>
        </svg>
      ),
      title: 'Security & Compliance',
      description: 'Enterprise-grade security with RBAC, SOC2 compliance, and comprehensive audit logging.',
      benefits: ['Role-based access control', 'SOC2 compliant', 'Complete audit trails'],
      color: 'purple'
    },
    {
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14 2Z"/>
          <path d="M14 2v4h4"/>
          <path d="M10 9H8"/>
          <path d="M16 13H8"/>
        </svg>
      ),
      title: 'Audit & Compliance',
      description: 'Track every change with comprehensive audit logs and compliance reporting.',
      benefits: ['Immutable logs', 'Compliance reports', 'Change tracking'],
      color: 'blue'
    },
    {
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>
          <circle cx="9" cy="7" r="4"/>
          <path d="M22 21v-2a4 4 0 0 0-3-3.87"/>
          <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
        </svg>
      ),
      title: 'Team Collaboration',
      description: 'Work together with role-based permissions and project sharing.',
      benefits: ['Multi-user workspaces', 'Permission management', 'Team projects'],
      color: 'purple'
    },
    {
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="18" cy="18" r="3"/>
          <circle cx="6" cy="6" r="3"/>
          <path d="M18 6V5"/>
          <path d="M6 18v-1"/>
          <path d="m6 9 12-3"/>
          <path d="m6 15 12-3"/>
        </svg>
      ),
      title: 'GitHub Sync',
      description: 'Push generated code directly to GitHub repositories with one click.',
      benefits: ['Direct repository push', 'Branch management', 'Pull request integration'],
      color: 'orange'
    },
    {
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="m18 16 4-4-4-4"/>
          <path d="m6 8-4 4 4 4"/>
          <path d="m14.5 4-5 16"/>
        </svg>
      ),
      title: 'Webhooks & Integrations',
      description: 'Connect with your existing tools through webhooks and API integrations.',
      benefits: ['Custom webhooks', 'CI/CD integration', 'Event notifications'],
      color: 'purple'
    },
  ];

  return (
    <section className="py-20 bg-white dark:bg-slate-950 border-y border-slate-200 dark:border-slate-800">
      <div className="text-center mb-12 max-w-3xl mx-auto px-4">
        <h2 className="text-3xl md:text-4xl font-extrabold text-slate-900 dark:text-slate-50 tracking-tight mb-4">Enterprise-Grade Features</h2>
        <h3 className="text-lg text-slate-600 dark:text-slate-400 font-medium">Everything you need to build, deploy & manage infrastructure at scale</h3>
      </div>

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-7xl mx-auto px-4">
        {features.map((feature, index) => (
          <FeatureCard key={index} {...feature} />
        ))}
      </div>
    </section>
  );
};

export default FeaturesSection;