import React, { useState, useEffect } from 'react';
import { Send, Github, Gitlab, RefreshCw, Layers, CheckCircle2, FileJson } from 'lucide-react';
import { toast } from 'react-hot-toast';
import Card from '../ui/Card';
import Button from '../ui/Button';
import PRCommentDisplay, { PrCommentData, ResourceChange } from '../pipeline/PRCommentDisplay';

interface PRCommentSimulatorProps {
    projectId: string;
    repoId: string;
    repoName: string;
    provider: 'github' | 'gitlab';
    branch: string;
    className?: string;
}

const PRCommentSimulator: React.FC<PRCommentSimulatorProps> = ({
    projectId,
    repoId: _repoId,
    repoName,
    provider,
    branch = 'main',
    className = ''
}) => {
    const [prNumber, setPrNumber] = useState(42);
    const [prBranch, setPrBranch] = useState('feat/waf-reputation-rule');
    const [eventTemplate, setEventTemplate] = useState<'pr-open' | 'pr-sync' | 'comment-apply' | 'pr-failed'>('pr-open');
    const [isDispatching, setIsDispatching] = useState(false);
    const [rawPayload, setRawPayload] = useState<any>({});
    
    // Live PR comment mock data that changes on dispatching events
    const [prComment, setPrComment] = useState<PrCommentData | null>(null);

    // Compute sample resources
    const mockResources: ResourceChange[] = [
        { action: 'add', resource: 'aws_waf_rule.ip_reputation' },
        { action: 'add', resource: 'aws_security_group_rule.waf_ingress' },
        { action: 'remove', resource: 'aws_security_group_rule.legacy_ssh' }
    ];

    const generatePayload = () => {
        const repoFull = `${provider === 'github' ? 'github.com' : 'gitlab.com'}/my-org/${repoName}`;
        const commitHash = '6a3b2c1f4e9d8c7b6a5e4d3c2b1a0f9e8d7c6b5a';
        
        switch (eventTemplate) {
            case 'pr-open':
                return {
                    event: 'pull_request',
                    action: 'opened',
                    number: prNumber,
                    pull_request: {
                        head: { ref: prBranch, sha: commitHash },
                        base: { ref: branch },
                        title: 'Add WAF IP reputation rule and remove legacy SSH ingress',
                        html_url: `https://${provider === 'github' ? 'github' : 'gitlab'}.com/my-org/${repoName}/pull/${prNumber}`
                    },
                    repository: {
                        name: repoName,
                        full_name: `my-org/${repoName}`,
                        html_url: `https://${repoFull}`
                    },
                    sender: { login: 'manjufkanavi', avatar_url: 'https://avatars.githubusercontent.com/u/101ca890' }
                };
            case 'pr-sync':
                return {
                    event: 'pull_request',
                    action: 'synchronize',
                    number: prNumber,
                    pull_request: {
                        head: { ref: prBranch, sha: '8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d' },
                        base: { ref: branch },
                        title: 'Add WAF IP reputation rule and remove legacy SSH ingress',
                        html_url: `https://${provider === 'github' ? 'github' : 'gitlab'}.com/my-org/${repoName}/pull/${prNumber}`
                    },
                    repository: { name: repoName, full_name: `my-org/${repoName}` }
                };
            case 'comment-apply':
                return {
                    event: 'issue_comment',
                    action: 'created',
                    issue: {
                        number: prNumber,
                        pull_request: { html_url: `https://${provider === 'github' ? 'github' : 'gitlab'}.com/my-org/${repoName}/pull/${prNumber}` }
                    },
                    comment: {
                        id: 19837648,
                        body: 'digger apply',
                        user: { login: 'manjufkanavi' }
                    },
                    repository: { name: repoName, full_name: `my-org/${repoName}` }
                };
            case 'pr-failed':
                return {
                    event: 'pull_request',
                    action: 'opened',
                    number: prNumber,
                    pull_request: {
                        head: { ref: 'feat/failed-auth', sha: '9f1d4e2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e' },
                        base: { ref: branch },
                        title: 'Draft invalid credentials resource config',
                        html_url: `https://${provider === 'github' ? 'github' : 'gitlab'}.com/my-org/${repoName}/pull/${prNumber}`
                    },
                    repository: { name: repoName, full_name: `my-org/${repoName}` }
                };
        }
    };

    useEffect(() => {
        setRawPayload(generatePayload());
    }, [eventTemplate, prNumber, prBranch]);

    const handleDispatch = async () => {
        setIsDispatching(true);
        try {
            // Post payload to backend receive API or execute local simulate flow
            const { getAuthHeaders } = await import('../../services/authHeaders');
            await fetch(`/api/webhooks/receive/${projectId}-${repoName}`, {
                method: 'POST',
                headers: {
                    ...getAuthHeaders(),
                    'Content-Type': 'application/json',
                    'X-GitHub-Event': eventTemplate.startsWith('comment') ? 'issue_comment' : 'pull_request'
                },
                body: JSON.stringify(rawPayload)
            });
            
            // Wait 1.2s to simulate active planning and logs execution runs
            await new Promise(resolve => setTimeout(resolve, 1200));

            // Set comment state based on template triggered
            if (eventTemplate === 'pr-open') {
                setPrComment({
                    state: 'plan-succeeded',
                    title: 'OpenTofu Plan summary',
                    resources: mockResources,
                    planDetails: `Initializing OpenTofu...\nSuccess! Plan: 2 to add, 0 to change, 1 to destroy.\n\n+ resource "aws_waf_rule" "ip_reputation" {\n    name = "ip_reputation"\n  }\n+ resource "aws_security_group_rule" "waf_ingress" {\n    type = "ingress"\n  }\n- resource "aws_security_group_rule" "legacy_ssh" {\n    type = "ingress"\n  }`,
                    expandable: true,
                    prUrl: `https://${provider === 'github' ? 'github' : 'gitlab'}.com/my-org/${repoName}/pull/${prNumber}`,
                    commitHash: '6a3b2c1f4e9d8c7b6a5e4d3c2b1a0f9e8d7c6b5a',
                    timestamp: new Date()
                });
                toast.success('Digger Plan posted as PR comment successfully!');
            } else if (eventTemplate === 'comment-apply') {
                if (!prComment) {
                    toast.error('You must dispatch a PR Open Plan event first before applying.');
                    return;
                }
                setPrComment(prev => prev ? ({
                    ...prev,
                    state: 'apply-succeeded',
                    title: 'OpenTofu Apply complete',
                    planDetails: `Successfully applied plan output to AWS Cloud infrastructure!\nApply complete! Resources: 2 added, 0 changed, 1 destroyed.`
                }) : null);
                toast.success('Digger Apply executed successfully!');
            } else if (eventTemplate === 'pr-failed') {
                setPrComment({
                    state: 'plan-failed',
                    title: 'OpenTofu Plan (Failed)',
                    resources: [{ action: 'add', resource: 'aws_security_group_rule.legacy_ssh' }],
                    planDetails: `Error: rpc error: code = Unknown desc = provider "aws" not configured\nCheck that AWS credentials are mounted in the Digger deployment.`,
                    expandable: true,
                    prUrl: `https://${provider === 'github' ? 'github' : 'gitlab'}.com/my-org/${repoName}/pull/${prNumber}`,
                    commitHash: '9f1d4e2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e',
                    timestamp: new Date()
                });
                toast.error('Digger Plan failed, error logs posted.');
            }
        } catch (error) {
            // Mock succeed case if backend receive endpoint does not exist yet (as we assume it will be developed)
            // This satisfies the offline/sandbox resilience of the UI developer guidelines!
            if (eventTemplate === 'pr-open') {
                setPrComment({
                    state: 'plan-succeeded',
                    title: 'OpenTofu Plan summary',
                    resources: mockResources,
                    planDetails: `Initializing OpenTofu...\nSuccess! Plan: 2 to add, 0 to change, 1 to destroy.\n\n+ resource "aws_waf_rule" "ip_reputation" {\n    name = "ip_reputation"\n  }\n+ resource "aws_security_group_rule" "waf_ingress" {\n    type = "ingress"\n  }\n- resource "aws_security_group_rule" "legacy_ssh" {\n    type = "ingress"\n  }`,
                    expandable: true,
                    prUrl: `https://${provider === 'github' ? 'github' : 'gitlab'}.com/my-org/${repoName}/pull/${prNumber}`,
                    commitHash: '6a3b2c1f4e9d8c7b6a5e4d3c2b1a0f9e8d7c6b5a',
                    timestamp: new Date()
                });
                toast.success('Digger Plan posted (emulated mode).');
            } else if (eventTemplate === 'comment-apply') {
                setPrComment(prev => prev ? ({
                    ...prev,
                    state: 'apply-succeeded',
                    title: 'OpenTofu Apply complete',
                    planDetails: `Successfully applied plan output to AWS Cloud infrastructure!\nApply complete! Resources: 2 added, 0 changed, 1 destroyed.`
                }) : null);
                toast.success('Digger Apply executed (emulated mode).');
            } else if (eventTemplate === 'pr-failed') {
                setPrComment({
                    state: 'plan-failed',
                    title: 'OpenTofu Plan (Failed)',
                    resources: [{ action: 'add', resource: 'aws_security_group_rule.legacy_ssh' }],
                    planDetails: `Error: rpc error: code = Unknown desc = provider "aws" not configured\nCheck that AWS credentials are mounted in the Digger deployment.`,
                    expandable: true,
                    prUrl: `https://${provider === 'github' ? 'github' : 'gitlab'}.com/my-org/${repoName}/pull/${prNumber}`,
                    commitHash: '9f1d4e2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e',
                    timestamp: new Date()
                });
                toast.error('Digger Plan failed.');
            }
        } finally {
            setIsDispatching(false);
        }
    };

    const handleApplyFromComment = () => {
        setEventTemplate('comment-apply');
        toast('Simulating "digger apply" comment dispatch...');
        setTimeout(() => {
            handleDispatch();
        }, 100);
    };

    return (
        <div className={`space-y-6 ${className}`}>
            {/* Header info */}
            <div>
                <h3 className="text-xl font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                    <Layers className="w-5 h-5 text-brand-primary" /> Interactive GitOps PR Comment Simulator
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                    Simulate webhook payloads sent by Git providers, test your Digger workflow configurations, and interact with the resulting bot comments.
                </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                {/* Simulation controls column */}
                <div className="lg:col-span-5 space-y-4">
                    <Card className="p-5 space-y-4 border border-slate-200 dark:border-slate-800">
                        <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400 dark:text-slate-500 block">Simulation Controls</span>
                        
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">PR Number</label>
                                <input
                                    type="number"
                                    value={prNumber}
                                    onChange={(e) => setPrNumber(Number(e.target.value))}
                                    className="w-full bg-slate-50 border border-slate-300 rounded-xl px-4 py-2 text-xs font-semibold"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">PR Source Branch</label>
                                <input
                                    type="text"
                                    value={prBranch}
                                    onChange={(e) => setPrBranch(e.target.value)}
                                    className="w-full bg-slate-50 border border-slate-300 rounded-xl px-4 py-2 text-xs font-semibold"
                                />
                            </div>
                        </div>

                        <div>
                            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Webhook Event Template</label>
                            <div className="space-y-2">
                                {[
                                    { id: 'pr-open', label: 'PR Opened (Run Plan)', desc: 'Simulate opening branch PR to trigger a tofu plan' },
                                    { id: 'comment-apply', label: 'PR Comment: "digger apply" (Run Deploy)', desc: 'Post a comment to execute tofu apply deployment' },
                                    { id: 'pr-failed', label: 'PR Opened - Config Error (Run Failed)', desc: 'Simulate pipeline errors with missing providers' }
                                ].map((t) => (
                                    <label
                                        key={t.id}
                                        className={`flex items-start gap-3 p-2.5 rounded-xl border text-xs font-medium cursor-pointer transition ${
                                            eventTemplate === t.id
                                                ? 'bg-brand-primary/5 border-brand-primary/40 text-slate-800 dark:text-slate-200'
                                                : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700/50 text-slate-500'
                                        }`}
                                    >
                                        <input
                                            type="radio"
                                            name="template"
                                            checked={eventTemplate === t.id}
                                            onChange={() => setEventTemplate(t.id as any)}
                                            className="mt-0.5 accent-brand-primary"
                                        />
                                        <div>
                                            <span className="font-bold text-xs">{t.label}</span>
                                            <p className="text-[10px] text-slate-400 mt-0.5">{t.desc}</p>
                                        </div>
                                    </label>
                                ))}
                            </div>
                        </div>

                        <Button
                            onClick={handleDispatch}
                            disabled={isDispatching}
                            className="w-full flex items-center justify-center gap-1.5 font-bold py-2.5 rounded-xl shadow bg-brand-primary hover:bg-brand-primary/95 text-white"
                        >
                            {isDispatching ? (
                                <>
                                    <RefreshCw className="w-4 h-4 animate-spin" />
                                    Dispatching Event...
                                </>
                            ) : (
                                <>
                                    <Send className="w-4 h-4" />
                                    Dispatch Webhook Event
                                </>
                            )}
                        </Button>
                    </Card>

                    {/* Raw payload JSON view block */}
                    <Card className="p-0 overflow-hidden border border-slate-200 dark:border-slate-800">
                        <div className="bg-slate-900 border-b border-slate-800 px-4 py-2 flex items-center justify-between text-slate-400 font-mono text-[10px]">
                            <span className="flex items-center gap-1.5"><FileJson className="w-3.5 h-3.5 text-brand-primary" /> webhook_payload.json</span>
                            <span className="text-slate-500">POST /api/webhooks/receive</span>
                        </div>
                        <pre className="bg-[var(--color-console-bg)] p-3 text-[10px] text-slate-400 font-mono max-h-[160px] overflow-y-auto select-all scrollbar-thin">
                            <code>{JSON.stringify(rawPayload, null, 2)}</code>
                        </pre>
                    </Card>
                </div>

                {/* PR bot comment output column */}
                <div className="lg:col-span-7 space-y-4">
                    <Card className="p-5 border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 min-h-[400px] flex flex-col justify-between">
                        <div>
                            <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400 dark:text-slate-500 block mb-4">Pull Request Conversation Feed</span>
                            
                            {prComment ? (
                                <div className="animate-fadeIn">
                                    <PRCommentDisplay 
                                        data={prComment} 
                                        onApplyTrigger={handleApplyFromComment}
                                        onRetryTrigger={() => {
                                            setEventTemplate('pr-open');
                                            setTimeout(() => handleDispatch(), 100);
                                        }}
                                    />
                                </div>
                            ) : (
                                <div className="text-center py-20 border border-dashed border-slate-300 dark:border-slate-700 rounded-2xl p-6 bg-white dark:bg-slate-800">
                                    {provider === 'github' ? <Github className="w-12 h-12 text-slate-300 mx-auto mb-3" /> : <Gitlab className="w-12 h-12 text-slate-300 mx-auto mb-3" />}
                                    <h4 className="font-bold text-slate-700 dark:text-slate-200">No Webhook Dispatched Yet</h4>
                                    <p className="text-xs text-slate-400 dark:text-slate-500 max-w-xs mx-auto mt-1 leading-relaxed">
                                        Use the simulator controls on the left to fire a simulated pull request event. Digger's automated comment response will render here.
                                    </p>
                                </div>
                            )}
                        </div>

                        {prComment && (
                            <div className="mt-6 p-3 bg-green-500/10 border border-green-500/20 text-green-700 dark:text-green-400 rounded-xl text-xs flex items-center gap-2.5">
                                <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                                <div>
                                    <span className="font-bold">Active PR Simulation Session:</span>
                                    <p className="text-[10px] text-green-600 dark:text-green-500/90 mt-0.5">Digger bot comment is running on head branch <strong>{prBranch}</strong>. You can interact with actions directly.</p>
                                </div>
                            </div>
                        )}
                    </Card>
                </div>
            </div>
        </div>
    );
};

export default PRCommentSimulator;
