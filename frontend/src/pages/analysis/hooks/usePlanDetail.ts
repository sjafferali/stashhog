import { useState, useEffect } from 'react';
import { message } from 'antd';
import api from '@/services/api';
import type { SceneChanges } from '@/components/analysis';
import type { CostResponse } from '@/types/models';

// Raw API response types
interface RawChange {
  id?: number;
  field: string;
  action?: string;
  current_value:
    | string
    | number
    | boolean
    | string[]
    | Record<string, unknown>
    | null;
  proposed_value:
    | string
    | number
    | boolean
    | string[]
    | Record<string, unknown>
    | null;
  confidence: number;
  applied?: boolean;
  rejected?: boolean;
}

interface RawScene {
  scene_id: string;
  scene_title?: string;
  scene_path?: string;
  changes: RawChange[];
}

export interface PlanDetailData {
  id: number;
  name: string;
  description?: string;
  status: 'draft' | 'reviewing' | 'applied' | 'cancelled';
  created_at: string;
  updated_at: string;
  applied_at?: string;
  total_scenes: number;
  total_changes: number;
  metadata: {
    model?: string;
    temperature?: number;
    confidence_threshold?: number;
    processing_time?: number;
    options?: {
      detect_performers?: boolean;
      detect_studios?: boolean;
      detect_tags?: boolean;
      detect_details?: boolean;
    };
  };
  scenes: SceneChanges[];
}

export interface UsePlanDetailReturn {
  plan: PlanDetailData | null;
  loading: boolean;
  error: Error | null;
  costs: CostResponse | null;
  costsLoading: boolean;
  refresh: () => Promise<void>;
  updateChange: (
    changeId: string,
    proposedValue:
      | string
      | number
      | boolean
      | string[]
      | Record<string, unknown>
      | null
  ) => Promise<void>;
  acceptChange: (changeId: string | number) => Promise<void>;
  rejectChange: (changeId: string | number) => Promise<void>;
  acceptAllChanges: (sceneId?: string) => void;
  rejectAllChanges: (sceneId?: string) => void;
  acceptByConfidence: (confidenceThreshold: number) => Promise<void>;
  acceptByField: (field: string) => Promise<void>;
  rejectByField: (field: string) => Promise<void>;
  cancelPlan: () => Promise<void>;
  getStatistics: () => {
    totalChanges: number;
    acceptedChanges: number;
    rejectedChanges: number;
    pendingChanges: number;
    acceptanceRate: number;
    averageConfidence: number;
  };
  getFieldCounts: () => {
    title: number;
    performers: number;
    tags: number;
    studio: number;
    details: number;
    date: number;
    markers: number;
  };
}

