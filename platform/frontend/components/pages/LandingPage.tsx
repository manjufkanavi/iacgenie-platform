import React, { useState, useEffect } from 'react';
import { View } from './types';
import Header from '../layout/Header';
import Footer from '../layout/Footer';
import AnimatedCodeBlock from '../landing/AnimatedCodeBlock';
import TrustLogoGrid from '../landing/TrustLogoGrid';
import HowItWorksSection from '../landing/HowItWorksSection';
import FeaturesSection from '../landing/FeaturesSection';
import ComparisonSection from '../landing/ComparisonSection';
import PricingSection from '../landing/PricingSection';
import FinalCTASection from '../landing/FinalCTASection';
import Toast from '../ui/Toast';
import Button from '../ui/Button';
import { useAppStore } from '.././store/useAppStore';

interface LandingPageProps {
  onNavigate: (view: View) => void;
}

const LandingPage: React.FC<LandingPageProps> = ({ onNavigate }) => {
  const isAuthenticated = useAppStore(state => state.isAuthenticated);
  const [toast, setToast] = useState<{ message: string; type?: 'success' | 'info' | 'warning' } | null>(null);
  const [showToast, setShowToast] = useState(false);

  useEffect(() => {
    const hash = window.location.hash;
    if (hash) {
      setTimeout(() => {
        const element = document.querySelector(hash);
        if (element) {
          element.scrollIntoView({ behavior: 'smooth' });
        }
      }, 150);
    }
  }, []);

  const showToastNotification = (message: string, type: 'success' | 'info' | 'warning' = 'info') => {
    setToast({ message, type });
    setShowToast(true);
  };

  const closeToast = () => {
    setShowToast(false);
  };

  return (
    <div className="min-h-screen bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 transition-colors duration-200">
      {/* Header/Navigation */}
      <Header onNavigate={onNavigate} isAuthenticated={isAuthenticated} />

      {/* Hero Section - Light/Dark theme matching generator page */}
      <section className="relative pt-32 pb-20 bg-gradient-to-b from-slate-50 to-white dark:from-slate-900/50 dark:to-slate-950">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold text-slate-900 dark:text-slate-50 tracking-tight mb-6">
            Build Cloud Infrastructure<br />
            at the Speed of Thought
          </h1>

          <p className="text-lg md:text-xl text-slate-600 dark:text-slate-400 max-w-3xl mx-auto mb-8 font-medium">
            Iacgenie uses AI to translate your natural language requests into production-grade
            OpenTofu, Docker & Kubernetes code in seconds. Multi-cloud support for AWS, Google Cloud & Azure.
          </p>

          {/* Interactive Code Demo */}
          <div className="mb-12">
            <AnimatedCodeBlock />
          </div>

          {/* Primary & Secondary CTAs */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-12">
            {isAuthenticated ? (
              <Button
                onClick={() => onNavigate('dashboard')}
                size="lg"
                className="px-8 py-4 text-base"
              >
                Go to Dashboard
              </Button>
            ) : (
              <Button
                onClick={() => onNavigate('signin')}
                size="lg"
                className="px-8 py-4 text-base"
              >
                Get Started Free
              </Button>
            )}

            <Button
              onClick={() => showToastNotification('Demo coming soon', 'warning')}
              variant="secondary"
              size="lg"
              className="px-8 py-4 text-base"
            >
              Watch Demo →
            </Button>
          </div>

          {/* Trust Logos */}
          <TrustLogoGrid />
        </div>
      </section>

      {/* How It Works Section */}
      <div id="how-it-works">
        <HowItWorksSection showToast={showToastNotification} />
      </div>

      {/* Features Grid Section */}
      <div id="features">
        <FeaturesSection />
      </div>

      {/* Comparison Section (Before/After) */}
      <ComparisonSection />

      {/* Pricing Section */}
      <div id="pricing">
        <PricingSection onNavigate={onNavigate} showToast={showToastNotification} />
      </div>

      {/* Final CTA Section */}
      <FinalCTASection
        showToast={showToastNotification}
        primaryCTA={
          isAuthenticated
            ? { text: 'Go to Dashboard', onClick: () => onNavigate('dashboard') }
            : { text: 'Create Free Account', onClick: () => onNavigate('signin') }
        }
      />

      {/* Footer */}
      <Footer onNavigate={onNavigate} showToast={showToastNotification} />

      {/* Toast Notification */}
      {showToast && toast && (
        <Toast
          message={toast.message}
          type={toast.type || 'info'}
          onClose={closeToast}
        />
      )}
    </div>
  );
};

export default LandingPage;

