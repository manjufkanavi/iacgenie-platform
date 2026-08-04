import React, { Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import GeneratorUI from './GeneratorUI';

// ─── Landing Page (unauthenticated) ────────────────────────────────
const LandingPage: React.FC = () => {
  const { isAuthenticated, navigate } = React.useMemo(
    () => ({
      isAuthenticated:
        localStorage.getItem('iacgenie_token') !== null,
      navigate: (view: string) => {
        window.location.href = view;
      },
    }),
    []
  );

  if (isAuthenticated) {
    return <Navigate to="/generator" replace />;
  }

  return (
    <div className="min-h-screen bg-slate-900 text-slate-300 flex flex-col">
      {/* Hero */}
      <div className="flex-1 flex flex-col items-center justify-center px-4 py-20 text-center">
        <h1 className="text-5xl font-bold text-white mb-6">
          IacGenie AI
        </h1>
        <p className="text-xl text-slate-400 mb-8 max-w-2xl">
          Build cloud infrastructure at the speed of thought. Turn
          natural language into production-ready Terraform, Docker &
          Kubernetes code in seconds.
        </p>
        <div className="flex gap-4">
          <button
            onClick={() => navigate('/signin')}
            className="px-8 py-3 bg-orange-500 hover:bg-orange-600 text-white rounded-lg font-semibold transition"
          >
            Sign In
          </button>
          <button
            onClick={() => navigate('/signup')}
            className="px-8 py-3 bg-slate-700 hover:bg-slate-600 text-white rounded-lg font-semibold transition"
          >
            Sign Up
          </button>
        </div>
      </div>

      {/* Footer */}
      <footer className="text-center py-6 text-slate-500 text-sm">
        &copy; {new Date().getFullYear()} IacGenie AI. All rights reserved.
      </footer>
    </div>
  );
};

// ─── Authenticated App ─────────────────────────────────────────────
const AuthenticatedApp: React.FC = () => {
  return (
    <div className="min-h-screen bg-slate-900 text-slate-300">
      <Suspense fallback={<div className="p-8 text-center">Loading...</div>}>
        <Toaster position="top-right" />
        <GeneratorUI />
      </Suspense>
    </div>
  );
};

// ─── Root App ──────────────────────────────────────────────────────
const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/signin" element={<LandingPage />} />
        <Route path="/signup" element={<LandingPage />} />
        <Route path="/generator" element={<AuthenticatedApp />} />
        <Route path="/settings" element={<AuthenticatedApp />} />
        <Route path="/dashboard" element={<AuthenticatedApp />} />
        <Route path="/deployments" element={<AuthenticatedApp />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
