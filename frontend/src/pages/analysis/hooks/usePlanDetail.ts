import { useState, useEffect } from 'react';
import { message } from 'antd';
import api from '@/services/api';
import type { SceneChanges } from '@/components/analysis';

// Raw API response types
interface RawChange {
  id?: number;
  field: string;
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
  changes: RawChange[];
}

export interface PlanDetailData {
  id: number;
  name: string;
  description?: string;
  status: 'DRAFT' | 'REVIEWING' | 'APPLIED' | 'CANCELLED';
  created_at: string;
  updated_at: string;
  applied_at?: string;
  total_scenes: number;
  total_changes: number;
  metadata: {
    model?: string;
    temperature?: number;
    confidence_threshold?: number;
    options?: {
      detect_performers?: boolean;
      detect_studios?: boolean;
      detect_tags?: boolean;
      detect_details?: boolean;
      use_ai?: boolean;
    };
  };
  scenes: SceneChanges[];
}

export interface UsePlanDetailReturn {
  plan: PlanDetailData | null;
  loading: boolean;
  error: Error | null;
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
  getStatistics: () => {
    totalChanges: number;
    acceptedChanges: number;
    rejectedChanges: number;
    pendingChanges: number;
    acceptanceRate: number;
    averageConfidence: number;
  };
}

export function usePlanDetail(planId: number): UsePlanDetailReturn {
  const [plan, setPlan] = useState<PlanDetailData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

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

  useEffect(() => {
    if (planId) {
      void fetchPlan();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [planId]); // fetchPlan is stable

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
  const acceptAllChanges = (sceneId?: string) => {
    setPlan((prev) => {
      if (!prev) return null;

      return {
        ...prev,
        scenes: prev.scenes.map((scene) => {
          if (sceneId && scene.scene_id !== sceneId) return scene;

          return {
            ...scene,
            changes: scene.changes.map((change) => ({
              ...change,
              accepted: true,
              rejected: false,
            })),
          };
        }),
      };
    });
  };

  // Reject all changes for a scene or all scenes
  const rejectAllChanges = (sceneId?: string) => {
    setPlan((prev) => {
      if (!prev) return null;

      return {
        ...prev,
        scenes: prev.scenes.map((scene) => {
          if (sceneId && scene.scene_id !== sceneId) return scene;

          return {
            ...scene,
            changes: scene.changes.map((change) => ({
              ...change,
              accepted: false,
              rejected: true,
            })),
          };
        }),
      };
    });
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

  return {
    plan,
    loading,
    error,
    refresh: fetchPlan,
    updateChange,
    acceptChange,
    rejectChange,
    acceptAllChanges,
    rejectAllChanges,
    getStatistics,
  };
}
