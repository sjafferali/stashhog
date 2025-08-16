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
  Dropdown,
  Menu,
} from 'antd';
import type { CheckboxChangeEvent } from '@/types/antd-proper';
import {
  EyeOutlined,
  ExperimentOutlined,
  CheckCircleOutlined,
  InfoCircleOutlined,
  ClockCircleOutlined,
  CalendarOutlined,
  MoreOutlined,
  VideoCameraOutlined,
  RobotOutlined,
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
import { useMutation, useQueryClient } from '@tanstack/react-query';
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
    detectVideoTags: false,
  });
  const [analysisModalVisible, setAnalysisModalVisible] = useState(false);
  const [selectedSceneForAnalysis, setSelectedSceneForAnalysis] =
    useState<Scene | null>(null);
  const [tempAnalysisOptions, setTempAnalysisOptions] =
    useState<AnalysisTypeOptions>({
      detectPerformers: true,
      detectStudios: true,
      detectTags: true,
      detectDetails: false,
      detectVideoTags: false,
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
  const analyzeMutation = useMutation({
    mutationFn: async ({
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
          detect_video_tags: options.detectVideoTags,
          confidence_threshold: 0.7,
        },
      });
      return response.data;
    },
    onSuccess: () => {
      void message.success('Started analysis for scene');
      void queryClient.invalidateQueries({ queryKey: ['jobs'] });
      void queryClient.invalidateQueries({ queryKey: ['scene-analysis'] });
    },
    onError: () => {
      void message.error('Failed to start analysis');
    },
  });

  const handleAnalyze = useCallback(
    (scene: Scene) => {
      setSelectedSceneForAnalysis(scene);
      setTempAnalysisOptions(analysisOptions);
      setAnalysisModalVisible(true);
    },
    [analysisOptions]
  );

  const handleAnalysisModalOk = useCallback(() => {
    if (selectedSceneForAnalysis) {
      setAnalysisOptions(tempAnalysisOptions);
      analyzeMutation.mutate({
        sceneId: selectedSceneForAnalysis.id.toString(),
        options: tempAnalysisOptions,
      });
      setAnalysisModalVisible(false);
      setSelectedSceneForAnalysis(null);
    }
  }, [selectedSceneForAnalysis, tempAnalysisOptions, analyzeMutation]);

  const handleAnalysisModalCancel = useCallback(() => {
    setAnalysisModalVisible(false);
    setSelectedSceneForAnalysis(null);
    setTempAnalysisOptions(analysisOptions);
  }, [analysisOptions]);

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
            {record.active_jobs && record.active_jobs.length > 0 && (
              <Tooltip title={`Active job: ${record.active_jobs[0].type}`}>
                <ClockCircleOutlined
                  style={{ color: '#faad14', fontSize: 16 }}
                />
              </Tooltip>
            )}
            {record.analyzed && (
              <Tooltip title="Analyzed">
                <CheckCircleOutlined
                  style={{ color: '#52c41a', fontSize: 16 }}
                />
              </Tooltip>
            )}
            {record.video_analyzed && (
              <Tooltip title="Video Analyzed">
                <VideoCameraOutlined
                  style={{ color: '#722ed1', fontSize: 16 }}
                />
              </Tooltip>
            )}
            {record.generated && (
              <Tooltip title="Generated">
                <RobotOutlined style={{ color: '#1890ff', fontSize: 16 }} />
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
        width: 80,
        fixed: 'right',
        render: (_: unknown, record: Scene) => {
          const menu = (
            <Menu
              onClick={(e: { domEvent: MouseEvent }) => {
                e.domEvent.stopPropagation();
              }}
            >
              <Menu.Item
                key="view"
                icon={<EyeOutlined />}
                onClick={() => onSceneSelect(record)}
              >
                View Details
              </Menu.Item>
              <Menu.Item
                key="analyze"
                icon={<ExperimentOutlined />}
                onClick={() => handleAnalyze(record)}
                disabled={analyzeMutation.isPending}
              >
                Analyze Scene
              </Menu.Item>
            </Menu>
          );

          return (
            <Dropdown overlay={menu} trigger={['click']}>
              <Button
                size="small"
                icon={<MoreOutlined />}
                onClick={(e: MouseEvent<HTMLElement>) => {
                  e.stopPropagation();
                }}
              />
            </Dropdown>
          );
        },
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
      analyzeMutation.isPending,
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
              {scene.active_jobs && scene.active_jobs.length > 0 && (
                <Tooltip title={`Active job: ${scene.active_jobs[0].type}`}>
                  <ClockCircleOutlined
                    style={{ color: '#faad14', fontSize: 16 }}
                  />
                </Tooltip>
              )}
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
              <Dropdown
                overlay={
                  <Menu
                    onClick={(e: { domEvent: MouseEvent }) => {
                      e.domEvent.stopPropagation();
                    }}
                  >
                    <Menu.Item
                      key="analyze"
                      icon={<ExperimentOutlined />}
                      onClick={() => handleAnalyze(scene)}
                      disabled={analyzeMutation.isPending}
                    >
                      Analyze Scene
                    </Menu.Item>
                  </Menu>
                }
                trigger={['click']}
              >
                <Button
                  size="small"
                  icon={<MoreOutlined />}
                  onClick={(e: MouseEvent<HTMLElement>) => {
                    e.stopPropagation();
                  }}
                />
              </Dropdown>
            </div>
          </div>
        </div>
      ))}
    </div>
  );

  return (
    <>
      <div className={styles.listView}>
        <div className={styles.desktopTable}>
          <Table
            columns={columns}
            dataSource={scenes}
            rowKey="id"
            pagination={false}
            onChange={handleTableChange}
            scroll={{ x: 1300 }}
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

      <Modal
        title="Analyze Scene"
        open={analysisModalVisible}
        onOk={handleAnalysisModalOk}
        onCancel={handleAnalysisModalCancel}
        confirmLoading={analyzeMutation.isPending}
        width={500}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <p>
            Analyze scene &quot;
            {selectedSceneForAnalysis?.title ||
              `#${selectedSceneForAnalysis?.id}`}
            &quot; with the following options:
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
