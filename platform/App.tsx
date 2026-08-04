import React, { Suspense } from 'react';
import GeneratorUI from './GeneratorUI';
import { Toaster } from 'react-hot-toast';

const App: React.FC = () => {
  return (
    <div className="min-h-screen bg-slate-900 text-slate-300">
      <Suspense fallback={<div className="p-8 text-center">Loading...</div>}>
        <Toaster position="top-right" />
        <GeneratorUI />
      </Suspense>
    </div>
  );
};

export default App;
