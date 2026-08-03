import React, { useMemo } from 'react';
import ResourceImpactSummary from './ResourceImpactSummary';
import type { DiffResource } from './DiffPanel';

interface DeploymentImpactSummaryProps {
  planJson?: string;
  hasPermission?: boolean;
  onResourceSelect?: (address: string) => void;
  className?: string;
}

export const DeploymentImpactSummary: React.FC<DeploymentImpactSummaryProps> = ({
  planJson,
  hasPermission = true,
  onResourceSelect,
  className = '',
}) => {
  const parsedResources = useMemo<DiffResource[]>(() => {
    if (!planJson) return [];
    
    try {
      // Find the line that looks like a valid terraform plan output
      // OpenTofu plan JSON is often a stream of JSON objects separated by newlines.
      // We look for the one containing resource_changes or just parse it if it's a single object.
      
      const lines = planJson.split('\n');
      let planObj: any = null;
      
      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const obj = JSON.parse(line);
          if (obj && obj.resource_changes) {
            planObj = obj;
            break;
          }
        } catch (e) {
          // ignore parsing error for individual lines
        }
      }
      
      // If we didn't find it line by line, try parsing the whole string
      if (!planObj) {
        const obj = JSON.parse(planJson);
        if (obj && obj.resource_changes) {
          planObj = obj;
        }
      }

      if (!planObj || !Array.isArray(planObj.resource_changes)) {
        return [];
      }

      return planObj.resource_changes.map((change: any): DiffResource => {
        const actions = change.change?.actions || [];
        
        let action: DiffResource['action'] = 'update';
        if (actions.includes('create')) action = 'create';
        else if (actions.includes('delete') || actions.includes('destroy')) action = 'destroy';

        return {
          address: change.address || 'unknown',
          type: change.type || 'unknown',
          name: change.name || 'unknown',
          action,
          provider: change.provider_name || 'unknown',
          costDelta: 0, // Would need infracost integration
          changes: {}, // Can map change.before/after if needed
        };
      });
    } catch (e) {
      console.error('Failed to parse OpenTofu plan JSON:', e);
      return [];
    }
  }, [planJson]);

  return (
    <ResourceImpactSummary
      resources={parsedResources}
      showCostImpact={true}
      onResourceSelect={onResourceSelect}
      hasPermission={hasPermission}
      className={className}
    />
  );
};

export default DeploymentImpactSummary;
