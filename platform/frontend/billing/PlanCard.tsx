import React from 'react';
import Card from '../ui/Card';
import Button from '../ui/Button';
import { Plan } from '../../types';

interface PlanCardProps {
  plan: Plan;
  description: string;
  features: string[];
  price: string;
  cta: string;
  currentPlan: Plan;
  onUpgrade?: () => void;
  disabled?: boolean;
}

const PlanCard: React.FC<PlanCardProps> = ({
  plan,
  description,
  features,
  price,
  cta,
  currentPlan,
  onUpgrade,
  disabled = false,
}) => {
  const isCurrent = plan === currentPlan;

  return (
    <Card
      className={`flex flex-col relative overflow-hidden transition-all duration-350 transform hover:-translate-y-1 hover:shadow-2xl ${
        isCurrent
          ? 'border-orange-500 ring-2 ring-orange-500 ring-offset-2'
          : 'border-gray-200 hover:border-orange-200'
      }`}
      data-testid={`plan-card-${plan.toLowerCase()}`}
    >
      {isCurrent && (
        <div className="absolute top-0 right-0 bg-orange-500 text-white text-[10px] font-black uppercase tracking-wider px-3 py-1 rounded-bl-xl shadow-md">
          Current Plan
        </div>
      )}

      <div className="flex-1 p-6 sm:p-8">
        <h3 className="text-2xl font-black text-gray-900 mb-1">{plan}</h3>
        <p className="text-sm font-semibold text-gray-500 mb-6">{description}</p>
        
        <div className="flex items-baseline mb-8">
          <span className="text-4xl font-extrabold text-gray-900 tracking-tight">{price}</span>
          {price !== 'Free' && <span className="text-gray-400 font-semibold ml-2">/ month</span>}
        </div>

        {/* Features Checklist */}
        <ul className="space-y-4 border-t border-gray-100 pt-6">
          {features.map((feature, i) => (
            <li key={i} className="flex items-start">
              <div className="flex-shrink-0 mt-0.5">
                <svg className="h-5 w-5 text-green-500 font-bold bg-green-50 rounded-full p-0.5 border border-green-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <p className="ml-3 text-sm font-semibold text-gray-600">{feature}</p>
            </li>
          ))}
        </ul>
      </div>

      <div className="p-6 sm:p-8 pt-0 mt-auto">
        <Button
          size="lg"
          variant={isCurrent ? 'secondary' : 'primary'}
          className={`w-full font-bold shadow-lg py-3.5 transition-all ${
            isCurrent
              ? 'bg-gray-100 text-gray-500 border-0 cursor-default'
              : 'bg-gradient-to-r from-orange-500 to-red-500 text-white hover:from-orange-600 hover:to-red-600 border-0 transform hover:-translate-y-0.5'
          }`}
          onClick={onUpgrade}
          disabled={isCurrent || disabled}
          data-testid={`plan-cta-${plan.toLowerCase()}`}
        >
          {isCurrent ? 'Active Plan' : cta}
        </Button>
      </div>
    </Card>
  );
};

export default PlanCard;
