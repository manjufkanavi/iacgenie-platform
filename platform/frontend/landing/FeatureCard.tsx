import React from 'react';

interface FeatureCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  benefits?: string[];
  color?: 'blue' | 'purple' | 'orange' | 'green';
}

const FeatureCard: React.FC<FeatureCardProps> = ({ 
  icon, 
  title, 
  description, 
  benefits,
  color = 'blue',
}) => {
  const colorClasses = {
    blue: 'bg-blue-500/20 text-blue-500 group-hover:bg-blue-500/30 dark:bg-blue-500/30 dark:text-blue-400 dark:group-hover:bg-blue-500/40',
    purple: 'bg-purple-500/20 text-purple-500 group-hover:bg-purple-500/30 dark:bg-purple-500/30 dark:text-purple-400 dark:group-hover:bg-purple-500/40',
    orange: 'bg-brand-primary/20 text-brand-primary group-hover:bg-brand-primary/30 dark:bg-brand-primary/30 dark:text-orange-400 dark:group-hover:bg-brand-primary/40',
    green: 'bg-green-500/20 text-green-500 group-hover:bg-green-500/30 dark:bg-green-500/30 dark:text-green-400 dark:group-hover:bg-green-500/40',
  };

  return (
    <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 hover:border-slate-350 dark:hover:border-slate-500 shadow-sm hover:shadow-xl hover:-translate-y-2 transition-all duration-300 group">
      <div className={`h-12 w-12 rounded-lg ${colorClasses[color]} flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300`}>
        {icon}
      </div>
      
      <h3 className="text-xl font-semibold text-slate-900 dark:text-slate-50 mb-3">{title}</h3>
      <p className="text-slate-600 dark:text-slate-400 leading-relaxed mb-4">{description}</p>
      
      {benefits && benefits.length > 0 && (
        <ul className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700">
          {benefits.map((benefit, index) => (
            <li key={index} className="flex items-start gap-2 text-sm text-slate-600 dark:text-slate-400">
              <span className="text-green-500 mt-1 flex-shrink-0">✓</span>
              <span className="mt-0.5">{benefit}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default FeatureCard;