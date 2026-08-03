
import React from 'react';
import Card from '../ui/Card';
import Button from '../ui/Button';
import { useAppStore } from '../../store/useAppStore';

const AboutUsPage: React.FC = () => {
  const isAuthenticated = useAppStore(state => state.isAuthenticated);
  const navigate = useAppStore(state => state.navigate);

  return (
    <div className="max-w-4xl mx-auto py-12 px-4 space-y-8 text-slate-900 dark:text-slate-50 dark:text-slate-100 transition-colors duration-200">
      <div>
        <h1 className="text-4xl font-extrabold text-slate-900 dark:text-slate-50 dark:text-white sm:text-5xl">About Iacgenie</h1>
        <p className="mt-4 text-xl text-slate-600 dark:text-slate-300 dark:text-slate-400">
          Empowering developers to build and deploy cloud infrastructure with the speed of thought.
        </p>
      </div>

      <Card>
        <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-50 mb-4">Our Mission</h2>
        <p className="text-lg text-slate-700 dark:text-slate-200">
          At Iacgenie, our mission is to revolutionize the way developers interact with cloud infrastructure. We believe that creating, configuring, and deploying complex systems should be an intuitive and efficient process, not a bottleneck. By harnessing the power of artificial intelligence, we translate natural language into production-grade Infrastructure-as-Code, enabling teams to focus on innovation instead of boilerplate.
        </p>
      </Card>

      <Card>
        <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-50 mb-4">What is Iacgenie?</h2>
        <p className="mb-4 text-slate-700 dark:text-slate-200">
          Iacgenie is a cutting-edge SaaS platform designed to bridge the gap between human intent and machine execution. Simply describe your infrastructure needs in plain English, and our advanced AI models will generate modular, secure, and scalable code for the tools you already use and love.
        </p>
        <ul className="list-disc list-inside space-y-2 text-slate-600 dark:text-slate-300">
          <li>
            <span className="font-semibold text-slate-800 dark:text-slate-100">AI-Driven Code Generation:</span> Go from a prompt like “Create a serverless API with a DynamoDB table” to complete OpenTofu, Docker, or Kubernetes files in seconds.
          </li>
          <li>
            <span className="font-semibold text-slate-800 dark:text-slate-100">Seamless Cloud Deployment:</span> Connect your cloud accounts (AWS, GCP, Azure) and deploy your generated infrastructure directly from our platform.
          </li>
          <li>
            <span className="font-semibold text-slate-800 dark:text-slate-100">Multi-Cloud & Multi-Tool:</span> We support the industry's most popular tools and providers, ensuring Iacgenie fits perfectly into your existing workflows.
          </li>
        </ul>
      </Card>

      <Card>
        <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-50 mb-4">Our Core Values</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-slate-50 dark:bg-slate-700/50 p-4 rounded-lg border border-slate-200 dark:border-slate-600">
            <h3 className="font-semibold text-brand-primary mb-2">Developer Empowerment</h3>
            <p className="text-sm text-slate-600 dark:text-slate-300">We build tools that augment developer capabilities, reduce cognitive load, and make complex tasks more manageable.</p>
          </div>
          <div className="bg-slate-50 dark:bg-slate-700/50 p-4 rounded-lg border border-slate-200 dark:border-slate-600">
            <h3 className="font-semibold text-brand-primary mb-2">Radical Automation</h3>
            <p className="text-sm text-slate-600 dark:text-slate-300">We are committed to automating every possible step of the infrastructure lifecycle to improve speed, reliability, and consistency.</p>
          </div>
          <div className="bg-slate-50 dark:bg-slate-700/50 p-4 rounded-lg border border-slate-200 dark:border-slate-600">
            <h3 className="font-semibold text-brand-primary mb-2">Security & Transparency</h3>
            <p className="text-sm text-slate-600 dark:text-slate-300">We prioritize security in our code generation and provide full visibility into the infrastructure you are deploying. No black boxes.</p>
          </div>
        </div>
      </Card>

      <div className="text-center pt-4">
        <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-50 dark:text-white">Ready to build the future?</h2>
        <p className="mt-2 text-slate-600 dark:text-slate-300 dark:text-slate-400">
          Start generating your infrastructure in seconds.
        </p>
        <div className="mt-6">
          <Button
            size="lg"
            variant="primary"
            onClick={() => {
              if (isAuthenticated) {
                navigate('generator');
              } else {
                navigate('signin');
              }
            }}
          >
            Get Started with Iacgenie
          </Button>
        </div>
      </div>
    </div>
  );
};

export default AboutUsPage;