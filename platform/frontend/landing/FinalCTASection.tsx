import React from 'react';
import Button from '../ui/Button';

interface FinalCTASectionProps {
  title?: string;
  subtitle?: string[];
  primaryCTA?: { text: string; onClick?: () => void };
  secondaryCTA?: { text: string; onClick?: () => void };
  tertiaryLink?: { text: string; href?: string };
  showToast?: (message: string, type?: 'success' | 'info' | 'warning') => void;
}

const FinalCTASection: React.FC<FinalCTASectionProps> = ({
  title = 'Ready to Transform Your Infrastructure Workflow?',
  subtitle = [
    'Start building today. No credit card required.',
    '14-day free trial on all paid plans.',
  ],
  primaryCTA = { text: 'Create Free Account', onClick: () => {} },
  secondaryCTA = { text: 'Schedule Demo →', onClick: () => {} },
  tertiaryLink = { text: 'Talk to Sales →', href: '/contact' },
  showToast,
}) => {
  const handleTryDemoClick = () => {
    if (showToast) {
      showToast('Demo coming soon', 'warning');
    }
  };

  return (
    <section className="py-20 bg-white dark:bg-slate-950 border-y border-slate-200 dark:border-slate-800">
      <div className="bg-gradient-to-br from-slate-50 to-white dark:from-slate-900/50 dark:to-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl p-12 text-center max-w-4xl mx-auto shadow-sm">
        <h2 className="text-3xl md:text-4xl font-extrabold text-slate-900 dark:text-slate-50 tracking-tight mb-6">{title}</h2>
        
        <ul className="mb-8">
          {subtitle.map((item, index) => (
            <li key={index} className="text-slate-600 dark:text-slate-400 mb-2 last:mb-0 font-medium">{item}</li>
          ))}
        </ul>
        
        <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
          <Button
            onClick={primaryCTA.onClick}
            size="lg"
            className="px-8 py-4 text-base"
          >
            {primaryCTA.text}
          </Button>
          
          {secondaryCTA && (
            <Button
              onClick={secondaryCTA.onClick}
              variant="secondary"
              size="lg"
              className="px-8 py-4 text-base"
            >
              {secondaryCTA.text}
            </Button>
          )}
        </div>
        
        <div className="mt-6">
          <button
            onClick={handleTryDemoClick}
            className="text-brand-primary hover:text-brand-primary/80 font-bold hover:underline transition-colors"
          >
            Try Interactive Demo
          </button>
        </div>
        
        {tertiaryLink && (
          <a
            href={tertiaryLink.href}
            className="text-brand-primary hover:text-orange-600 font-bold mt-6 inline-block hover:underline transition-colors"
          >
            {tertiaryLink.text}
          </a>
        )}
      </div>
    </section>
  );
};

export default FinalCTASection;
