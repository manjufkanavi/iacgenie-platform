import React from 'react';

interface Step {
  number: number;
  title: string;
  subtitle: string[];
  description: string;
  icon: React.ReactNode;
  color: 'blue' | 'purple' | 'orange';
}

interface HowItWorksSectionProps {
  showToast?: (message: string, type?: 'success' | 'info' | 'warning') => void;
}

const HowItWorksSection: React.FC<HowItWorksSectionProps> = ({ showToast }) => {
  const steps: Step[] = [
    {
      number: 1,
      title: 'Describe',
      subtitle: ['Natural Language'],
      description: 'Enter your infrastructure requirements in plain English. Describe what you need, not how to build it.',
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
        </svg>
      ),
      color: 'blue',
    },
    {
      number: 2,
      title: 'Generate',
      subtitle: ['AI Analysis & Validation'],
      description: 'Our AI analyzes your request and generates production-ready OpenTofu, Docker & Kubernetes code with built-in validation.',
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 3a9 9 0 1 0 9 9"/>
          <path d="M12 3v6"/>
          <path d="M12 15h6"/>
        </svg>
      ),
      color: 'purple',
    },
    {
      number: 3,
      title: 'Deploy',
      subtitle: ['One-Click Deployment'],
      description: 'Review the generated code, simulate deployments with OpenTofu plan/apply, and push directly to GitHub.',
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.33-.04-3.84l-1.5-1.5c-1.5-1.56-3-1.56-3.84-.04z"/>
          <path d="m12 15 2.5-2.5"/>
          <path d="m15 12 2.5-2.5"/>
          <path d="M12 3v9"/>
          <path d="M3 12h9"/>
        </svg>
      ),
      color: 'orange',
    },
  ];

  const stepColorClasses = {
    blue: 'bg-blue-500/20 text-blue-500 group-hover:bg-blue-500/30',
    purple: 'bg-purple-500/20 text-purple-500 group-hover:bg-purple-500/30',
    orange: 'bg-brand-primary/20 text-brand-primary group-hover:bg-brand-primary/30',
  };

  return (
    <section className="py-20 bg-white border-y border-gray-200">
      <div className="text-center mb-16 max-w-3xl mx-auto px-4">
        <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">How Iacgenie Works</h2>
        <h3 className="text-lg text-gray-600">From idea to infrastructure in 3 steps</h3>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-7xl mx-auto px-4">
        {steps.map((step) => (
          <div
            key={step.number}
            className="bg-white border border-gray-200 rounded-xl p-6 hover:border-slate-300 dark:hover:border-slate-500 transition-all duration-300 hover:-translate-y-2 hover:shadow-xl group flex flex-col items-center text-center"
          >
            <div className="text-4xl font-bold text-gray-400 mb-2">{step.number}</div>
            
            <div className={`h-16 w-16 rounded-lg ${stepColorClasses[step.color]} flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300`}>
              {step.icon}
            </div>

            <h3 className="text-xl font-semibold text-gray-900 mb-2">{step.title}</h3>
            {step.subtitle.map((sub, i) => (
              <p key={i} className="text-sm text-gray-500 mb-2">{sub}</p>
            ))}
            <p className="text-gray-600 leading-relaxed flex-1">{step.description}</p>
          </div>
        ))}
      </div>

      <div className="mt-12 text-center">
        <button
          onClick={() => showToast?.('Demo coming soon', 'warning')}
          className="text-brand-primary hover:text-brand-primary/80 font-semibold inline-flex items-center gap-2"
        >
          Try Interactive Demo →
        </button>
      </div>
    </section>
  );
};

export default HowItWorksSection;