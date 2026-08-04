import React, { useState, useEffect } from 'react';
import Card from '../ui/Card';
import Button from '../ui/Button';
import Select from '../ui/Select';
import { ReviewStatusBadge } from '../ui/ReviewStatusBadge';
import toast from 'react-hot-toast';
import { View } from '../types';
import { workflowService as workflowService } from '../workflowService';

interface ReviewItem {
  id: string;
  generationId: string;
  prompt: string;
  priority: 'high' | 'medium' | 'low';
  status: 'pending-review' | 'needs-revision' | 'assigned' | 'approved';
  assignedTo: string | null;
  createdAt: string;
  testResults?: Array<{ name: string; status: 'passed' | 'failed'; message: string }>;
}

const HumanReviewQueuePage: React.FC<{ onNavigate?: (view: View) => void }> = ({}) => {
  const [reviews, setReviews] = useState<ReviewItem[]>([]);
  const [filteredReviews, setFilteredReviews] = useState<ReviewItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  
  // Filters
  const [priorityFilter, setPriorityFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [assignedTo, setAssignedTo] = useState<string>('all');
  
  // Selection
  const [selectedReviewIds, setSelectedReviewIds] = useState<Set<string>>(new Set());
  
  // Detail view
  const [selectedReviewId, setSelectedReviewId] = useState<string | null>(null);
  const [detailPanelOpen, setDetailPanelOpen] = useState(false);

  // Load pending reviews from pipeline API
  useEffect(() => {
    const loadReviews = async () => {
      setIsLoading(true);
      try {
        const res = await workflowService.getPipelines({
          status: 'running',
          limit: 100,
        });
        const items: ReviewItem[] = (res.data?.sessions || []).map((p: any) => ({
          id: p.id,
          generationId: p.id,
          prompt: p.prompt || 'No description',
          priority: 'medium',
          status: (p.status === 'human_review' || p.status === 'HUMAN_REVIEW') ? 'pending-review' :
                  (p.status === 'assigned') ? 'assigned' : 'pending-review',
          assignedTo: null,
          createdAt: p.created_at || new Date().toISOString(),
          testResults: [],
        }));
        setReviews(items);
      } catch (err) {
        console.error('Failed to load review queue:', err);
        toast.error('Failed to load review queue');
        setReviews([]);
      } finally {
        setIsLoading(false);
      }
    };
    loadReviews();
  }, []);

  // Apply filters
  useEffect(() => {
    let filtered = [...reviews];
    
    if (priorityFilter !== 'all') {
      filtered = filtered.filter(r => r.priority === priorityFilter);
    }
    
    if (statusFilter !== 'all') {
      filtered = filtered.filter(r => r.status === statusFilter);
    }
    
    if (assignedTo !== 'all') {
      filtered = filtered.filter(r => r.assignedTo === assignedTo);
    }
    
    setFilteredReviews(filtered);
  }, [reviews, priorityFilter, statusFilter, assignedTo]);

  const toggleSelectReview = (reviewId: string) => {
    const newSelected = new Set(selectedReviewIds);
    if (newSelected.has(reviewId)) {
      newSelected.delete(reviewId);
    } else {
      newSelected.add(reviewId);
    }
    setSelectedReviewIds(newSelected);
  };

  const handleViewReview = (reviewId: string) => {
    setSelectedReviewId(reviewId);
    setDetailPanelOpen(true);
  };

  const handleCloseDetailPanel = () => {
    setDetailPanelOpen(false);
    setSelectedReviewId(null);
  };

  const handleApprove = async (reviewId: string) => {
    try {
      await workflowService.approvePhase(reviewId);
      toast.success('Review approved successfully');
      setReviews(prev => prev.map(r =>
        r.id === reviewId ? { ...r, status: 'approved' } : r
      ));
      handleCloseDetailPanel();
    } catch (err: any) {
      toast.error(err.message || 'Failed to approve review');
    }
  };

  const handleReject = async (reviewId: string) => {
    try {
      await workflowService.intervenePhase(reviewId, 'Rejected - see comments');
      toast.success('Review rejected successfully');
      setReviews(prev => prev.map(r =>
        r.id === reviewId ? { ...r, status: 'needs-revision' } : r
      ));
      handleCloseDetailPanel();
    } catch (err: any) {
      toast.error(err.message || 'Failed to reject review');
    }
  };

  const getSelectedReview = (): ReviewItem | undefined => {
    return reviews.find(r => r.id === selectedReviewId);
  };

  const hasActiveFilters = priorityFilter !== 'all' || statusFilter !== 'all' || assignedTo !== 'all';

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-50">Human Review Queue</h1>
        <p className="mt-1 text-slate-600 dark:text-slate-300">Review generations requiring human intervention</p>
      </div>

      {/* Filters */}
      <Card padding="none">
        <div className="p-4 border-b border-slate-200 dark:border-slate-600">
          <div className="flex flex-wrap gap-4 items-center">
            {/* Priority Filter */}
            <Select 
              label="Priority" 
              value={priorityFilter} 
              onChange={(e) => setPriorityFilter(e.target.value)}
            >
              <option value="all">All Priorities</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </Select>

            {/* Status Filter */}
            <Select 
              label="Status" 
              value={statusFilter} 
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="all">All Statuses</option>
              <option value="pending-review">Pending Review</option>
              <option value="needs-revision">Needs Revision</option>
              <option value="assigned">Assigned</option>
            </Select>

            {/* Assigned To Filter */}
            <Select 
              label="Assigned To" 
              value={assignedTo} 
              onChange={(e) => setAssignedTo(e.target.value)}
            >
              <option value="all">All Users</option>
              <option value="unassigned">Unassigned</option>
              {/* User options would be populated from store */}
            </Select>

            {/* Clear Filters Button */}
            {hasActiveFilters && (
              <Button 
                variant="secondary" 
                size="sm"
                onClick={() => {
                  setPriorityFilter('all');
                  setStatusFilter('all');
                  setAssignedTo('all');
                }}
              >
                Clear Filters
              </Button>
            )}
          </div>
        </div>

        {/* Bulk Actions Bar */}
        {selectedReviewIds.size > 0 && (
          <div className="p-4 bg-slate-50 dark:bg-slate-700/50 border-b border-slate-200 dark:border-slate-600 flex items-center justify-between">
            <div className="text-sm text-slate-600 dark:text-slate-300">
              {selectedReviewIds.size} review(s) selected
            </div>
            <div className="flex gap-2">
              <Button variant="primary" size="sm">Approve Selected</Button>
              <Button variant="danger" size="sm">Reject Selected</Button>
            </div>
          </div>
        )}

        {/* Review Items List */}
        <div className="divide-y divide-slate-200 dark:divide-slate-600">
          {isLoading ? (
            <div className="text-center p-16 text-slate-500 dark:text-slate-400">Loading reviews...</div>
          ) : filteredReviews.length === 0 ? (
            <div className="text-center p-16 text-slate-500 dark:text-slate-400">
              No reviews found matching your filters.
            </div>
          ) : (
            filteredReviews.map((review) => {
              const isSelected = selectedReviewIds.has(review.id);
              
              return (
                <div 
                  key={review.id} 
                  className={`p-4 flex items-center justify-between hover:bg-slate-50 dark:bg-slate-700/50 transition-colors ${isSelected ? 'bg-brand-primary/5' : ''}`}
                >
                  <div className="flex items-center gap-4 flex-1">
                    <input 
                      type="checkbox" 
                      checked={isSelected}
                      onChange={() => toggleSelectReview(review.id)}
                      className="rounded border-slate-300 dark:border-slate-500 text-brand-primary focus:ring-brand-primary"
                    />
                    
                    <div className="flex items-center gap-3 flex-1">
                      <ReviewStatusBadge status={review.status} priority={review.priority} />
                      
                      <div className="flex-1">
                        <div className="text-sm font-mono text-slate-900 dark:text-slate-50">{review.generationId}</div>
                        <div className="text-sm text-slate-600 dark:text-slate-300 truncate max-w-md">{review.prompt}</div>
                      </div>
                    </div>

                    {review.assignedTo && (
                      <div className="text-sm text-slate-500 dark:text-slate-400">
                        Assigned to: {review.assignedTo}
                      </div>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    <Button 
                      variant="secondary" 
                      size="sm"
                      onClick={() => handleViewReview(review.id)}
                    >
                      Review
                    </Button>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Summary Footer */}
        {!isLoading && filteredReviews.length > 0 && (
          <div className="px-6 py-4 border-t border-slate-200 dark:border-slate-600 text-sm text-slate-600 dark:text-slate-300">
            Showing {filteredReviews.length} of {reviews.length} reviews
          </div>
        )}
      </Card>

      {/* Review Detail Panel (Slide-over) */}
      {detailPanelOpen && selectedReviewId && (
        <HumanReviewDetailPanel 
          review={getSelectedReview()} 
          isOpen={detailPanelOpen}
          onClose={handleCloseDetailPanel}
          onApprove={handleApprove}
          onReject={handleReject}
        />
      )}
    </div>
  );
};

// Review Detail Panel Component (Slide-over)
interface HumanReviewDetailPanelProps {
  review: ReviewItem | undefined;
  isOpen: boolean;
  onClose: () => void;
  onApprove: (reviewId: string) => void;
  onReject: (reviewId: string) => void;
}

const HumanReviewDetailPanel: React.FC<HumanReviewDetailPanelProps> = ({ 
  review, 
  isOpen, 
  onClose,
  onApprove,
  onReject 
}) => {
  const [comment, setComment] = useState('');

  if (!isOpen || !review) return null;

  const handleApprove = () => {
    if (comment && comment.trim()) {
      // Add comment before approving
      onApprove(review.id);
    } else {
      onApprove(review.id);
    }
  };

  const handleReject = () => {
    if (!comment || !comment.trim()) {
      toast.error('Please provide rejection feedback');
      return;
    }
    onReject(review.id);
  };

  return (
    <div 
      className="fixed inset-0 bg-black/60 z-40 transition-opacity"
      onClick={onClose}
    >
      <div 
        className="fixed inset-y-0 right-0 w-full max-w-4xl bg-slate-900 z-50 shadow-2xl transform transition-transform ease-in-out duration-300"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-700 flex-shrink-0">
          <div>
            <h2 className="text-xl font-bold text-white">Review: {review.generationId}</h2>
            <div className="flex items-center gap-2 mt-1">
              <ReviewStatusBadge status={review.status} priority={review.priority} />
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-full text-slate-400 hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-brand-primary">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 p-6 overflow-y-auto space-y-6">
          {/* Original Prompt */}
          <Card>
            <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-2">Original Prompt</h3>
            <p className="text-slate-200">{review.prompt}</p>
          </Card>

          {/* Test Results */}
          {review.testResults && review.testResults.length > 0 && (
            <Card>
              <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">Automated Test Results</h3>
              <div className="space-y-2">
                {review.testResults.map((result, index) => (
                  <div key={index} className="flex items-center justify-between p-3 bg-slate-800 rounded-lg">
                    <span className="text-sm text-slate-200">{result.name}</span>
                    <span className={`text-xs font-semibold px-2 py-1 rounded ${
                      result.status === 'passed' 
                        ? 'bg-green-900 text-green-200' 
                        : 'bg-red-900 text-red-200'
                    }`}>
                      {result.status === 'passed' ? 'PASSED' : 'FAILED'}
                    </span>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Reviewer Comments */}
          <Card>
            <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-2">Reviewer Comments</h3>
            <textarea
              className="w-full h-32 px-3 py-2 bg-slate-800 border border-slate-700 rounded-md text-slate-200 placeholder-slate-500 dark:placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-primary"
              placeholder="Add your review comments here..."
              value={comment}
              onChange={(e) => setComment(e.target.value)}
            />
          </Card>

          {/* Review Actions */}
          <div className="flex gap-3">
            <Button variant="secondary" onClick={onClose}>Cancel</Button>
            <Button variant="danger" onClick={handleReject}>Reject with Comments</Button>
            <Button variant="primary" onClick={handleApprove}>Approve Generation</Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HumanReviewQueuePage;
