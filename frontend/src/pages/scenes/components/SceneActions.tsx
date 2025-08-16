import React, { useState } from 'react';
import {
  Card,
  Space,
  Button,
  Dropdown,
  Modal,
  Select,
  message,
  Tag,
  Radio,
} from 'antd';
import {
  ExperimentOutlined,
  ExportOutlined,
  ClearOutlined,
  DownOutlined,
  PlusOutlined,
  MinusOutlined,
  SyncOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  VideoCameraOutlined,
  DatabaseOutlined,
  RobotOutlined,
} from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from '@/services/api';
import { useScenesStore } from '@/store/slices/scenes';
import { Tag as TagType } from '@/types/models';
import { exportToCSV, exportToJSON } from '../utils/export';
import {
  AnalysisTypeSelector,
  AnalysisTypeOptions,
  hasAtLeastOneAnalysisTypeSelected,
} from '@/components/forms/AnalysisTypeSelector';
import type { MenuProps, RadioChangeEvent } from 'antd';

interface SceneActionsProps {
  selectedCount: number;
  onClearSelection: () => void;
}

export const SceneActions: React.FC<SceneActionsProps> = ({
  selectedCount,
  onClearSelection,
}) => {
  const { selectedScenes } = useScenesStore();
  const queryClient = useQueryClient();
  const [tagModalVisible, setTagModalVisible] = useState(false);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [tagAction, setTagAction] = useState<'add' | 'remove'>('add');

  // State for bulk update confirmation modal
  const [bulkUpdateModalVisible, setBulkUpdateModalVisible] = useState(false);
  const [pendingBulkUpdate, setPendingBulkUpdate] = useState<{
    field: 'analyzed' | 'video_analyzed' | 'generated';
    value: boolean;
  } | null>(null);
  const [analysisOptions, setAnalysisOptions] = useState<AnalysisTypeOptions>({
    detectPerformers: true,
    detectStudios: true,
    detectTags: true,
    detectDetails: false,
    detectVideoTags: false,
  });
  const [analysisModalVisible, setAnalysisModalVisible] = useState(false);
  const [analysisType, setAnalysisType] = useState<'ai' | 'non-ai'>('ai');
  const [tempAnalysisOptions, setTempAnalysisOptions] =
    useState<AnalysisTypeOptions>({
      detectPerformers: true,
      detectStudios: true,
      detectTags: true,
      detectDetails: false,
      detectVideoTags: false,
    });

  // Fetch tags for the modal
  const { data: tags } = useQuery<TagType[]>({
    queryKey: ['tags'],
    queryFn: async () => {
      const response = await api.get('/entities/tags');
      // The backend returns a direct array, not a paginated response
      return response.data;
    },
  });

  // Note: Video tags mutation removed - now handled through regular analysis endpoint

  // Analyze mutation
  const analyzeMutation = useMutation({
    mutationFn: async ({
      sceneIds,
      options,
      type,
    }: {
      sceneIds: string[];
      options: AnalysisTypeOptions;
      type: 'ai' | 'non-ai';
    }) => {
      const endpoint =
        type === 'ai' ? '/analysis/generate' : '/analysis/generate-non-ai';
      const response = await api.post(
        endpoint,
        {
          scene_ids: sceneIds,
          plan_name: `${type === 'ai' ? 'AI' : 'Non-AI'} Analysis - ${sceneIds.length} scenes - ${new Date().toISOString()}`,
          options: {
            detect_performers: options.detectPerformers,
            detect_studios: options.detectStudios,
            detect_tags: options.detectTags,
            detect_details: options.detectDetails,
            detect_video_tags: options.detectVideoTags,
            confidence_threshold: 0.7,
          },
        },
        {
          params: { background: true },
        }
      );
      return response.data;
    },
    onSuccess: (data) => {
      if (data.job_id) {
        void message.success(
          `Analysis job queued (Job ID: ${data.job_id}) for ${selectedCount} scenes`
        );
      } else if (data.plan_id) {
        void message.success(
          `Created analysis plan ${data.plan_id} for ${selectedCount} scenes`
        );
      } else {
        void message.success(`Started analysis for ${selectedCount} scenes`);
      }
      onClearSelection();
      void queryClient.invalidateQueries({ queryKey: ['jobs'] });
      void queryClient.invalidateQueries({ queryKey: ['plans'] });
    },
    onError: (error) => {
      console.error('Analysis error:', error);
      void message.error('Failed to start analysis');
    },
  });

  // Sync mutation
  const syncMutation = useMutation({
    mutationFn: async (sceneIds: string[]) => {
      const response = await api.post('/scenes/resync-bulk', sceneIds, {
        params: { background: true },
      });
      return response.data;
    },
    onSuccess: () => {
      void message.success(`Started sync for ${selectedCount} scenes`);
      onClearSelection();
      void queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
    onError: () => {
      void message.error('Failed to start sync');
    },
  });

  // Tag mutation
  const tagMutation = useMutation({
    mutationFn: async ({
      sceneIds,
      tagIds,
      action,
    }: {
      sceneIds: number[];
      tagIds: number[];
      action: 'add' | 'remove';
    }) => {
      const endpoint =
        action === 'add' ? '/scenes/add-tags' : '/scenes/remove-tags';
      const response = await api.post(endpoint, {
        scene_ids: sceneIds,
        tag_ids: tagIds,
      });
      return response.data;
    },
    onSuccess: (_, variables) => {
      void message.success(
        `${variables.action === 'add' ? 'Added' : 'Removed'} tags for ${selectedCount} scenes`
      );
      onClearSelection();
      void queryClient.invalidateQueries({ queryKey: ['scenes'] });
    },
    onError: () => {
      void message.error('Failed to update tags');
    },
  });

  // Bulk update mutation for analyzed status
  const bulkUpdateMutation = useMutation({
    mutationFn: async ({
      sceneIds,
      updates,
    }: {
      sceneIds: string[];
      updates: {
        analyzed?: boolean;
        video_analyzed?: boolean;
        generated?: boolean;
      };
    }) => {
      const response = await api.patch('/scenes/bulk-update', {
        scene_ids: sceneIds,
        updates,
      });
      return response.data;
    },
    onSuccess: (data, variables) => {
      const updateMessages = [];
      if (variables.updates.analyzed !== undefined) {
        updateMessages.push(
          `${variables.updates.analyzed ? 'Set' : 'Unset'} analyzed status`
        );
      }
      if (variables.updates.video_analyzed !== undefined) {
        updateMessages.push(
          `${variables.updates.video_analyzed ? 'Set' : 'Unset'} video analyzed status`
        );
      }
      if (variables.updates.generated !== undefined) {
        updateMessages.push(
          `${variables.updates.generated ? 'Set' : 'Unset'} generated status`
        );
      }
      void message.success(
        `${updateMessages.join(' and ')} for ${data.updated_count} scenes`
      );
      onClearSelection();
      void queryClient.invalidateQueries({ queryKey: ['scenes'] });
    },
    onError: () => {
      void message.error('Failed to update scene attributes');
    },
  });

  const handleAnalyze = () => {
    setTempAnalysisOptions(analysisOptions);
    setAnalysisModalVisible(true);
  };

  const handleAnalysisModalOk = () => {
    setAnalysisOptions(tempAnalysisOptions);

    // For non-AI analysis, only performers detection is available
    const effectiveOptions =
      analysisType === 'non-ai'
        ? {
            ...tempAnalysisOptions,
            detectStudios: false,
            detectTags: false,
            detectDetails: false,
            detectVideoTags: false,
          }
        : tempAnalysisOptions;

    // Check if any analysis options are selected
    if (
      effectiveOptions.detectPerformers ||
      effectiveOptions.detectStudios ||
      effectiveOptions.detectTags ||
      effectiveOptions.detectDetails ||
      effectiveOptions.detectVideoTags
    ) {
      // Use regular analysis endpoint for all options including video tags
      analyzeMutation.mutate({
        sceneIds: Array.from(selectedScenes),
        options: effectiveOptions,
        type: analysisType,
      });
    }

    setAnalysisModalVisible(false);
  };

  const handleSync = () => {
    Modal.confirm({
      title: 'Sync Scenes',
      content: `Are you sure you want to sync ${selectedCount} selected scenes from Stash?`,
      onOk: () => {
        syncMutation.mutate(Array.from(selectedScenes));
      },
    });
  };

  const handleTagAction = () => {
    setTagModalVisible(true);
  };

  const handleTagModalOk = () => {
    if (selectedTags.length === 0) {
      void message.warning('Please select at least one tag');
      return;
    }

    const sceneIds = Array.from(selectedScenes).map((id) => parseInt(id, 10));
    const tagIds = selectedTags.map((id) => parseInt(id, 10));

    tagMutation.mutate({
      sceneIds,
      tagIds,
      action: tagAction,
    });

    setTagModalVisible(false);
    setSelectedTags([]);
  };

  const handleExport = async (format: 'csv' | 'json') => {
    try {
      // Fetch full scene data for selected scenes
      const selectedIds = Array.from(selectedScenes).map((id) =>
        parseInt(id, 10)
      );
      const response = await api.post('/scenes/bulk-fetch', {
        ids: selectedIds,
      });
      const scenes = response.data;

      if (format === 'csv') {
        exportToCSV(scenes, 'scenes-export');
      } else {
        exportToJSON(scenes, 'scenes-export');
      }

      void message.success(
        `Exported ${selectedCount} scenes to ${format.toUpperCase()}`
      );
    } catch (error) {
      void message.error(
        `Failed to export scenes: ${(error as Error).message}`
      );
    }
  };

  const handleBulkAnalyzedUpdate = (
    field: 'analyzed' | 'video_analyzed' | 'generated',
    value: boolean
  ) => {
    // Use controlled modal instead of Modal.confirm
    setPendingBulkUpdate({ field, value });
    setBulkUpdateModalVisible(true);
  };

  const handleBulkUpdateConfirm = () => {
    if (!pendingBulkUpdate) return;

    bulkUpdateMutation.mutate({
      sceneIds: Array.from(selectedScenes),
      updates: { [pendingBulkUpdate.field]: pendingBulkUpdate.value },
    });

    setBulkUpdateModalVisible(false);
    setPendingBulkUpdate(null);
  };

  const handleBulkUpdateCancel = () => {
    setBulkUpdateModalVisible(false);
    setPendingBulkUpdate(null);
  };

  const handleMenuClick: MenuProps['onClick'] = ({ key }) => {
    switch (key) {
      case 'add-tags':
        setTagAction('add');
        handleTagAction();
        break;
      case 'remove-tags':
        setTagAction('remove');
        handleTagAction();
        break;
      case 'set-analyzed':
        handleBulkAnalyzedUpdate('analyzed', true);
        break;
      case 'unset-analyzed':
        handleBulkAnalyzedUpdate('analyzed', false);
        break;
      case 'set-video-analyzed':
        handleBulkAnalyzedUpdate('video_analyzed', true);
        break;
      case 'unset-video-analyzed':
        handleBulkAnalyzedUpdate('video_analyzed', false);
        break;
      case 'set-generated':
        handleBulkAnalyzedUpdate('generated', true);
        break;
      case 'unset-generated':
        handleBulkAnalyzedUpdate('generated', false);
        break;
      case 'export-csv':
        void handleExport('csv');
        break;
      case 'export-json':
        void handleExport('json');
        break;
    }
  };

  const bulkActions: MenuProps['items'] = [
    {
      key: 'add-tags',
      label: 'Add Tags',
      icon: <PlusOutlined />,
    },
    {
      key: 'remove-tags',
      label: 'Remove Tags',
      icon: <MinusOutlined />,
    },
    {
      type: 'divider',
    },
    {
      key: 'set-analyzed',
      label: 'Set Analyzed',
      icon: <CheckCircleOutlined />,
    },
    {
      key: 'unset-analyzed',
      label: 'Unset Analyzed',
      icon: <CloseCircleOutlined />,
    },
    {
      type: 'divider',
    },
    {
      key: 'set-video-analyzed',
      label: 'Set Video Analyzed',
      icon: <VideoCameraOutlined />,
    },
    {
      key: 'unset-video-analyzed',
      label: 'Unset Video Analyzed',
      icon: <CloseCircleOutlined />,
    },
    {
      type: 'divider',
    },
    {
      key: 'set-generated',
      label: 'Set Generated',
      icon: <RobotOutlined />,
    },
    {
      key: 'unset-generated',
      label: 'Unset Generated',
      icon: <CloseCircleOutlined />,
    },
    {
      type: 'divider',
    },
    {
      key: 'export-csv',
      label: 'Export as CSV',
      icon: <ExportOutlined />,
    },
    {
      key: 'export-json',
      label: 'Export as JSON',
      icon: <ExportOutlined />,
    },
  ];

  return (
    <>
      <Card size="small">
        <Space
          size="middle"
          style={{ width: '100%', justifyContent: 'space-between' }}
        >
          <Space>
            <Tag color="blue">{selectedCount} selected</Tag>

            <Button
              icon={<SyncOutlined />}
              onClick={handleSync}
              loading={syncMutation.isPending}
            >
              Sync Selected
            </Button>

            <Button
              icon={<ExperimentOutlined />}
              onClick={handleAnalyze}
              loading={analyzeMutation.isPending}
            >
              Analyze Selected
            </Button>

            <Dropdown menu={{ items: bulkActions, onClick: handleMenuClick }}>
              <Button>
                <Space>
                  More Actions
                  <DownOutlined />
                </Space>
              </Button>
            </Dropdown>
          </Space>

          <Button icon={<ClearOutlined />} onClick={onClearSelection} danger>
            Clear Selection
          </Button>
        </Space>
      </Card>

      <Modal
        title={`${tagAction === 'add' ? 'Add' : 'Remove'} Tags`}
        open={tagModalVisible}
        onOk={handleTagModalOk}
        onCancel={() => {
          setTagModalVisible(false);
          setSelectedTags([]);
        }}
        confirmLoading={tagMutation.isPending}
      >
        <p>
          Select tags to {tagAction} {tagAction === 'add' ? 'to' : 'from'}{' '}
          {selectedCount} selected scenes:
        </p>
        <Select
          mode="multiple"
          placeholder={`Select tags to ${tagAction}...`}
          value={selectedTags}
          onChange={(value: string[]) => setSelectedTags(value)}
          style={{ width: '100%' }}
          filterOption={
            ((
              input: string,
              option?: any // eslint-disable-line @typescript-eslint/no-explicit-any
            ) =>
              (typeof option?.label === 'string' &&
                option.label.toLowerCase().includes(input.toLowerCase())) ||
              false) as any // eslint-disable-line @typescript-eslint/no-explicit-any
          }
          options={
            tags?.map((t) => ({
              label: t.name,
              value: t.id.toString(),
            })) as any // eslint-disable-line @typescript-eslint/no-explicit-any
          }
        />
      </Modal>

      <Modal
        title="Analyze Scenes"
        open={analysisModalVisible}
        onOk={handleAnalysisModalOk}
        onCancel={() => {
          setAnalysisModalVisible(false);
          setTempAnalysisOptions(analysisOptions);
          setAnalysisType('ai');
        }}
        confirmLoading={analyzeMutation.isPending}
        okButtonProps={{
          disabled:
            analysisType === 'ai'
              ? !hasAtLeastOneAnalysisTypeSelected(tempAnalysisOptions)
              : !tempAnalysisOptions.detectPerformers,
        }}
        width={500}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <p>Analyze {selectedCount} selected scenes:</p>

          <div>
            <div style={{ marginBottom: '12px' }}>
              <strong>Analysis Type:</strong>
            </div>
            <Radio.Group
              value={analysisType}
              onChange={(e: RadioChangeEvent) =>
                setAnalysisType(e.target.value as 'ai' | 'non-ai')
              }
              style={{ width: '100%' }}
            >
              <Space direction="vertical" style={{ width: '100%' }}>
                <Radio value="ai">
                  <Space>
                    <RobotOutlined />
                    <span>AI Analysis</span>
                  </Space>
                  <div
                    style={{
                      marginLeft: '24px',
                      fontSize: '12px',
                      color: '#666',
                    }}
                  >
                    Uses OpenAI to detect performers, tags, studios, and
                    generate descriptions
                  </div>
                </Radio>
                <Radio value="non-ai">
                  <Space>
                    <DatabaseOutlined />
                    <span>Non-AI Analysis (Path-based)</span>
                  </Space>
                  <div
                    style={{
                      marginLeft: '24px',
                      fontSize: '12px',
                      color: '#666',
                    }}
                  >
                    Fast detection from file paths, no API costs, performers
                    only
                  </div>
                </Radio>
              </Space>
            </Radio.Group>
          </div>

          {analysisType === 'ai' ? (
            <AnalysisTypeSelector
              value={tempAnalysisOptions}
              onChange={setTempAnalysisOptions}
            />
          ) : (
            <div
              style={{
                padding: '12px',
                background: '#f0f0f0',
                borderRadius: '4px',
              }}
            >
              <Space direction="vertical">
                <div>
                  <strong>Non-AI analysis will:</strong>
                </div>
                <ul style={{ margin: '8px 0', paddingLeft: '20px' }}>
                  <li>Detect performers from file paths and directory names</li>
                  <li>Match against OFScraper directory structure</li>
                  <li>Clean HTML from scene details</li>
                </ul>
                <div style={{ fontSize: '12px', color: '#666' }}>
                  Note: Scenes will NOT be marked as analyzed, allowing AI
                  analysis later
                </div>
              </Space>
            </div>
          )}
        </Space>
      </Modal>

      {/* Bulk Update Confirmation Modal */}
      <Modal
        title={
          pendingBulkUpdate
            ? `${pendingBulkUpdate.value ? 'Set' : 'Unset'} ${
                pendingBulkUpdate.field === 'analyzed'
                  ? 'Analyzed'
                  : 'Video Analyzed'
              } Status`
            : 'Bulk Update'
        }
        open={bulkUpdateModalVisible}
        onOk={handleBulkUpdateConfirm}
        onCancel={handleBulkUpdateCancel}
        confirmLoading={bulkUpdateMutation.isPending}
      >
        <p>
          Are you sure you want to {pendingBulkUpdate?.value ? 'set' : 'unset'}{' '}
          the{' '}
          {pendingBulkUpdate?.field === 'analyzed'
            ? 'Analyzed'
            : 'Video Analyzed'}{' '}
          status for {selectedCount} selected scenes?
        </p>
      </Modal>
    </>
  );
};
