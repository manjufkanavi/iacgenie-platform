import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Send, ChevronRight, Home, Copy, FileCode,
  CheckCircle2, Clock, AlertTriangle, Play, HelpCircle
} from 'lucide-react';
import { usePipelineStore, ChatMessage } from '../../store/usePipelineStore';
import { workflowService as workflowService } from '../../services/workflowService';
import toast from 'react-hot-toast';

function PageBreadcrumb({ pipelineId }: { pipelineId: string }): React.ReactElement {
  return (
    <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400 mb-4" data-testid="clarify-breadcrumb">
      <Home className="w-4 h-4 hover:text-brand-primary cursor-pointer" />
      <ChevronRight className="w-3 h-3" />
      <span>Pipelines</span>
      <ChevronRight className="w-3 h-3" />
      <span className="hover:text-brand-primary cursor-pointer">{pipelineId}</span>
      <ChevronRight className="w-3 h-3" />
      <span className="text-slate-900 dark:text-slate-50 font-bold">Clarify</span>
    </div>
  );
}

const ClarifyAgentPanel: React.FC = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const pipelineId = id || 'abc123-def456';

  const {
    activePipeline,
    addLogEntry,
    clarifyConversations,
    setClarifyConversation,
    addClarifyMessage,
    specDrafts,
    addSpecDraft,
  } = usePipelineStore();

  const [inputValue, setInputValue] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeDraftTab, setActiveDraftTab] = useState(0);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const messages = clarifyConversations[pipelineId] || [];
  const drafts = specDrafts[pipelineId] || [];

  // Determine current agent responsive visual status: Running, Escalation, Complete
  // Default status mapping if activePipeline is not set
  const pipelineStatus = activePipeline?.status || 'running'; // running, escalated, completed, paused, failed
  
  // Set up mock conversation and mock drafts on initial load if empty
  useEffect(() => {
    if (id) {
      workflowService.getPipelineState(id).then((data: any) => {
        addLogEntry({ phase: 'clarify', message: `Pipeline loaded: ${data.data?.pipeline_id}`, level: 'info' });
      }).catch(() => {});
    }

    if (messages.length === 0) {
      const initialMessages: ChatMessage[] = [
        {
          id: 'msg_1',
          role: 'agent',
          content: 'Hello! I am the Iacgenie Clarify Agent. I have analyzed your initial infrastructure request. To proceed with the highest level of accuracy, could you please clarify the following:\n\n1. Which cloud provider and region are we targeting?\n2. What is your approximate monthly budget?\n3. Do you have specific instance type or storage size constraints?',
          timestamp: new Date(Date.now() - 300000).toISOString(),
          suggestions: ['AWS in us-west-2, budget under $500', 'GCP in us-central1, budget under $1000', 'Azure in eastus, custom setup']
        }
      ];
      setClarifyConversation(pipelineId, initialMessages);
    }

    if (drafts.length === 0) {
      const initialDraft = JSON.stringify({
        $schema: "https://iacgenie.ai/schemas/pipeline-spec-v1.json",
        version: "1.0.0",
        provider: "aws",
        region: "us-west-2",
        resources: {
          vpc: { cidr: "10.0.0.0/16" },
          subnets: ["public-a", "public-b", "private-a", "private-b"],
          nat_gateway: true
        },
        metadata: {
          generatedBy: "ClarifyAgent",
          versionId: "draft_v1"
        }
      }, null, 2);
      addSpecDraft(pipelineId, initialDraft);
    }
  }, [id, pipelineId, messages.length, drafts.length, setClarifyConversation, addSpecDraft, addLogEntry]);

  // Scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  const handleSend = () => {
    if (!inputValue.trim()) return;

    const userMsg: ChatMessage = {
      id: `msg_${Date.now()}`,
      role: 'user',
      content: inputValue,
      timestamp: new Date().toISOString()
    };

    addClarifyMessage(pipelineId, userMsg);
    setInputValue('');
    setIsStreaming(true);

    // Simulate Agent response and generation of a new spec draft version
    setTimeout(() => {
      // Determine provider/region based on input
      const inputLower = inputValue.toLowerCase();
      const provider = inputLower.includes('gcp') ? 'gcp' : inputLower.includes('azure') ? 'azure' : 'aws';
      const region = inputLower.includes('us-central1') ? 'us-central1' : inputLower.includes('eastus') ? 'eastus' : 'us-west-2';
      const budget = inputLower.includes('1000') ? 1000 : 500;

      const newAgentMsg: ChatMessage = {
        id: `msg_${Date.now() + 1}`,
        role: 'agent',
        content: `Got it! I've analyzed your clarification details:\n- Cloud Provider: **${provider.toUpperCase()}**\n- Region: **${region}**\n- Budget: **$${budget}/month**\n\nI have successfully synthesized Draft version ${drafts.length + 1} of the specification file in the sidebar. Please review.`,
        timestamp: new Date().toISOString(),
        confidence: 96,
        suggestions: ['Looks perfect, proceed!', 'Change to multi-region setup', 'Enable VPC Peering']
      };

      addClarifyMessage(pipelineId, newAgentMsg);

      // Generate new draft
      const newDraftSpec = JSON.stringify({
        $schema: "https://iacgenie.ai/schemas/pipeline-spec-v1.json",
        version: `1.0.${drafts.length}`,
        provider,
        region,
        resources: {
          vpc: { cidr: "10.0.0.0/16" },
          subnets: ["public-a", "public-b", "private-a", "private-b"],
          nat_gateway: true,
          budget_limits: { monthly: budget }
        },
        metadata: {
          generatedBy: "ClarifyAgent",
          versionId: `draft_v${drafts.length + 1}`,
          timestamp: new Date().toISOString()
        }
      }, null, 2);

      addSpecDraft(pipelineId, newDraftSpec);
      setActiveDraftTab(drafts.length); // Switch to the newly generated spec tab
      setIsStreaming(false);
      toast.success(`Draft specification v${drafts.length + 1} generated successfully!`);
    }, 2000);
  };

  const handleSuggestionClick = (suggestion: string) => {
    setInputValue(suggestion);
  };

  const handleCopySpec = () => {
    const currentSpec = drafts[activeDraftTab] || '';
    if (currentSpec) {
      navigator.clipboard.writeText(currentSpec);
      toast.success('Draft specification copied to clipboard!');
    }
  };

  const handleEscalationResponse = (action: string) => {
    toast.success(`Escalation resolved: action "${action}" triggered.`);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-6" data-testid="clarify-agent-panel">
      {/* Breadcrumb */}
      <PageBreadcrumb pipelineId={pipelineId} />

      {/* Responsive Visual State Header Card */}
      {/* Visual State: ESCALATION (status === 'escalated') */}
      {pipelineStatus === 'escalated' ? (
        <div className="bg-amber-50 dark:bg-amber-950/20 rounded-2xl shadow-xl p-6 mb-6 border-l-4 border-amber-500 animate-fade-in" data-testid="clarify-header-escalated">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-amber-100 dark:bg-amber-900/30 rounded-xl flex items-center justify-center flex-shrink-0 border border-amber-200">
                <AlertTriangle className="w-6 h-6 text-amber-600 animate-bounce" />
              </div>
              <div>
                <h1 className="text-2xl font-black text-amber-900 dark:text-amber-200">Clarify Agent - Escalation Triggered</h1>
                <p className="text-sm font-semibold text-amber-700 dark:text-amber-400 mt-0.5">The pipeline requires human intervention to resolve resource contradictions.</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => handleEscalationResponse('override')}
                className="px-4 py-2 bg-amber-600 text-white rounded-xl text-xs font-extrabold uppercase tracking-wider hover:bg-amber-700 transition"
              >
                Override Spec
              </button>
              <button
                onClick={() => handleEscalationResponse('re-run')}
                className="px-4 py-2 bg-white text-amber-700 border border-amber-200 rounded-xl text-xs font-extrabold uppercase tracking-wider hover:bg-amber-50 transition"
              >
                Re-Run Agent
              </button>
            </div>
          </div>
        </div>
      ) : pipelineStatus === 'completed' ? (
        /* Visual State: COMPLETE (status === 'completed') */
        <div className="bg-green-50 dark:bg-green-950/20 rounded-2xl shadow-xl p-6 mb-6 border-l-4 border-green-500 animate-fade-in" data-testid="clarify-header-completed">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-green-100 dark:bg-green-900/30 rounded-xl flex items-center justify-center flex-shrink-0 border border-green-200">
                <CheckCircle2 className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <h1 className="text-2xl font-black text-green-900 dark:text-green-200">Clarify Agent - Requirements Complete</h1>
                <p className="text-sm font-semibold text-green-700 dark:text-green-400 mt-0.5">Specifications gathered. Proceed to next phase.</p>
              </div>
            </div>
            <button
              onClick={() => navigate(`/generator-agent/${pipelineId}`)}
              className="px-5 py-2.5 bg-green-600 text-white rounded-xl text-xs font-extrabold uppercase tracking-wider hover:bg-green-700 transition shadow-md"
            >
              Start Code Generation
            </button>
          </div>
        </div>
      ) : (
        /* Visual State: RUNNING (status === 'running') */
        <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 mb-6 border-l-4 border-brand-primary" data-testid="clarify-header-running">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-brand-primary-subtle rounded-xl flex items-center justify-center">
                <FileCode className="w-5 h-5 text-brand-primary animate-pulse" />
              </div>
              <div>
                <h1 className="text-2xl font-black text-slate-900 dark:text-slate-50">Clarify Agent - Requirements Gathering</h1>
                <p className="text-sm font-semibold text-slate-500 dark:text-slate-400 mt-0.5">Active multi-turn conversation refining specifications.</p>
              </div>
            </div>
            <div className="flex items-center gap-4 text-xs font-semibold flex-wrap">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-brand-primary animate-ping" />
                <span className="text-brand-primary font-bold uppercase tracking-wider">Agent Running</span>
              </span>
              <span className="text-slate-400 dark:text-slate-500">|</span>
              <span className="text-slate-500 dark:text-slate-400">
                Turns: <span className="font-bold text-slate-800 dark:text-slate-200">{messages.filter((m) => m.role === 'agent').length}</span>
              </span>
              <span className="text-slate-400 dark:text-slate-500">|</span>
              <span className="px-2.5 py-1 bg-slate-100 dark:bg-slate-700 rounded-lg text-slate-600 dark:text-slate-300">
                Model: Gemini 1.5 Pro
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        {/* Chat Panel (2 columns) */}
        <div className="lg:col-span-2">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 sm:p-8 flex flex-col h-[650px] border border-slate-100 dark:border-slate-600">
            <h2 className="text-sm font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-6 flex items-center gap-2">
              <HelpCircle className="w-4 h-4 text-brand-primary" />
              Agent Conversation Thread
            </h2>

            {/* Chat Messages */}
            <div className="flex-1 overflow-y-auto pr-2 space-y-6 mb-6">
              {messages.map((msg) => (
                <div key={msg.id} className={`flex gap-3.5 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`} data-testid={`chat-message-${msg.role}`}>
                  {/* Avatar */}
                  <div
                    className={`w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 shadow-md ${
                      msg.role === 'agent'
                        ? 'bg-brand-primary'
                        : 'bg-slate-800 border border-slate-700'
                    }`}
                  >
                    {msg.role === 'agent' ? (
                      <FileCode className="w-4 h-4 text-white" />
                    ) : (
                      <span className="text-white text-xs font-black">USER</span>
                    )}
                  </div>

                  {/* Message Bubble */}
                  <div className={`flex-1 ${msg.role === 'user' ? 'flex justify-end' : ''}`}>
                    <div
                      className={`rounded-2xl p-4 max-w-[85%] shadow-sm ${
                        msg.role === 'agent'
                          ? 'bg-brand-primary-subtle border border-brand-primary/20 rounded-[20px_20px_20px_4px] text-slate-900 dark:text-slate-50'
                          : 'bg-slate-800 text-white rounded-[20px_20px_4px_20px]'
                      }`}
                    >
                      {/* Header */}
                      <div className={`flex items-center gap-2 mb-2 ${msg.role === 'user' ? 'justify-end' : ''}`}>
                        <span className="text-xs font-black uppercase tracking-wider text-slate-400 dark:text-slate-500">
                          {msg.role === 'agent' ? 'Clarify Agent' : 'You'}
                        </span>
                        <span className="text-[10px] font-semibold text-slate-400 dark:text-slate-500">
                          {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>

                      {/* Content */}
                      <p className="text-sm font-semibold leading-relaxed whitespace-pre-wrap">{msg.content}</p>

                      {/* Confidence Badge */}
                      {msg.confidence && msg.role === 'agent' && (
                        <div className="mt-3">
                          <span className="px-2 py-0.5 bg-brand-primary/10 text-brand-primary rounded-lg text-[10px] font-bold uppercase tracking-wider">
                            Confidence: {msg.confidence}%
                          </span>
                        </div>
                      )}

                      {/* Suggestions */}
                      {msg.suggestions && msg.role === 'agent' && (
                        <div className="flex flex-wrap gap-2 mt-4">
                          {msg.suggestions.map((suggestion) => (
                            <button
                              key={suggestion}
                              onClick={() => handleSuggestionClick(suggestion)}
                              className="px-3.5 py-1.5 bg-white border border-slate-200 dark:border-slate-600 rounded-full text-xs font-bold text-slate-600 dark:text-slate-300 hover:border-brand-primary hover:text-brand-primary transition shadow-sm"
                            >
                              {suggestion}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}

              {/* Streaming Indicator */}
              {isStreaming && (
                <div className="flex gap-3.5">
                  <div className="w-9 h-9 bg-brand-primary rounded-full flex items-center justify-center flex-shrink-0 shadow-md">
                    <FileCode className="w-4 h-4 text-white" />
                  </div>
                  <div className="bg-brand-primary-subtle border border-brand-primary/20 rounded-[20px_20px_20px_4px] p-4 flex items-center gap-3">
                    <div className="flex space-x-1 animate-pulse">
                      <div className="w-2.5 h-2.5 bg-brand-primary rounded-full animate-bounce" />
                      <div className="w-2.5 h-2.5 bg-brand-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <div className="w-2.5 h-2.5 bg-brand-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                    <span className="text-xs font-bold text-brand-primary uppercase tracking-wider">Agent is typing...</span>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Input Box */}
            <div className="border-t border-slate-100 dark:border-slate-600 pt-4 mt-auto">
              <textarea
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                className="w-full border border-slate-200 dark:border-slate-600 rounded-xl p-3 text-sm focus:outline-none focus:ring-4 focus:ring-brand-primary/20 focus:border-brand-primary resize-none bg-white text-slate-900 dark:text-slate-50 placeholder-slate-400 dark:placeholder-slate-500 font-semibold"
                rows={3}
                placeholder="Reply to Clarify Agent or paste requirement specs..."
                disabled={isStreaming}
              />

              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mt-3 gap-3">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">Quick Actions:</span>
                  <button
                    onClick={() => handleSuggestionClick('AWS setup in region us-west-2')}
                    className="px-3 py-1 bg-slate-50 dark:bg-slate-700/50 border border-slate-200 dark:border-slate-600 rounded-lg text-xs font-bold text-slate-600 dark:text-slate-300 hover:border-brand-primary hover:text-brand-primary transition"
                  >
                    AWS setup
                  </button>
                  <button
                    onClick={() => handleSuggestionClick('Proceed with default values')}
                    className="px-3 py-1 bg-slate-50 dark:bg-slate-700/50 border border-slate-200 dark:border-slate-600 rounded-lg text-xs font-bold text-slate-600 dark:text-slate-300 hover:border-brand-primary hover:text-brand-primary transition"
                  >
                    Use Defaults
                  </button>
                </div>
                <button
                  onClick={handleSend}
                  disabled={!inputValue.trim() || isStreaming}
                  className="px-5 py-2.5 bg-brand-primary border-0 text-white rounded-xl text-sm font-bold shadow-md hover:bg-brand-primary/90 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transform hover:-translate-y-0.5 active:translate-y-0"
                >
                  <Send className="w-4 h-4" />
                  Send Response
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Refined Spec Preview Sidebar (1 column) */}
        <div className="lg:col-span-1">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 border border-slate-100 dark:border-slate-600 flex flex-col h-[650px]">
            {/* Version Draft Tabs */}
            <div className="border-b border-slate-200 dark:border-slate-600 pb-3 mb-4">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider flex items-center gap-2">
                  <FileCode className="w-4 h-4 text-green-500" />
                  Spec Version Drafts
                </h2>
                <div className="flex items-center gap-1">
                  <button
                    onClick={handleCopySpec}
                    className="p-1.5 text-slate-400 dark:text-slate-500 hover:text-brand-primary hover:bg-brand-primary-subtle rounded-lg transition"
                    title="Copy specification to clipboard"
                  >
                    <Copy className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Draft Tab row */}
              <div className="flex flex-wrap gap-1.5" data-testid="spec-drafts-tabs">
                {drafts.map((_, index) => (
                  <button
                    key={index}
                    onClick={() => setActiveDraftTab(index)}
                    className={`px-3 py-1 rounded-lg text-xs font-bold transition ${
                      activeDraftTab === index
                        ? 'bg-brand-primary text-white shadow-sm'
                        : 'bg-slate-50 dark:bg-slate-700/50 text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700'
                    }`}
                    data-testid={`spec-draft-tab-${index}`}
                  >
                    v1.{index}
                  </button>
                ))}
              </div>
            </div>

            {/* Spec JSON Code Editor Viewer */}
            <div className="flex-1 bg-slate-900 rounded-xl p-4 font-mono text-[11px] overflow-auto shadow-inner text-green-400 border border-slate-850 h-[380px]">
              {drafts[activeDraftTab] ? (
                <pre>{drafts[activeDraftTab]}</pre>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-center text-slate-500 dark:text-slate-400">
                  <Clock className="w-10 h-10 mb-2 animate-spin text-slate-600 dark:text-slate-300" />
                  <p>Synthesizing draft spec...</p>
                </div>
              )}
            </div>

            {/* Next Step Action Button */}
            <button
              disabled={drafts.length === 0 || isStreaming}
              onClick={() => {
                toast.success('Specifications verified! Launching generator agent...');
                navigate(`/generator-agent/${pipelineId}`);
              }}
              className="w-full mt-4 py-3.5 bg-brand-primary hover:bg-brand-primary/90 text-white rounded-xl text-xs font-extrabold uppercase tracking-wider shadow-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed transform hover:-translate-y-0.5 active:translate-y-0 flex items-center justify-center gap-2"
              data-testid="clarify-proceed-button"
            >
              <Play className="w-4 h-4 fill-current" />
              Verify & Proceed
            </button>
          </div>
        </div>
      </div>

      {/* Footer Back Dashboard */}
      <div className="mt-4">
        <button
          onClick={() => navigate(`/pipeline/${pipelineId}`)}
          className="inline-flex items-center gap-2 text-sm font-bold text-brand-primary hover:text-brand-primary/80 transition"
        >
          <Home className="w-4 h-4" />
          Back to Pipeline Dashboard
        </button>
      </div>
    </div>
  );
};

export { ClarifyAgentPanel };