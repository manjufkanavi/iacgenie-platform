import React from 'react';
import Button from '../ui/Button';

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

interface PricingCardProps {
  tier: PricingTier;
}

const PricingCard: React.FC<PricingCardProps> = ({ tier }) => {
  const handleCtaClick = () => {
    if (tier.onCtaClick) {
      tier.onCtaClick();
    }
  };

  return (
    <div className={`bg-white dark:bg-slate-800 border ${tier.recommended ? 'border-brand-primary shadow-xl scale-105 z-10' : 'border-slate-200 dark:border-slate-700'} rounded-xl p-8 hover:border-slate-350 dark:hover:border-slate-500 hover:shadow-xl transition-all duration-300 flex flex-col`}>
      {tier.recommended && (
        <div className="-mt-12 mb-4">
          <span className="bg-brand-primary text-white text-xs font-extrabold uppercase tracking-wider px-3 py-1.5 rounded-full inline-block shadow-sm">
            Most Popular
          </span>
        </div>
      )}
      
      <h3 className="text-2xl font-bold text-slate-900 dark:text-slate-50 mb-2">{tier.name}</h3>
      <div className="flex items-baseline gap-2 mb-4">
        <span className="text-4xl font-extrabold text-slate-900 dark:text-slate-50">{tier.price}</span>
        {tier.period && (
          <span className="text-slate-500 dark:text-slate-400 text-sm font-medium">{tier.period}</span>
        )}
      </div>
      
      <p className="text-slate-600 dark:text-slate-400 mb-6 font-medium leading-relaxed">{tier.description}</p>
      
      <ul className="space-y-3 mb-8 flex-1">
        {tier.features.map((feature, index) => (
          <li key={index} className="flex items-start gap-2 text-slate-600 dark:text-slate-400 font-medium">
            <span className="text-green-500 mt-1 flex-shrink-0">✓</span>
            <span className="mt-0.5">{feature}</span>
          </li>
        ))}
      </ul>
      
      <div className="mt-auto pt-6 border-t border-slate-200 dark:border-slate-700">
        <Button
          onClick={handleCtaClick}
          variant={tier.ctaVariant === 'primary' ? 'primary' : 'secondary'}
          size="lg"
          className="w-full"
        >
          {tier.ctaText}
        </Button>
      </div>
    </div>
  );
};

export default PricingCard;
