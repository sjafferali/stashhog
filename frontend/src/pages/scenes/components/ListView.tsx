import React, { useMemo, useCallback, MouseEvent, useState } from 'react';
import {
  Table,
  Tag,
  Space,
  Button,
  Checkbox,
  Typography,
  Tooltip,
  Modal,
  message,
} from 'antd';
import type { CheckboxChangeEvent } from '@/types/antd-proper';
import {
  EyeOutlined,
  ExperimentOutlined,
  CheckCircleOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import { ColumnsType } from 'antd/es/table';
import type {
  TablePaginationConfig,
  SorterResult,
  FilterValue,
} from '@/types/antd-proper';
import { useSearchParams } from 'react-router-dom';
import { Scene } from '@/types/models';
import { useScenesStore } from '@/store/slices/scenes';
import { useMutation, useQueryClient } from 'react-query';
import dayjs from 'dayjs';
import api from '@/services/api';
import { SceneThumbnail } from '@/components/common/SceneThumbnail';
import {
  AnalysisTypeSelector,
  AnalysisTypeOptions,
} from '@/components/forms/AnalysisTypeSelector';

const { Text } = Typography;

interface ListViewProps {
  scenes: Scene[];
  onSceneSelect: (scene: Scene) => void;
}

const formatDuration = (seconds?: number): string => {
  if (!seconds) return 'N/A';
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);

  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${minutes}:${secs.toString().padStart(2, '0')}`;
};

export const ListView: React.FC<ListViewProps> = ({
  scenes,
  onSceneSelect,
}) => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [analysisOptions, setAnalysisOptions] = useState<AnalysisTypeOptions>({
    detectPerformers: true,
    detectStudios: true,
    detectTags: true,
    detectDetails: false,
    useAi: true,
  });
  const {
    selectedScenes,
    toggleSceneSelection,
    selectAllScenes,
    clearSelection,
  } = useScenesStore();
  const queryClient = useQueryClient();

  const sortBy = searchParams.get('sort_by') || 'created_at';
  const sortOrder = searchParams.get('sort_order') || 'desc';

  // Analyze mutation
  const analyzeMutation = useMutation(
    async ({
      sceneId,
      options,
    }: {
      sceneId: string;
      options: AnalysisTypeOptions;
    }) => {
      const response = await api.post('/analysis/generate', {
        scene_ids: [sceneId],
        plan_name: `Scene #${sceneId} Analysis - ${new Date().toISOString()}`,
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
        void message.success('Started analysis for scene');
        void queryClient.invalidateQueries('jobs');
        void queryClient.invalidateQueries(['scene-analysis']);
      },
      onError: () => {
        void message.error('Failed to start analysis');
      },
    }
  );

  const handleAnalyze = useCallback(
    (scene: Scene) => {
      Modal.confirm({
        title: 'Analyze Scene',
        content: (
          <Space direction="vertical" style={{ width: '100%' }}>
            <p>
              Analyze scene &quot;{scene.title || `#${scene.id}`}&quot; with the
              following options:
            </p>
            <AnalysisTypeSelector
              value={analysisOptions}
              onChange={setAnalysisOptions}
            />
          </Space>
        ),
        onOk: () => {
          analyzeMutation.mutate({
            sceneId: scene.id.toString(),
            options: analysisOptions,
          });
        },
        width: 500,
      });
    },
    [analyzeMutation, analysisOptions]
  );

  const handleSortChange = useCallback(
    (column: string) => {
      const params = new URLSearchParams(searchParams);

      if (sortBy === column) {
        // Toggle direction if same column
        params.set('sort_order', sortOrder === 'asc' ? 'desc' : 'asc');
      } else {
        // New column, default to desc
        params.set('sort_by', column);
        params.set('sort_order', 'desc');
      }

      setSearchParams(params);
    },
    [searchParams, setSearchParams, sortBy, sortOrder]
  );

  const columns: ColumnsType<Scene> = useMemo(
    () => [
      {
        title: () => (
          <Checkbox
            checked={
              scenes.length > 0 &&
              scenes.every((s) => selectedScenes.has(s.id.toString()))
            }
            indeterminate={
              scenes.some((s) => selectedScenes.has(s.id.toString())) &&
              !scenes.every((s) => selectedScenes.has(s.id.toString()))
            }
            onChange={(e: CheckboxChangeEvent) => {
              if (e.target.checked) {
                selectAllScenes(scenes.map((s) => s.id.toString()));
              } else {
                clearSelection();
              }
            }}
          />
        ),
        key: 'selection',
        width: 50,
        fixed: 'left',
        render: (_: unknown, record: Scene) => (
          <Checkbox
            checked={selectedScenes.has(record.id.toString())}
            onClick={(e: MouseEvent) => e.stopPropagation()}
            onChange={() => toggleSceneSelection(record.id.toString())}
          />
        ),
      },
      {
        title: 'Thumbnail',
        key: 'thumbnail',
        width: 120,
        render: (_: unknown, record: Scene) => (
          <SceneThumbnail
            sceneId={record.id}
            title={record.title || 'Scene thumbnail'}
            width={100}
            height={60}
            style={{ objectFit: 'cover', borderRadius: 4 }}
          />
        ),
      },
      {
        title: 'Title',
        dataIndex: 'title',
        key: 'title',
        sorter: true,
        sortOrder:
          sortBy === 'title'
            ? sortOrder === 'asc'
              ? 'ascend'
              : 'descend'
            : null,
        render: (title: string | null, record: Scene) => (
          <Space direction="vertical" size="small">
            <Text strong>{title || 'Untitled'}</Text>
            {record.path && (
              <Text
                type="secondary"
                ellipsis
                style={{ fontSize: 12, maxWidth: 300 }}
              >
                {record.path}
              </Text>
            )}
          </Space>
        ),
      },
      {
        title: 'Studio',
        key: 'studio',
        width: 150,
        render: (_: unknown, record: Scene) =>
          record.studio ? <Tag color="blue">{record.studio.name}</Tag> : null,
      },
      {
        title: 'Performers',
        key: 'performers',
        width: 200,
        render: (_: unknown, record: Scene) => (
          <Space size="small" wrap>
            {record.performers?.map((performer) => (
              <Tag key={performer.id} color="pink">
                {performer.name}
              </Tag>
            ))}
          </Space>
        ),
      },
      {
        title: 'Tags',
        key: 'tags',
        width: 200,
        render: (_: unknown, record: Scene) => (
          <Space size="small" wrap>
            {record.tags?.slice(0, 3).map((tag) => (
              <Tag key={tag.id} color="green">
                {tag.name}
              </Tag>
            ))}
            {record.tags && record.tags.length > 3 && (
              <Tag>+{record.tags.length - 3} more</Tag>
            )}
          </Space>
        ),
      },
      {
        title: 'Date',
        dataIndex: 'stash_date',
        key: 'date',
        width: 120,
        sorter: true,
        sortOrder:
          sortBy === 'date'
            ? sortOrder === 'asc'
              ? 'ascend'
              : 'descend'
            : null,
        render: (date: string | null) =>
          date ? dayjs(date).format('YYYY-MM-DD') : 'N/A',
      },
      {
        title: 'Duration',
        dataIndex: 'duration',
        key: 'duration',
        width: 100,
        sorter: true,
        sortOrder:
          sortBy === 'duration'
            ? sortOrder === 'asc'
              ? 'ascend'
              : 'descend'
            : null,
        render: (duration: number | undefined) => formatDuration(duration),
      },
      {
        title: 'Status',
        key: 'status',
        width: 100,
        render: (_: unknown, record: Scene) => (
          <Space>
            {record.analyzed && (
              <Tooltip title="Analyzed">
                <CheckCircleOutlined
                  style={{ color: '#52c41a', fontSize: 16 }}
                />
              </Tooltip>
            )}
            {record.details && (
              <Tooltip title="Has details">
                <InfoCircleOutlined
                  style={{ color: '#1890ff', fontSize: 16 }}
                />
              </Tooltip>
            )}
          </Space>
        ),
      },
      {
        title: 'Actions',
        key: 'actions',
        width: 120,
        fixed: 'right',
        render: (_: unknown, record: Scene) => (
          <Space>
            <Button
              size="small"
              icon={<EyeOutlined />}
              onClick={(e: MouseEvent<HTMLElement>) => {
                e.stopPropagation();
                onSceneSelect(record);
              }}
            >
              View
            </Button>
            <Button
              size="small"
              icon={<ExperimentOutlined />}
              onClick={(e: MouseEvent<HTMLElement>) => {
                e.stopPropagation();
                handleAnalyze(record);
              }}
              loading={analyzeMutation.isLoading}
            >
              Analyze
            </Button>
          </Space>
        ),
      },
    ],
    [
      scenes,
      selectedScenes,
      sortBy,
      sortOrder,
      onSceneSelect,
      toggleSceneSelection,
      selectAllScenes,
      clearSelection,
      handleAnalyze,
      analyzeMutation.isLoading,
    ]
  );

  const handleTableChange = useCallback(
    (
      _pagination: TablePaginationConfig | false,
      _filters: Record<string, FilterValue | null>,
      sorter: SorterResult<Scene> | SorterResult<Scene>[]
    ) => {
      if (!Array.isArray(sorter) && sorter.field) {
        handleSortChange(sorter.field as string);
      }
    },
    [handleSortChange]
  );

  return (
    <Table
      columns={columns}
      dataSource={scenes}
      rowKey="id"
      pagination={false}
      onChange={handleTableChange}
      scroll={{ x: 1200 }}
      onRow={(record: Scene) => ({
        onClick: () => onSceneSelect(record),
        style: { cursor: 'pointer' },
      })}
      rowClassName={(record: Scene) =>
        selectedScenes.has(record.id.toString()) ? 'ant-table-row-selected' : ''
      }
    />
  );
};
