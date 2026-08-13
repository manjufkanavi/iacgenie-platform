import React, { useEffect, useState } from 'react';
import { BrowserRouter, Route, Routes, Navigate } from 'react-router-dom';
import GeneratorUI from './GeneratorUI';
import LayoutShell from './layout/LayoutShell';
import Header from './layout/Header';
import Footer from './layout/Footer';
import Toast from './ui/Toast';
import AboutUsPage from './pages/AboutUsPage';
import DashboardPage from './pages/DashboardPage';
import DeploymentsPage from './pages/DeploymentsPage';
import DocsPage from './pages/DocsPage';
import PrivacyPolicyPage from './pages/PrivacyPolicyPage';
import SettingsPage from './pages/SettingsPage';
import { View } from './types';

// New page imports
import AcceptableUsePolicyPage from './pages/AcceptableUsePolicyPage';
import AuditLogPage from './pages/AuditLogPage';
import BillingPage from './pages/BillingPage';
import VerifyOtpPage from './pages/VerifyOtpPage';
import ContactUsPage from './pages/ContactUsPage';
import DeveloperSettingsPage from './pages/DeveloperSettingsPage';
import ForgotPasswordPage from './pages/ForgotPasswordPage';
import HumanReviewQueuePage from './pages/HumanReviewQueuePage';
import LandingPage from './pages/LandingPage';
import SignInPage from './pages/SignInPage';
import SignUpPage from './pages/SignUpPage';
import SwaggerPage from './pages/SwaggerPage';
import TermsOfServicePage from './pages/TermsOfServicePage';
import UsageAnalyticsPage from './pages/UsageAnalyticsPage';
import TeamManagementPage from './pages/TeamManagementPage';
import VerifyEmailPage from './pages/VerifyEmailPage';
import ResetPasswordPage from './pages/ResetPasswordPage';
import PipelineDashboardPage from './pages/PipelineDashboardPage';
import PipelineDetailView from './pages/PipelineDetailView';
import ClarifyAgentPanel from './pipeline/ClarifyAgentPanel';
import AppErrorBoundary from './common/AppErrorBoundary';
import MonacoWorkspacePanel from './ui/MonacoWorkspacePanel';
import { localAuthService } from './services/localAuthService';
import { useAppStore } from './store/useAppStore';
import { ProtectedRoute, PublicOnlyRoute } from './auth/ProtectedRoute';
import { usePipelineStore } from './store/usePipelineStore';

import { useLocation } from 'react-router-dom';

// Component to sync React Router location changes with Zustand store
const LocationSyncer: React.FC = () => {
  const location = useLocation();
  const currentView = useAppStore(state => state.currentView);
  const setCurrentView = useAppStore(state => state.setCurrentView);

  useEffect(() => {
    const pathToView: Record<string, View> = {
      '/': 'landing',
      '/signin': 'signin',
      '/signup': 'signup',
      '/forgot-password': 'forgot-password',
      '/reset-password': 'reset-password',
      '/dashboard': 'dashboard',
      '/generator': 'generator',
      '/deployments': 'deployments',
      '/settings': 'settings',
      '/developer': 'developer',
      '/billing': 'billing',
      '/audit-log': 'audit-log',
      '/docs': 'docs',
      '/api-docs': 'api-docs',
      '/about': 'about',
      '/privacy': 'privacy',
      '/terms': 'terms',
      '/contact': 'contact',
      '/aup': 'aup',
      '/human-review': 'human-review',
      '/usage-analytics': 'usage-analytics',
      '/team-members': 'team-members',
      '/workspace-manager': 'workspace-manager',
      // Pipeline agentic loop routes
      '/pipelines': 'pipeline-dashboard',
      '/pipelines/new': 'clarify-agent',
      '/pipelines/:id/generate': 'generator-agent',
      '/pipelines/:id/static-analysis': 'static-analysis',
      '/pipelines/:id/plan-review': 'plan-review',
      '/pipelines/:id/apply-review': 'apply-review',
      '/pipelines/:id/escalation': 'escalation-handler',
      '/pipelines/:id/sessions': 'session-manager',
    };
    
    // For parameterized routes like /pipelines/:id, we need basic matching
    let view = pathToView[location.pathname];
    if (!view) {
      if (location.pathname.startsWith('/pipelines/')) {
        if (location.pathname.endsWith('/generate')) {
          view = 'generator-agent';
        } else if (location.pathname.endsWith('/static-analysis')) {
          view = 'static-analysis';
        } else if (location.pathname.endsWith('/plan-review')) {
          view = 'plan-review';
        } else if (location.pathname.endsWith('/apply-review')) {
          view = 'apply-review';
        } else if (location.pathname.endsWith('/escalation')) {
          view = 'escalation-handler';
        } else if (location.pathname.endsWith('/sessions')) {
          view = 'session-manager';
        } else {
          view = 'pipeline-detail';
        }
      }
    }
    
    if (view && view !== currentView) {
      setCurrentView(view);
    }
  }, [location.pathname, currentView, setCurrentView]);

  return null;
};

const PublicLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const isAuthenticated = useAppStore(state => state.isAuthenticated);
  const [toast, setToast] = useState<{ message: string; type?: 'success' | 'info' | 'warning' } | null>(null);
  const [showToast, setShowToast] = useState(false);

  const handleNavigate = (view: View) => {
    const pathMap: Record<View, string> = {
      'landing': '/',
      'signin': '/signin',
      'signup': '/signup',
      'forgot-password': '/forgot-password',
      'dashboard': '/dashboard',
      'generator': '/generator',
      'deployments': '/deployments',
      'settings': '/settings',
      'developer': '/developer',
      'billing': '/billing',
      'audit-log': '/audit-log',
      'docs': '/docs',
      'api-docs': '/api-docs',
      'about': '/about',
      'privacy': '/privacy',
      'terms': '/terms',
      'contact': '/contact',
      'aup': '/aup',
      'human-review': '/human-review',
      'usage-analytics': '/usage-analytics',
      'team-members': '/team-members',
      'pipeline-dashboard': '/pipelines',
      'clarify-agent': '/pipelines/new',
      'generator-agent': '/pipelines/:id/generate',
      'static-analysis': '/pipelines/:id/static-analysis',
      'plan-review': '/pipelines/:id/plan-review',
      'apply-review': '/pipelines/:id/apply-review',
      'escalation-handler': '/pipelines/:id/escalation',
      'session-manager': '/pipelines/:id/sessions',
      'reset-password': '/reset-password',
      'pipeline-detail': '/pipelines/:id',
      'workspace-manager': '/workspace-manager',
      'agent-configuration': '/agent-configuration',
    };
    
    let path = pathMap[view];
    if (path) {
      if (path.includes('/:id')) {
        const activePipeline = usePipelineStore.getState().activePipeline;
        if (activePipeline?.id) {
          path = path.replace('/:id', `/${activePipeline.id}`);
        } else {
          path = '/pipelines';
        }
      }
      window.location.href = path;
    }
  };

  const showToastNotification = (message: string, type: 'success' | 'info' | 'warning' = 'info') => {
    setToast({ message, type });
    setShowToast(true);
  };

  const closeToast = () => {
    setShowToast(false);
  };

  return (
    <div className="min-h-screen flex flex-col bg-white dark:bg-slate-950 text-gray-900 dark:text-slate-100 transition-colors duration-200">
      <Header onNavigate={handleNavigate} isAuthenticated={isAuthenticated} />
      <main className="flex-grow pt-20">
        {children}
      </main>
      <Footer onNavigate={handleNavigate} showToast={showToastNotification} />
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

const App: React.FC = () => {
  const { isAuthenticated, currentView, signIn, initializeAuth } = useAppStore();
  const [isInitialized, setIsInitialized] = useState(false);
  
  // Sync browser URL changes with Zustand store (now handled by LocationSyncer component)

  useEffect(() => {
    // 🔧 FIX: Initialize authentication state from localStorage on app startup
    const initializeApp = async () => {
      try {
        // First, try to restore auth state from localStorage
        initializeAuth();
        // Then check for existing authentication via localAuthService
        const user = localAuthService.getCurrentUser();
        if (user) {
          signIn(user);
        }
      } catch (error) {
        console.error('Failed to initialize authentication:', error);
        // Clear any invalid auth data
        await localAuthService.logout();
      } finally {
        setIsInitialized(true);
      }
    };
    initializeApp();
  }, [signIn, initializeAuth]);

  useEffect(() => {
    // On view change, update the document title for better browser history
    const viewTitles: Record<View, string> = {
      'landing': 'Welcome',
      'signin': 'Sign In',
      'signup': 'Sign Up',
      'forgot-password': 'Forgot Password',
      'dashboard': 'Dashboard',
      'generator': 'Generator',
      'deployments': 'Deployments',
      'settings': 'Project Settings',
      'developer': 'Developer Settings',
      'billing': 'Billing',
      'audit-log': 'Audit Log',
      'docs': 'Documentation',
      'api-docs': 'API Reference',
      'about': 'About Us',
      'privacy': 'Privacy Policy',
      'terms': 'Terms of Service',
      'contact': 'Contact Us',
      'aup': 'Acceptable Use Policy',
      'human-review': 'Human Review Queue',
      'usage-analytics': 'Usage Analytics',
      'team-members': 'Team Members',
      // Pipeline agentic loop views
      'pipeline-dashboard': 'Pipeline Dashboard',
      'clarify-agent': 'Clarify Agent',
      'generator-agent': 'Generator Agent',
      'static-analysis': 'Static Analysis',
      'plan-review': 'Plan Review',
      'apply-review': 'Apply Review',
      'escalation-handler': 'Escalation Handler',
      'session-manager': 'Session Manager',
      'reset-password': 'Reset Password',
      'pipeline-detail': 'Pipeline Detail',
      'workspace-manager': 'Workspace Manager',
      'agent-configuration': 'Agent Configuration',
    };
    document.title = `${viewTitles[currentView] || 'App'} - Iacgenie AI`;
  }, [currentView]);

  const handleSignIn = async (user: any) => {
    try {
      signIn(user);
    } catch (err: any) {
      console.error('Login error:', err);
    }
  };

  const handleNavigate = (view: View) => {
    // Use window.location to update URL - Router handles the routing
    const pathMap: Record<View, string> = {
      'landing': '/',
      'signin': '/signin',
      'signup': '/signup',
      'forgot-password': '/forgot-password',
      'dashboard': '/dashboard',
      'generator': '/generator',
      'deployments': '/deployments',
      'settings': '/settings',
      'developer': '/developer',
      'billing': '/billing',
      'audit-log': '/audit-log',
      'docs': '/docs',
      'api-docs': '/api-docs',
      'about': '/about',
      'privacy': '/privacy',
      'terms': '/terms',
      'contact': '/contact',
      'aup': '/aup',
      'human-review': '/human-review',
      'usage-analytics': '/usage-analytics',
      'team-members': '/team-members',
      // Pipeline agentic loop paths
      'pipeline-dashboard': '/pipelines',
      'clarify-agent': '/pipelines/new',
      'generator-agent': '/pipelines/:id/generate',
      'static-analysis': '/pipelines/:id/static-analysis',
      'plan-review': '/pipelines/:id/plan-review',
      'apply-review': '/pipelines/:id/apply-review',
      'escalation-handler': '/pipelines/:id/escalation',
      'session-manager': '/pipelines/:id/sessions',
      'reset-password': '/reset-password',
      'pipeline-detail': '/pipelines/:id',
      'workspace-manager': '/workspace-manager',
      'agent-configuration': '/agent-configuration',
    };
    
    let path = pathMap[view];
    if (path) {
      if (path.includes('/:id')) {
        const activePipeline = usePipelineStore.getState().activePipeline;
        if (activePipeline?.id) {
          path = path.replace('/:id', `/${activePipeline.id}`);
        } else {
          path = '/pipelines';
        }
      }
      window.location.href = path;
    }
  };

  const renderDashboardLayout = () => (
    <LayoutShell>
      {renderContent()}
    </LayoutShell>
  );

  const renderContent = () => {
    switch (currentView) {
      // Public pages
      case 'landing': return <LandingPage onNavigate={handleNavigate} />;
      case 'signin': return <SignInPage onSignIn={handleSignIn} onNavigate={handleNavigate} />;
      case 'signup': return <SignUpPage onNavigate={handleNavigate} />;
      case 'forgot-password': return <ForgotPasswordPage onNavigate={handleNavigate} />;
      case 'reset-password': return <ResetPasswordPage onNavigate={handleNavigate} />;
      case 'about': return <AboutUsPage />;
      case 'privacy': return <PrivacyPolicyPage />;
      case 'terms': return <TermsOfServicePage />;
      case 'contact': return <ContactUsPage />;
      case 'aup': return <AcceptableUsePolicyPage />;
      case 'docs': return <DocsPage />;
      case 'api-docs': return <SwaggerPage />;
      // Authenticated pages - Pages that don't require onNavigate prop
      case 'dashboard': return <DashboardPage />;
      case 'generator': return <GeneratorUI />;
      case 'deployments': return <DeploymentsPage />;
      case 'settings': return <SettingsPage />;
      case 'developer': return <DeveloperSettingsPage />;
      case 'billing': return <BillingPage />;
      case 'audit-log': return <AuditLogPage />;
      case 'human-review': return <HumanReviewQueuePage />;
      case 'usage-analytics': return <UsageAnalyticsPage />;
      case 'team-members': return <TeamManagementPage />;
      // Pipeline agentic loop pages (placeholder - to be implemented)
      case 'pipeline-dashboard': return <PipelineDashboardPage />;
      case 'clarify-agent': return <ClarifyAgentPanel />;
      case 'generator-agent': return <PipelineDetailView />;
      case 'static-analysis': return <PipelineDetailView />;
      case 'plan-review': return <PipelineDetailView />;
      case 'apply-review': return <PipelineDetailView />;
      case 'escalation-handler': return <PipelineDetailView />;
      case 'session-manager': return <PipelineDetailView />;
      case 'workspace-manager': return <MonacoWorkspacePanel files={[]} selectedFile={null} onFileSelect={() => {}} />;
      default:
        // Fallback logic
        return isAuthenticated ? <DashboardPage /> : <LandingPage onNavigate={handleNavigate} />;
    }
  };

  // Show loading state only while initializing authentication, not while loading projects
  if (!isInitialized) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-primary mx-auto mb-4"></div>
          <p className="text-gray-600">Initializing Iacgenie AI...</p>
        </div>
      </div>
    );
  }

  return (
    <AppErrorBoundary>
      <BrowserRouter>
        <LocationSyncer />
        <Routes>
            {/* Email verification route */}
          <Route path="/verify-email/:token" element={<VerifyEmailPage />} />
          {/* OTP verification route */}
          <Route path="/verify-otp/:token" element={<VerifyOtpPage />} />

        {/* Public-only routes — redirect to dashboard if already authenticated */}
        <Route path="/signin" element={<PublicOnlyRoute><SignInPage onSignIn={handleSignIn} onNavigate={handleNavigate} /></PublicOnlyRoute>} />
        <Route path="/signup" element={<PublicOnlyRoute><SignUpPage onNavigate={handleNavigate} /></PublicOnlyRoute>} />
        <Route path="/forgot-password" element={<PublicOnlyRoute><ForgotPasswordPage onNavigate={handleNavigate} /></PublicOnlyRoute>} />
        <Route path="/reset-password" element={<PublicOnlyRoute><ResetPasswordPage onNavigate={handleNavigate} /></PublicOnlyRoute>} />
        <Route path="/about" element={<PublicLayout><AboutUsPage /></PublicLayout>} />
        <Route path="/privacy" element={<PublicLayout><PrivacyPolicyPage /></PublicLayout>} />
        <Route path="/terms" element={<PublicLayout><TermsOfServicePage /></PublicLayout>} />
        <Route path="/contact" element={<PublicLayout><ContactUsPage /></PublicLayout>} />
        <Route path="/aup" element={<PublicLayout><AcceptableUsePolicyPage /></PublicLayout>} />
        <Route path="/docs" element={<PublicLayout><DocsPage /></PublicLayout>} />
        <Route path="/api-docs" element={<PublicLayout><SwaggerPage /></PublicLayout>} />

        {/* Protected routes — require authentication */}
        <Route path="/dashboard" element={<ProtectedRoute>{renderDashboardLayout()}</ProtectedRoute>} />
        <Route path="/generator" element={<ProtectedRoute>{renderDashboardLayout()}</ProtectedRoute>} />
        <Route path="/deployments" element={<ProtectedRoute>{renderDashboardLayout()}</ProtectedRoute>} />
        <Route path="/settings" element={<ProtectedRoute>{renderDashboardLayout()}</ProtectedRoute>} />
        <Route path="/developer" element={<ProtectedRoute>{renderDashboardLayout()}</ProtectedRoute>} />
        <Route path="/billing" element={<ProtectedRoute>{renderDashboardLayout()}</ProtectedRoute>} />
        <Route path="/audit-log" element={<ProtectedRoute>{renderDashboardLayout()}</ProtectedRoute>} />
        <Route path="/human-review" element={<ProtectedRoute>{renderDashboardLayout()}</ProtectedRoute>} />
        <Route path="/usage-analytics" element={<ProtectedRoute>{renderDashboardLayout()}</ProtectedRoute>} />
        <Route path="/team-members" element={<ProtectedRoute>{renderDashboardLayout()}</ProtectedRoute>} />
        <Route path="/workspace-manager" element={<ProtectedRoute>{renderDashboardLayout()}</ProtectedRoute>} />

        {/* Pipeline agentic loop routes */}
        <Route path="/pipelines" element={<ProtectedRoute>{renderDashboardLayout()}</ProtectedRoute>} />
        <Route path="/pipelines/new" element={<ProtectedRoute>{renderDashboardLayout()}</ProtectedRoute>} />
        <Route path="/pipelines/:id/generate" element={<ProtectedRoute>{renderDashboardLayout()}</ProtectedRoute>} />
        <Route path="/pipelines/:id/static-analysis" element={<ProtectedRoute>{renderDashboardLayout()}</ProtectedRoute>} />
        <Route path="/pipelines/:id/plan-review" element={<ProtectedRoute>{renderDashboardLayout()}</ProtectedRoute>} />
        <Route path="/pipelines/:id/apply-review" element={<ProtectedRoute>{renderDashboardLayout()}</ProtectedRoute>} />
        <Route path="/pipelines/:id/escalation" element={<ProtectedRoute>{renderDashboardLayout()}</ProtectedRoute>} />
        <Route path="/pipelines/:id/sessions" element={<ProtectedRoute>{renderDashboardLayout()}</ProtectedRoute>} />

        {/* 301 redirects for deleted routes */}
        <Route path="/generation-history" element={<Navigate to="/pipelines" replace />} />
        <Route path="/generation-diff" element={<Navigate to="/pipelines" replace />} />
        <Route path="/state-timeline" element={<Navigate to="/pipelines" replace />} />
        <Route path="/observability" element={<Navigate to="/pipelines" replace />} />
        <Route path="/admin" element={<Navigate to="/pipelines" replace />} />

        {/* Home route - renders outside LayoutShell */}
        <Route path="/" element={<LandingPage onNavigate={handleNavigate} />} />

        {/* Fallback to dashboard layout for all other routes when authenticated */}
        <Route path="*" element={<ProtectedRoute>{renderDashboardLayout()}</ProtectedRoute>} />
      </Routes>
    </BrowserRouter>
  </AppErrorBoundary>
);
}

export default App;