export function usePlanDetail(planId: number): UsePlanDetailReturn {
  const [plan, setPlan] = useState<PlanDetailData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [costs, setCosts] = useState<CostResponse | null>(null);
  const [costsLoading, setCostsLoading] = useState(false);

  // Helper function to determine field type
  const getFieldType = (
    field: string,
    value: unknown
  ): 'text' | 'array' | 'object' | 'date' | 'number' => {
    if (field === 'date') return 'date';
    if (field === 'rating' || field === 'duration') return 'number';
    if (Array.isArray(value)) return 'array';
    if (typeof value === 'object' && value !== null) return 'object';
    return 'text';
  };

  // Helper function to get field label
  const getFieldLabel = (field: string): string => {
    const labels: Record<string, string> = {
      title: 'Title',
      performers: 'Performers',
      tags: 'Tags',
      studio: 'Studio',
      details: 'Details',
      date: 'Date',
      rating: 'Rating',
      duration: 'Duration',
    };
    return labels[field] || field.charAt(0).toUpperCase() + field.slice(1);
  };

  // Fetch plan details
  const fetchPlan = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.get(`/analysis/plans/${planId}`);
      const rawData = response.data;

      // Transform the data to match expected format
      const transformedData: PlanDetailData = {
        ...rawData,
        scenes: rawData.scenes.map((scene: RawScene) => ({
          ...scene,
          changes: scene.changes.map((change: RawChange, index: number) => ({
            id: change.id || `${scene.scene_id}-${change.field}-${index}`,
            sceneId: scene.scene_id,
            field: change.field,
            fieldLabel: getFieldLabel(change.field),
            action: change.action as 'set' | 'add' | 'update' | undefined,
            currentValue: change.current_value,
            proposedValue: change.proposed_value,
            confidence: change.confidence,
            type: getFieldType(change.field, change.proposed_value),
            accepted: change.applied || false,
            rejected: change.rejected || false,
          })),
        })),
      };

      setPlan(transformedData);
    } catch (err) {
      setError(err as Error);
      void message.error('Failed to load plan details');
    } finally {
      setLoading(false);
    }
  };

  // Fetch plan costs
  const fetchCosts = async () => {
    try {
      setCostsLoading(true);
      const response = await api.get(`/analysis/plans/${planId}/costs`);
      setCosts(response.data);
    } catch (err) {
      // Don't show error message for costs - it's optional
      console.error('Failed to load plan costs:', err);
    } finally {
      setCostsLoading(false);
    }
  };

  useEffect(() => {
    if (planId) {
      void fetchPlan();
      void fetchCosts();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [planId]); // fetchPlan and fetchCosts are stable

  // Update a specific change
  const updateChange = async (
    changeId: string,
    proposedValue:
      | string
      | number
      | boolean
      | string[]
      | Record<string, unknown>
      | null
  ) => {
    try {
      await api.patch(`/analysis/changes/${changeId}`, {
        proposed_value: proposedValue,
      });

      // Update local state
      setPlan((prev) => {
        if (!prev) return null;

        return {
          ...prev,
          scenes: prev.scenes.map((scene) => ({
            ...scene,
            changes: scene.changes.map((change) =>
              change.id === changeId
                ? { ...change, proposedValue, editedValue: proposedValue }
                : change
            ),
          })),
        };
      });

      void message.success('Change updated');
    } catch (err) {
      void message.error('Failed to update change');
      throw err;
    }
  };

  // Accept a change
  const acceptChange = async (changeId: string | number) => {
    try {
      // Use the ID directly if it's numeric, otherwise extract from composite ID
      const numericId =
        typeof changeId === 'number' ? changeId : parseInt(changeId);

      // Update on server
      await api.patch(`/analysis/changes/${numericId}/status`, {
        accepted: true,
        rejected: false,
      });

      // Update local state
      setPlan((prev) => {
        if (!prev) return null;

        return {
          ...prev,
          scenes: prev.scenes.map((scene) => ({
            ...scene,
            changes: scene.changes.map((change) =>
              String(change.id) === String(changeId)
                ? { ...change, accepted: true, rejected: false }
                : change
            ),
          })),
        };
      });
    } catch (err) {
      void message.error('Failed to accept change');
      throw err;
    }
  };

  // Reject a change
  const rejectChange = async (changeId: string | number) => {
    try {
      // Use the ID directly if it's numeric, otherwise extract from composite ID
      const numericId =
        typeof changeId === 'number' ? changeId : parseInt(changeId);

      // Update on server
      await api.patch(`/analysis/changes/${numericId}/status`, {
        accepted: false,
        rejected: true,
      });

      // Update local state
      setPlan((prev) => {
        if (!prev) return null;

        return {
          ...prev,
          scenes: prev.scenes.map((scene) => ({
            ...scene,
            changes: scene.changes.map((change) =>
              String(change.id) === String(changeId)
                ? { ...change, accepted: false, rejected: true }
                : change
            ),
          })),
        };
      });
    } catch (err) {
      void message.error('Failed to reject change');
      throw err;
    }
  };

  // Accept all changes for a scene or all scenes
  const acceptAllChanges = async (sceneId?: string) => {
    try {
      const response = await api.post(`/analysis/plans/${planId}/bulk-update`, {
        action: 'accept_all',
        scene_id: sceneId,
      });

      // Refresh plan data to get updated statuses
      await fetchPlan();

      void message.success(`${response.data.updated_count} changes accepted`);
    } catch (err) {
      void message.error('Failed to accept changes');
      throw err;
    }
  };

  // Reject all changes for a scene or all scenes
  const rejectAllChanges = async (sceneId?: string) => {
    try {
      const response = await api.post(`/analysis/plans/${planId}/bulk-update`, {
        action: 'reject_all',
        scene_id: sceneId,
      });

      // Refresh plan data to get updated statuses
      await fetchPlan();

      void message.success(`${response.data.updated_count} changes rejected`);
    } catch (err) {
      void message.error('Failed to reject changes');
      throw err;
    }
  };

  // Accept changes by confidence threshold
  const acceptByConfidence = async (confidenceThreshold: number) => {
    try {
      const response = await api.post(`/analysis/plans/${planId}/bulk-update`, {
        action: 'accept_by_confidence',
        confidence_threshold: confidenceThreshold,
      });

      // Refresh plan data to get updated statuses
      await fetchPlan();

      void message.success(
        `${response.data.updated_count} changes accepted with confidence ≥ ${(confidenceThreshold * 100).toFixed(0)}%`
      );
    } catch (err) {
      void message.error('Failed to accept changes by confidence');
      throw err;
    }
  };

  // Accept changes by field
  const acceptByField = async (field: string) => {
    try {
      const response = await api.post(`/analysis/plans/${planId}/bulk-update`, {
        action: 'accept_by_field',
        field: field,
      });

      // Refresh plan data to get updated statuses
      await fetchPlan();

      void message.success(
        `${response.data.updated_count} ${field} changes accepted`
      );
    } catch (err) {
      void message.error(`Failed to accept ${field} changes`);
      throw err;
    }
  };

  // Reject changes by field
  const rejectByField = async (field: string) => {
    try {
      const response = await api.post(`/analysis/plans/${planId}/bulk-update`, {
        action: 'reject_by_field',
        field: field,
      });

      // Refresh plan data to get updated statuses
      await fetchPlan();

      void message.success(
        `${response.data.updated_count} ${field} changes rejected`
      );
    } catch (err) {
      void message.error(`Failed to reject ${field} changes`);
      throw err;
    }
  };

  // Cancel the plan
  const cancelPlan = async () => {
    try {
      await api.patch(`/analysis/plans/${planId}/cancel`);

      // Refresh plan data to get updated status
      await fetchPlan();

      void message.success('Plan cancelled');
    } catch (err) {
      void message.error('Failed to cancel plan');
      throw err;
    }
  };

  // Calculate statistics
  const getStatistics = () => {
    if (!plan) {
      return {
        totalChanges: 0,
        acceptedChanges: 0,
        rejectedChanges: 0,
        pendingChanges: 0,
        acceptanceRate: 0,
        averageConfidence: 0,
      };
    }

    let totalChanges = 0;
    let acceptedChanges = 0;
    let rejectedChanges = 0;
    let totalConfidence = 0;

    plan.scenes.forEach((scene) => {
      scene.changes.forEach((change) => {
        totalChanges++;
        if (change.accepted) acceptedChanges++;
        else if (change.rejected) rejectedChanges++;
        totalConfidence += change.confidence;
      });
    });

    const pendingChanges = totalChanges - acceptedChanges - rejectedChanges;
    const acceptanceRate =
      totalChanges > 0 ? (acceptedChanges / totalChanges) * 100 : 0;
    const averageConfidence =
      totalChanges > 0 ? totalConfidence / totalChanges : 0;

    return {
      totalChanges,
      acceptedChanges,
      rejectedChanges,
      pendingChanges,
      acceptanceRate,
      averageConfidence,
    };
  };

  // Get field counts for bulk actions
  const getFieldCounts = () => {
    const counts = {
      title: 0,
      performers: 0,
      tags: 0,
      studio: 0,
      details: 0,
      date: 0,
      markers: 0,
    };

    if (!plan) return counts;

    plan.scenes.forEach((scene) => {
      scene.changes.forEach((change) => {
        if (!change.accepted && !change.rejected) {
          const field = change.field as keyof typeof counts;
          if (field in counts) {
            counts[field]++;
          }
        }
      });
    });

    return counts;
  };

  return {
    plan,
    loading,
    error,
    costs,
    costsLoading,
    refresh: fetchPlan,
    updateChange,
    acceptChange,
    rejectChange,
    acceptAllChanges: (...args: Parameters<typeof acceptAllChanges>) =>
      void acceptAllChanges(...args),
    rejectAllChanges: (...args: Parameters<typeof rejectAllChanges>) =>
      void rejectAllChanges(...args),
    acceptByConfidence,
    acceptByField,
    rejectByField,
    cancelPlan,
    getStatistics,
    getFieldCounts,
  };
}
