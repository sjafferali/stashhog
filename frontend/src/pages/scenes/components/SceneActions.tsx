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
} from 'antd';
import {
  ExperimentOutlined,
  ExportOutlined,
  ClearOutlined,
  DownOutlined,
  PlusOutlined,
  MinusOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from 'react-query';
import api from '@/services/api';
import { useScenesStore } from '@/store/slices/scenes';
import { Tag as TagType } from '@/types/models';
import { exportToCSV, exportToJSON } from '../utils/export';
import {
  AnalysisTypeSelector,
  AnalysisTypeOptions,
} from '@/components/forms/AnalysisTypeSelector';
import type { MenuProps } from 'antd';

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
  const [analysisOptions, setAnalysisOptions] = useState<AnalysisTypeOptions>({
    detectPerformers: true,
    detectStudios: true,
    detectTags: true,
    detectDetails: false,
    detectVideoTags: false,
    useAi: true,
  });
  const [analysisModalVisible, setAnalysisModalVisible] = useState(false);
  const [tempAnalysisOptions, setTempAnalysisOptions] =
    useState<AnalysisTypeOptions>({
      detectPerformers: true,
      detectStudios: true,
      detectTags: true,
      detectDetails: false,
      detectVideoTags: false,
      useAi: true,
    });

  // Fetch tags for the modal
  const { data: tags } = useQuery<TagType[]>('tags', async () => {
    const response = await api.get('/entities/tags', {
      params: { size: 1000 },
    });
    return response.data.items;
  });

  // Video tags mutation
  const videoTagsMutation = useMutation(
    async ({
      sceneIds,
      options,
    }: {
      sceneIds: string[];
      options: AnalysisTypeOptions;
    }) => {
      const response = await api.post('/analysis/video-tags', {
        scene_ids: sceneIds,
        options,
        background: true,
      });
      return response.data;
    },
    {
      onSuccess: (_data) => {
        void message.success('Video tag analysis started');
        onClearSelection();
        void queryClient.invalidateQueries('jobs');
      },
      onError: () => {
        void message.error('Failed to start video tag analysis');
      },
    }
  );

  // Analyze mutation
  const analyzeMutation = useMutation(
    async ({
      sceneIds,
      options,
    }: {
      sceneIds: string[];
      options: AnalysisTypeOptions;
    }) => {
      const response = await api.post('/analysis/generate', {
        scene_ids: sceneIds,
        plan_name: `Bulk Analysis - ${sceneIds.length} scenes - ${new Date().toISOString()}`,
        options: {
          detect_performers: options.detectPerformers,
          detect_studios: options.detectStudios,
          detect_tags: options.detectTags,
          detect_details: options.detectDetails,
          use_ai: options.useAi,
          confidence_threshold: 0.7,
        },
      });
      return response.data;
    },
    {
      onSuccess: () => {
        void message.success(`Started analysis for ${selectedCount} scenes`);
        onClearSelection();
        void queryClient.invalidateQueries('jobs');
      },
      onError: () => {
        void message.error('Failed to start analysis');
      },
    }
  );

  // Sync mutation
  const syncMutation = useMutation(
    async (sceneIds: string[]) => {
      const response = await api.post('/scenes/resync-bulk', sceneIds, {
        params: { background: true },
      });
      return response.data;
    },
    {
      onSuccess: () => {
        void message.success(`Started sync for ${selectedCount} scenes`);
        onClearSelection();
        void queryClient.invalidateQueries('jobs');
      },
      onError: () => {
        void message.error('Failed to start sync');
      },
    }
  );

  // Tag mutation
  const tagMutation = useMutation(
    async ({
      sceneIds,
      tagIds,
      action,
    }: {
      sceneIds: string[];
      tagIds: number[];
      action: 'add' | 'remove';
    }) => {
      const endpoint =
        action === 'add' ? '/scenes/add-tags' : '/scenes/remove-tags';
      const response = await api.post(endpoint, {
        scene_ids: sceneIds.map((id) => parseInt(id, 10)),
        tag_ids: tagIds,
      });
      return response.data;
    },
    {
      onSuccess: (_, variables) => {
        void message.success(
          `${variables.action === 'add' ? 'Added' : 'Removed'} tags for ${selectedCount} scenes`
        );
        onClearSelection();
        void queryClient.invalidateQueries('scenes');
      },
      onError: () => {
        void message.error('Failed to update tags');
      },
    }
  );

  const handleAnalyze = () => {
    setTempAnalysisOptions(analysisOptions);
    setAnalysisModalVisible(true);
  };

  const handleAnalysisModalOk = () => {
    setAnalysisOptions(tempAnalysisOptions);

    // Check if only video tags is selected
    const isVideoTagsOnly =
      tempAnalysisOptions.detectVideoTags &&
      !tempAnalysisOptions.detectPerformers &&
      !tempAnalysisOptions.detectStudios &&
      !tempAnalysisOptions.detectTags &&
      !tempAnalysisOptions.detectDetails;

    if (isVideoTagsOnly) {
      // Use video tags endpoint for immediate application
      videoTagsMutation.mutate({
        sceneIds: Array.from(selectedScenes),
        options: tempAnalysisOptions,
      });
    } else {
      // Use regular analysis endpoint
      analyzeMutation.mutate({
        sceneIds: Array.from(selectedScenes),
        options: tempAnalysisOptions,
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

    tagMutation.mutate({
      sceneIds: Array.from(selectedScenes),
      tagIds: selectedTags.map((id) => parseInt(id, 10)),
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

  const bulkActions: MenuProps['items'] = [
    {
      key: 'add-tags',
      label: 'Add Tags',
      icon: <PlusOutlined />,
      onClick: () => {
        setTagAction('add');
        handleTagAction();
      },
    },
    {
      key: 'remove-tags',
      label: 'Remove Tags',
      icon: <MinusOutlined />,
      onClick: () => {
        setTagAction('remove');
        handleTagAction();
      },
    },
    {
      type: 'divider',
    },
    {
      key: 'export-csv',
      label: 'Export as CSV',
      icon: <ExportOutlined />,
      onClick: () => void handleExport('csv'),
    },
    {
      key: 'export-json',
      label: 'Export as JSON',
      icon: <ExportOutlined />,
      onClick: () => void handleExport('json'),
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
              loading={syncMutation.isLoading}
            >
              Sync Selected
            </Button>

            <Button
              icon={<ExperimentOutlined />}
              onClick={handleAnalyze}
              loading={analyzeMutation.isLoading}
            >
              Analyze Selected
            </Button>

            <Dropdown menu={{ items: bulkActions }}>
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
        confirmLoading={tagMutation.isLoading}
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
        }}
        confirmLoading={analyzeMutation.isLoading}
        width={500}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <p>
            Analyze {selectedCount} selected scenes with the following options:
          </p>
          <AnalysisTypeSelector
            value={tempAnalysisOptions}
            onChange={setTempAnalysisOptions}
          />
        </Space>
      </Modal>
    </>
  );
};
