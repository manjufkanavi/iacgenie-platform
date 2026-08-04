import React from 'react';
import { View } from './types';
import PricingCard from './PricingCard';
import { useAppStore } from '../../store/useAppStore';

interface PricingTier {
  name: string;
  price: string;
  period?: string; // 'per month', 'per user/month'
  description: string;
  features: string[];
  ctaText: string;
  ctaVariant?: 'primary' | 'outline';
  recommended?: boolean; // Highlight this tier
  onCtaClick?: () => void;
}

interface PricingSectionProps {
  onNavigate?: (view: View) => void;
  showToast?: (message: string, type?: 'success' | 'info' | 'warning') => void;
}

const PricingSection: React.FC<PricingSectionProps> = ({ onNavigate, showToast }) => {
  const isAuthenticated = useAppStore(state => state.isAuthenticated);

  const handleCtaClick = (ctaText: string) => {
    if (ctaText === 'Get Started Free' || ctaText === 'Start Free Trial') {
      if (onNavigate) {
        onNavigate(isAuthenticated ? 'dashboard' : 'signin');
      }
    } else if (ctaText === 'Contact Sales') {
      window.location.href = 'mailto:sales@iacgenie.com';
    }
  };


  const handleCompareClick = () => {
    if (showToast) {
      showToast('Coming soon', 'warning');
    }
  };

  const pricingTiers: PricingTier[] = [
    {
      name: 'Starter',
      price: 'Free',
      period: '',
      description: 'Perfect for individual developers getting started with infrastructure automation. Try Iacgenie free and see how fast you can build cloud infrastructure.',
      features: [
        'Up to 10 generations per month',
        'Single cloud provider support',
        'Basic OpenTofu generation',
        'Community support',
      ],
      ctaText: 'Get Started Free',
      ctaVariant: 'outline',
      onCtaClick: () => handleCtaClick('Get Started Free')
    },
    {
      name: 'Professional',
      price: '$49',
      period: 'per user/month',
      description: 'For teams building production infrastructure at scale. Get unlimited generations, multi-cloud support, and team collaboration features.',
      features: [
        'Unlimited generations',
        'Multi-cloud support (AWS/GCP/Azure)',
        'GitHub integration',
        'Team collaboration features',
        'Priority support',
      ],
      ctaText: 'Start Free Trial',
      ctaVariant: 'primary',
      recommended: true, // Highlight this tier
      onCtaClick: () => handleCtaClick('Start Free Trial')
    },
    {
      name: 'Enterprise',
      price: 'Custom',
      period: '',
      description: 'For organizations requiring advanced security, compliance, and dedicated support. Custom pricing with on-premise deployment options available.',
      features: [
        'Everything in Professional',
        'On-premise deployment option',
        'SSO/SAML integration',
        'Dedicated support manager',
        'Custom SLA options',
      ],
      ctaText: 'Contact Sales',
      ctaVariant: 'outline',
      onCtaClick: () => handleCtaClick('Contact Sales')
    },
  ];

  return (
    <section className="py-20 bg-white dark:bg-slate-950 border-y border-slate-200 dark:border-slate-800">
      <div className="text-center mb-12 max-w-3xl mx-auto px-4">
        <h2 className="text-3xl md:text-4xl font-extrabold text-slate-900 dark:text-slate-50 tracking-tight mb-4">Simple, Transparent Pricing</h2>
        <h3 className="text-lg text-slate-600 dark:text-slate-400 font-medium">Choose the plan that fits your needs</h3>
      </div>

      <div className="grid md:grid-cols-3 gap-8 max-w-7xl mx-auto px-4">
        {pricingTiers.map((tier, index) => (
          <PricingCard key={index} tier={tier} />
        ))}
      </div>

      <div className="text-center mt-12">
        <button
          onClick={handleCompareClick}
          className="text-brand-primary hover:text-brand-primary/80 font-bold hover:underline transition-colors"
        >
          Compare Plans →
        </button>
      </div>
    </section>
  );
};

export default PricingSection;
