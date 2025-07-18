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
  ClockCircleOutlined,
  CalendarOutlined,
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
import {
  AnalysisTypeSelector,
  AnalysisTypeOptions,
} from '@/components/forms/AnalysisTypeSelector';
import styles from './ListView.module.scss';

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
        title: 'Title',
        dataIndex: 'title',
        key: 'title',
        width: 300,
        sorter: true,
        sortOrder:
          sortBy === 'title'
            ? sortOrder === 'asc'
              ? 'ascend'
              : 'descend'
            : null,
        render: (title: string | null, record: Scene) => (
          <Space direction="vertical" size="small" className={styles.titleCell}>
            <Text strong style={{ wordBreak: 'break-word' }}>
              {title || 'Untitled'}
            </Text>
            {record.path && (
              <Text
                type="secondary"
                ellipsis
                style={{ fontSize: 12 }}
                title={record.path}
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

  // Mobile card view component
  const MobileCardView = () => (
    <div className={styles.mobileCards}>
      {scenes.length > 0 && (
        <div className={styles.mobileSelectAll}>
          <Checkbox
            checked={scenes.every((s) => selectedScenes.has(s.id.toString()))}
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
          >
            Select All ({scenes.length} scenes)
          </Checkbox>
        </div>
      )}
      {scenes.map((scene) => (
        <div
          key={scene.id}
          className={`${styles.mobileCard} ${selectedScenes.has(scene.id.toString()) ? styles.selected : ''}`}
          onClick={() => onSceneSelect(scene)}
        >
          <div className={styles.cardHeader}>
            <Checkbox
              className={styles.cardCheckbox}
              checked={selectedScenes.has(scene.id.toString())}
              onClick={(e: MouseEvent) => e.stopPropagation()}
              onChange={() => toggleSceneSelection(scene.id.toString())}
            />
            <div className={styles.cardTitle}>
              <h4 className={styles.title}>{scene.title || 'Untitled'}</h4>
              {scene.path && <div className={styles.path}>{scene.path}</div>}
            </div>
          </div>

          <div className={styles.cardMeta}>
            {scene.stash_date && (
              <div className={styles.metaItem}>
                <CalendarOutlined />
                <span>{dayjs(scene.stash_date).format('YYYY-MM-DD')}</span>
              </div>
            )}
            {scene.duration && (
              <div className={styles.metaItem}>
                <ClockCircleOutlined />
                <span>{formatDuration(scene.duration)}</span>
              </div>
            )}
          </div>

          <div className={styles.cardTags}>
            {scene.studio && <Tag color="blue">{scene.studio.name}</Tag>}
            {scene.performers?.slice(0, 2).map((performer) => (
              <Tag key={performer.id} color="pink">
                {performer.name}
              </Tag>
            ))}
            {scene.performers && scene.performers.length > 2 && (
              <Tag>+{scene.performers.length - 2}</Tag>
            )}
            {scene.tags?.slice(0, 2).map((tag) => (
              <Tag key={tag.id} color="green">
                {tag.name}
              </Tag>
            ))}
            {scene.tags && scene.tags.length > 2 && (
              <Tag>+{scene.tags.length - 2}</Tag>
            )}
          </div>

          <div className={styles.cardFooter}>
            <div className={styles.cardStatus}>
              {scene.analyzed && (
                <Tooltip title="Analyzed">
                  <CheckCircleOutlined
                    style={{ color: '#52c41a', fontSize: 16 }}
                  />
                </Tooltip>
              )}
              {scene.details && (
                <Tooltip title="Has details">
                  <InfoCircleOutlined
                    style={{ color: '#1890ff', fontSize: 16 }}
                  />
                </Tooltip>
              )}
            </div>
            <div className={styles.cardActions}>
              <Button
                size="small"
                icon={<EyeOutlined />}
                onClick={(e: MouseEvent<HTMLElement>) => {
                  e.stopPropagation();
                  onSceneSelect(scene);
                }}
              >
                View
              </Button>
              <Button
                size="small"
                icon={<ExperimentOutlined />}
                onClick={(e: MouseEvent<HTMLElement>) => {
                  e.stopPropagation();
                  handleAnalyze(scene);
                }}
                loading={analyzeMutation.isLoading}
              >
                Analyze
              </Button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );

  return (
    <div className={styles.listView}>
      <div className={styles.desktopTable}>
        <Table
          columns={columns}
          dataSource={scenes}
          rowKey="id"
          pagination={false}
          onChange={handleTableChange}
          scroll={{ x: 1400 }}
          onRow={(record: Scene) => ({
            onClick: () => onSceneSelect(record),
            style: { cursor: 'pointer' },
          })}
          rowClassName={(record: Scene) =>
            selectedScenes.has(record.id.toString())
              ? 'ant-table-row-selected'
              : ''
          }
        />
      </div>
      <MobileCardView />
    </div>
  );
};
