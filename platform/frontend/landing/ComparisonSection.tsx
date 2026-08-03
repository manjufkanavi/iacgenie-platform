import React from 'react';

interface ComparisonItem {
  before: string;
  after: string;
}

const ComparisonSection: React.FC = () => {
  const comparisons: ComparisonItem[] = [
    { before: 'Manual OpenTofu writing', after: 'Natural language input' },
    { before: '4-6 hours setup time', after: '30 seconds to generate' },
    { before: 'Multiple tools switching', after: 'One unified interface' },
    { before: 'Error-prone configurations', after: 'AI-validated code' },
    { before: 'No collaboration features', after: 'Team collaboration built-in' },
  ];

  return (
    <section className="py-20 bg-white dark:bg-slate-950 border-y border-slate-200 dark:border-slate-800">
      <div className="text-center mb-12 max-w-3xl mx-auto px-4">
        <h2 className="text-3xl md:text-4xl font-extrabold text-slate-900 dark:text-slate-50 tracking-tight mb-4">See The Difference</h2>
        <h3 className="text-lg text-slate-600 dark:text-slate-400 font-medium">How Iacgenie transforms your workflow</h3>
      </div>

      <div className="grid md:grid-cols-2 gap-8 max-w-5xl mx-auto px-4">
        {/* Before Column */}
        <div className="bg-white dark:bg-slate-800 border-l-4 border-l-slate-400 dark:border-l-slate-500 border border-slate-200 dark:border-slate-700 rounded-xl p-6 shadow-sm">
          <h3 className="text-xl font-bold text-slate-700 dark:text-slate-300 mb-6">Before Iacgenie</h3>
          <ul className="space-y-0">
            {comparisons.map((comp, index) => (
              <li key={index} className="flex items-start gap-3 py-4 border-b border-slate-200 dark:border-slate-700 last:border-0">
                <span className="font-bold text-xs uppercase tracking-wide flex-shrink-0 w-24 text-slate-400 dark:text-slate-500">BEFORE</span>
                <span className="flex-1 text-slate-600 dark:text-slate-300 font-medium text-sm">{comp.before}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* After Column */}
        <div className="bg-white dark:bg-slate-800 border-r-4 border-r-green-500 dark:border-r-green-600 border border-slate-200 dark:border-slate-700 rounded-xl p-6 shadow-sm">
          <h3 className="text-xl font-bold text-slate-800 dark:text-slate-100 mb-6">With Iacgenie</h3>
          <ul className="space-y-0">
            {comparisons.map((comp, index) => (
              <li key={index} className="flex items-start gap-3 py-4 border-b border-slate-200 dark:border-slate-700 last:border-0">
                <span className="font-bold text-xs uppercase tracking-wide flex-shrink-0 w-24 text-green-600 dark:text-green-400">AFTER</span>
                <span className="flex-1 text-slate-700 dark:text-slate-200 font-medium text-sm">{comp.after}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
};

export default ComparisonSection;