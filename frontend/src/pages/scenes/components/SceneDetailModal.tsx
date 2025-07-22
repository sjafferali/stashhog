import React, { useState, useEffect } from 'react';
import {
  Modal,
  Tabs,
  Descriptions,
  Tag,
  Space,
  Button,
  List,
  Typography,
  Divider,
  Timeline,
  Empty,
  Spin,
  message,
  Collapse,
} from 'antd';
import {
  FileOutlined,
  InfoCircleOutlined,
  ExperimentOutlined,
  HistoryOutlined,
  LinkOutlined,
  ClockCircleOutlined,
  // ExportOutlined,
  EditOutlined,
  ApiOutlined,
  BugOutlined,
  // SyncOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { Link } from 'react-router-dom';
import dayjs from 'dayjs';
import api from '@/services/api';
import apiClient from '@/services/apiClient';
import { Scene, AnalysisResult } from '@/types/models';
import useAppStore from '@/store';
import { SceneEditModal } from '@/components/scenes/SceneEditModal';
import {
  AnalysisTypeSelector,
  AnalysisTypeOptions,
  hasAtLeastOneAnalysisTypeSelected,
} from '@/components/forms/AnalysisTypeSelector';

const { TabPane } = Tabs;
const { Text, Paragraph } = Typography;
const { Panel } = Collapse;

interface SceneDetailModalProps {
  scene: Scene;
  visible: boolean;
  onClose: () => void;
}

export const SceneDetailModal: React.FC<SceneDetailModalProps> = ({
  scene,
  visible,
  onClose,
}) => {
  const [activeTab, setActiveTab] = useState('overview');
  const [analysisOptions, setAnalysisOptions] = useState<AnalysisTypeOptions>({
    detectPerformers: true,
    detectStudios: true,
    detectTags: true,
    detectDetails: false,
    detectVideoTags: false,
  });
  const [editModalVisible, setEditModalVisible] = useState(false);
  const queryClient = useQueryClient();
  const { settings, loadSettings, isLoaded } = useAppStore();

  // Load settings if not already loaded
  useEffect(() => {
    if (!isLoaded) {
      void loadSettings();
    }
  }, [isLoaded, loadSettings]);

  const handleOpenInStash = () => {
    const stashUrl = settings?.stash_url || '';
    if (stashUrl && scene.id) {
      // Remove trailing slash from stash_url if present
      const baseUrl = stashUrl.replace(/\/$/, '');
      const fullUrl = `${baseUrl}/scenes/${scene.id}`;
      window.open(fullUrl, '_blank');
    }
  };

  const handleOpenInAPI = () => {
    // Get current origin for the API base URL
    const apiUrl = `${window.location.origin}/api/scenes/${scene.id}`;
    window.open(apiUrl, '_blank');
  };

  const handleDebugStashAPI = () => {
    // Open the debug endpoint for Stash GraphQL data
    const debugUrl = `${window.location.origin}/api/debug/stashscene/${scene.id}`;
    window.open(debugUrl, '_blank');
  };

  // Check if we have a valid stash URL
  const hasStashUrl = Boolean(
    settings?.stash_url && settings.stash_url.trim() !== ''
  );

  // Fetch full scene details
  const { data: fullScene, isLoading } = useQuery<Scene>(
    ['scene', scene.id],
    async () => {
      const response = await api.get(`/scenes/${scene.id}`);
      return response.data;
    },
    {
      enabled: visible,
    }
  );

  // Fetch analysis results for the scene
  const { data: analysisResults } = useQuery<AnalysisResult[]>(
    ['scene-analysis', scene.id],
    async () => {
      const response = await api.get(`/analysis/scenes/${scene.id}/results`);
      return response.data;
    },
    {
      enabled: visible,
    }
  );

  // Analyze mutation
  const analyzeMutation = useMutation(
    async (options: AnalysisTypeOptions) => {
      const response = await api.post('/analysis/generate', {
        scene_ids: [scene.id],
        plan_name: `Scene #${scene.id} Analysis - ${new Date().toISOString()}`,
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
    {
      onSuccess: () => {
        void message.success('Started analysis for scene');
        void queryClient.invalidateQueries('jobs');
        void queryClient.invalidateQueries(['scene-analysis', scene.id]);
      },
      onError: () => {
        void message.error('Failed to start analysis');
      },
    }
  );

  // Toggle analyzed mutation
  const toggleAnalyzedMutation = useMutation(
    async (value: boolean) => {
      return await apiClient.updateScene(parseInt(scene.id), {
        analyzed: value,
      });
    },
    {
      onSuccess: () => {
        void message.success('Updated analyzed status');
        void queryClient.invalidateQueries(['scene', scene.id]);
      },
      onError: () => {
        void message.error('Failed to update analyzed status');
      },
    }
  );

  // Toggle video analyzed mutation
  const toggleVideoAnalyzedMutation = useMutation(
    async (value: boolean) => {
      return await apiClient.updateScene(parseInt(scene.id), {
        video_analyzed: value,
      });
    },
    {
      onSuccess: () => {
        void message.success('Updated video analyzed status');
        void queryClient.invalidateQueries(['scene', scene.id]);
      },
      onError: () => {
        void message.error('Failed to update video analyzed status');
      },
    }
  );

  const handleAnalyze = () => {
    let currentOptions = analysisOptions;
    Modal.confirm({
      title: 'Analyze Scene',
      content: (
        <Space direction="vertical" style={{ width: '100%' }}>
          <p>Analyze this scene with the following options:</p>
          <AnalysisTypeSelector
            value={analysisOptions}
            onChange={(newOptions) => {
              currentOptions = newOptions;
              setAnalysisOptions(newOptions);
              // Update the modal's OK button state
              const okButton = document.querySelector(
                '.ant-modal-confirm-btns .ant-btn-primary'
              ) as HTMLButtonElement;
              if (okButton) {
                okButton.disabled =
                  !hasAtLeastOneAnalysisTypeSelected(newOptions);
              }
            }}
          />
        </Space>
      ),
      onOk: () => {
        if (hasAtLeastOneAnalysisTypeSelected(currentOptions)) {
          analyzeMutation.mutate(currentOptions);
        }
      },
      okButtonProps: {
        disabled: !hasAtLeastOneAnalysisTypeSelected(analysisOptions),
      },
      width: 500,
    });
  };

  const formatFileSize = (bytes?: string): string => {
    if (!bytes) return 'N/A';
    const size = parseInt(bytes, 10);
    if (isNaN(size)) return 'N/A';

    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let unitIndex = 0;
    let formattedSize = size;

    while (formattedSize >= 1024 && unitIndex < units.length - 1) {
      formattedSize /= 1024;
      unitIndex++;
    }

    return `${formattedSize.toFixed(1)} ${units[unitIndex]}`;
  };

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

  const renderOverviewTab = () => (
    <Spin spinning={isLoading}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* Basic Info */}
        <Descriptions bordered column={2} title="Scene Information">
          <Descriptions.Item label="ID" span={2}>
            <Text copyable>{fullScene?.id || 'N/A'}</Text>
          </Descriptions.Item>

          <Descriptions.Item label="Title" span={2}>
            {fullScene?.title || 'Untitled'}
          </Descriptions.Item>

          <Descriptions.Item label="Studio">
            {fullScene?.studio ? (
              <Tag color="blue">{fullScene.studio.name}</Tag>
            ) : (
              'N/A'
            )}
          </Descriptions.Item>

          <Descriptions.Item label="Organized">
            <Tag color={fullScene?.organized ? 'green' : 'default'}>
              {fullScene?.organized ? 'Yes' : 'No'}
            </Tag>
          </Descriptions.Item>

          <Descriptions.Item label="Analyzed">
            <Space>
              <Tag color={fullScene?.analyzed ? 'green' : 'default'}>
                {fullScene?.analyzed ? 'Yes' : 'No'}
              </Tag>
              <Button
                size="small"
                type="link"
                loading={toggleAnalyzedMutation.isLoading}
                onClick={() =>
                  toggleAnalyzedMutation.mutate(!fullScene?.analyzed)
                }
              >
                {fullScene?.analyzed ? 'Unset' : 'Set'}
              </Button>
            </Space>
          </Descriptions.Item>

          <Descriptions.Item label="Video Analyzed">
            <Space>
              <Tag color={fullScene?.video_analyzed ? 'green' : 'default'}>
                {fullScene?.video_analyzed ? 'Yes' : 'No'}
              </Tag>
              <Button
                size="small"
                type="link"
                loading={toggleVideoAnalyzedMutation.isLoading}
                onClick={() =>
                  toggleVideoAnalyzedMutation.mutate(!fullScene?.video_analyzed)
                }
              >
                {fullScene?.video_analyzed ? 'Unset' : 'Set'}
              </Button>
            </Space>
          </Descriptions.Item>

          <Descriptions.Item label="Rating">
            {fullScene?.rating !== undefined ? `${fullScene.rating}/5` : 'N/A'}
          </Descriptions.Item>

          <Descriptions.Item label="URL">
            {fullScene?.url ? (
              <a href={fullScene.url} target="_blank" rel="noopener noreferrer">
                <LinkOutlined /> Open
              </a>
            ) : (
              'N/A'
            )}
          </Descriptions.Item>
        </Descriptions>

        {/* Date Information */}
        <Descriptions bordered column={2} title="Date Information">
          <Descriptions.Item label="Scene Date">
            {fullScene?.stash_date
              ? dayjs(fullScene.stash_date).format('YYYY-MM-DD')
              : 'N/A'}
          </Descriptions.Item>

          <Descriptions.Item label="Stash Created">
            {fullScene?.stash_created_at
              ? dayjs(fullScene.stash_created_at).format('YYYY-MM-DD HH:mm:ss')
              : 'N/A'}
          </Descriptions.Item>

          <Descriptions.Item label="Stash Updated">
            {fullScene?.stash_updated_at
              ? dayjs(fullScene.stash_updated_at).format('YYYY-MM-DD HH:mm:ss')
              : 'N/A'}
          </Descriptions.Item>

          <Descriptions.Item label="Last Synced">
            {fullScene?.last_synced
              ? dayjs(fullScene.last_synced).format('YYYY-MM-DD HH:mm:ss')
              : 'N/A'}
          </Descriptions.Item>

          <Descriptions.Item label="StashHog Created">
            {fullScene?.created_at
              ? dayjs(fullScene.created_at).format('YYYY-MM-DD HH:mm:ss')
              : 'N/A'}
          </Descriptions.Item>

          <Descriptions.Item label="StashHog Updated">
            {fullScene?.updated_at
              ? dayjs(fullScene.updated_at).format('YYYY-MM-DD HH:mm:ss')
              : 'N/A'}
          </Descriptions.Item>
        </Descriptions>

        {/* Performers */}
        {fullScene?.performers && fullScene.performers.length > 0 && (
          <>
            <Divider>Performers</Divider>
            <Space wrap>
              {fullScene.performers.map((performer) => (
                <Tag key={performer.id} color="pink" style={{ margin: '2px' }}>
                  {performer.name}
                </Tag>
              ))}
            </Space>
          </>
        )}

        {/* Tags */}
        {fullScene?.tags && fullScene.tags.length > 0 && (
          <>
            <Divider>Tags</Divider>
            <Space wrap>
              {fullScene.tags.map((tag) => (
                <Tag key={tag.id} color="green" style={{ margin: '2px' }}>
                  {tag.name}
                </Tag>
              ))}
            </Space>
          </>
        )}

        {/* Details */}
        {fullScene?.details && (
          <>
            <Divider>Details</Divider>
            <Paragraph>{fullScene.details}</Paragraph>
          </>
        )}
      </Space>
    </Spin>
  );

  const renderFilesTab = () => {
    const files = fullScene?.files || [];

    if (files.length === 0) {
      return (
        <Empty
          description="No file information available"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      );
    }

    // Find the primary file to set as default expanded
    const primaryFileKey =
      files.find((file) => file.is_primary)?.id || files[0]?.id;

    return (
      <Collapse defaultActiveKey={primaryFileKey ? [primaryFileKey] : []}>
        {files.map((file, index) => {
          const panelHeader = (
            <Space>
              <Text strong>{file.basename || `File ${index + 1}`}</Text>
              {file.is_primary && <Tag color="blue">Primary</Tag>}
              {file.format && <Tag>{file.format}</Tag>}
              {file.size && (
                <Text type="secondary">
                  {formatFileSize(file.size.toString())}
                </Text>
              )}
            </Space>
          );

          return (
            <Panel header={panelHeader} key={file.id}>
              <Descriptions bordered column={2} size="small">
                <Descriptions.Item label="File ID" span={2}>
                  <Text copyable>{file.id}</Text>
                </Descriptions.Item>

                <Descriptions.Item label="Path" span={2}>
                  <Text code>{file.path}</Text>
                </Descriptions.Item>

                {file.basename && (
                  <Descriptions.Item label="Basename" span={2}>
                    {file.basename}
                  </Descriptions.Item>
                )}

                <Descriptions.Item label="Size">
                  {formatFileSize(file.size?.toString())}
                </Descriptions.Item>

                <Descriptions.Item label="Format">
                  {file.format || 'N/A'}
                </Descriptions.Item>

                <Descriptions.Item label="Duration">
                  {formatDuration(file.duration)}
                </Descriptions.Item>

                <Descriptions.Item label="Resolution">
                  {file.width && file.height
                    ? `${file.width}x${file.height}`
                    : 'N/A'}
                </Descriptions.Item>

                <Descriptions.Item label="Video Codec">
                  {file.video_codec || 'N/A'}
                </Descriptions.Item>

                <Descriptions.Item label="Audio Codec">
                  {file.audio_codec || 'N/A'}
                </Descriptions.Item>

                <Descriptions.Item label="Frame Rate">
                  {file.frame_rate ? `${file.frame_rate} fps` : 'N/A'}
                </Descriptions.Item>

                <Descriptions.Item label="Bitrate">
                  {file.bit_rate
                    ? `${Math.round(file.bit_rate / 1000)} kbps`
                    : 'N/A'}
                </Descriptions.Item>

                <Descriptions.Item label="OS Hash">
                  {file.oshash ? <Text code>{file.oshash}</Text> : 'N/A'}
                </Descriptions.Item>

                <Descriptions.Item label="Perceptual Hash">
                  {file.phash ? <Text code>{file.phash}</Text> : 'N/A'}
                </Descriptions.Item>

                {file.mod_time && (
                  <Descriptions.Item label="Modified Time" span={2}>
                    {dayjs(file.mod_time).format('YYYY-MM-DD HH:mm:ss')}
                  </Descriptions.Item>
                )}
              </Descriptions>
            </Panel>
          );
        })}
      </Collapse>
    );
  };

  const renderMarkersTab = () => {
    const markers = fullScene?.markers || [];

    const formatTime = (seconds: number): string => {
      const hours = Math.floor(seconds / 3600);
      const minutes = Math.floor((seconds % 3600) / 60);
      const secs = Math.floor(seconds % 60);
      if (hours > 0) {
        return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
      }
      return `${minutes}:${secs.toString().padStart(2, '0')}`;
    };

    if (markers.length === 0) {
      return (
        <Empty
          description="No scene markers"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      );
    }

    return (
      <List
        dataSource={markers}
        renderItem={(marker) => (
          <List.Item>
            <List.Item.Meta
              avatar={
                <div
                  style={{
                    width: 60,
                    textAlign: 'center',
                    fontSize: '14px',
                    fontWeight: 500,
                    color: '#1890ff',
                  }}
                >
                  {formatTime(marker.seconds)}
                </div>
              }
              title={
                <Space>
                  <Text strong>{marker.title || 'Untitled'}</Text>
                  {marker.end_seconds && (
                    <Text type="secondary">
                      (duration:{' '}
                      {formatTime(marker.end_seconds - marker.seconds)})
                    </Text>
                  )}
                </Space>
              }
              description={
                <Space
                  direction="vertical"
                  size="small"
                  style={{ width: '100%' }}
                >
                  <Space wrap>
                    <Tag color="blue" key={marker.primary_tag.id}>
                      {marker.primary_tag.name}
                    </Tag>
                    {marker.tags.map((tag) => (
                      <Tag key={tag.id}>{tag.name}</Tag>
                    ))}
                  </Space>
                  {marker.created_at && (
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      Created:{' '}
                      {dayjs(marker.created_at).format('YYYY-MM-DD HH:mm:ss')}
                    </Text>
                  )}
                </Space>
              }
            />
          </List.Item>
        )}
      />
    );
  };

  const renderAnalysisTab = () => {
    const results = analysisResults || [];

    if (results.length === 0) {
      return (
        <Empty
          description="No analysis results yet"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        >
          <Button
            type="primary"
            icon={<ExperimentOutlined />}
            onClick={handleAnalyze}
            loading={analyzeMutation.isLoading}
          >
            Analyze Scene
          </Button>
        </Empty>
      );
    }

    return (
      <List
        dataSource={results}
        renderItem={(result: AnalysisResult) => (
          <List.Item>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Space>
                <Text strong>Plan:</Text>
                {result.plan ? (
                  <Link to={`/analysis/plans/${result.plan.id}`}>
                    <Tag style={{ cursor: 'pointer' }}>{result.plan.name}</Tag>
                  </Link>
                ) : (
                  <Tag>Unknown</Tag>
                )}
                <Text type="secondary">
                  {dayjs(result.created_at).format('YYYY-MM-DD HH:mm:ss')}
                </Text>
              </Space>

              {result.extracted_data && (
                <Descriptions size="small" bordered column={1}>
                  {result.extracted_data.title && (
                    <Descriptions.Item label="Title">
                      {result.extracted_data.title}
                    </Descriptions.Item>
                  )}

                  {result.extracted_data.date && (
                    <Descriptions.Item label="Date">
                      {result.extracted_data.date}
                    </Descriptions.Item>
                  )}

                  {result.extracted_data.performers && (
                    <Descriptions.Item label="Performers">
                      {result.extracted_data.performers.join(', ')}
                    </Descriptions.Item>
                  )}

                  {result.extracted_data.tags && (
                    <Descriptions.Item label="Tags">
                      {result.extracted_data.tags.join(', ')}
                    </Descriptions.Item>
                  )}

                  {result.extracted_data.studio && (
                    <Descriptions.Item label="Studio">
                      {result.extracted_data.studio}
                    </Descriptions.Item>
                  )}

                  {result.extracted_data.details && (
                    <Descriptions.Item label="Details">
                      {result.extracted_data.details}
                    </Descriptions.Item>
                  )}
                </Descriptions>
              )}

              <Space size="small">
                <Text type="secondary">Model: {result.model_used}</Text>
                <Text type="secondary">Time: {result.processing_time}s</Text>
              </Space>
            </Space>
          </List.Item>
        )}
      />
    );
  };

  const renderHistoryTab = () => (
    <Timeline>
      <Timeline.Item color="green">
        <Text strong>Scene Created in Stash</Text>
        <br />
        <Text type="secondary">
          {fullScene?.stash_created_at
            ? dayjs(fullScene.stash_created_at).format('YYYY-MM-DD HH:mm:ss')
            : 'N/A'}
        </Text>
      </Timeline.Item>

      {fullScene?.analyzed && (
        <Timeline.Item color="blue">
          <Text strong>Scene Analyzed</Text>
          <br />
          <Text type="secondary">Yes</Text>
        </Timeline.Item>
      )}

      {analysisResults?.map((result, index) => (
        <Timeline.Item key={result.id}>
          <Text strong>Analysis #{index + 1}</Text>
          <br />
          <Text type="secondary">
            {dayjs(result.created_at).format('YYYY-MM-DD HH:mm:ss')}
          </Text>
          <br />
          <Text type="secondary">Plan: {result.plan?.name || 'Unknown'}</Text>
        </Timeline.Item>
      ))}

      <Timeline.Item>
        <Text strong>Last Updated in Stash</Text>
        <br />
        <Text type="secondary">
          {fullScene?.stash_updated_at
            ? dayjs(fullScene.stash_updated_at).format('YYYY-MM-DD HH:mm:ss')
            : 'N/A'}
        </Text>
      </Timeline.Item>
    </Timeline>
  );

  return (
    <>
      <Modal
        title={
          <Space>
            <FileOutlined />
            {scene.title || 'Scene Details'}
          </Space>
        }
        open={visible}
        onCancel={() => {
          setEditModalVisible(false);
          onClose();
        }}
        width={800}
        footer={[
          <Button key="close" onClick={onClose}>
            Close
          </Button>,
          <Button
            key="edit"
            icon={<EditOutlined />}
            onClick={() => setEditModalVisible(true)}
          >
            Edit
          </Button>,
          <Button
            key="stash"
            icon={<LinkOutlined />}
            onClick={handleOpenInStash}
            disabled={!hasStashUrl}
          >
            Open in Stash
          </Button>,
          <Button key="api" icon={<ApiOutlined />} onClick={handleOpenInAPI}>
            Open in API
          </Button>,
          <Button
            key="debug"
            icon={<BugOutlined />}
            onClick={handleDebugStashAPI}
          >
            Debug Stash API
          </Button>,
          <Button
            key="analyze"
            type="primary"
            icon={<ExperimentOutlined />}
            onClick={handleAnalyze}
            loading={analyzeMutation.isLoading}
          >
            Analyze
          </Button>,
        ]}
      >
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <TabPane
            tab={
              <span>
                <InfoCircleOutlined /> Overview
              </span>
            }
            key="overview"
          >
            {renderOverviewTab()}
          </TabPane>

          <TabPane
            tab={
              <span>
                <FileOutlined /> Files/Paths
              </span>
            }
            key="files"
          >
            {renderFilesTab()}
          </TabPane>

          <TabPane
            tab={
              <span>
                <ClockCircleOutlined /> Markers
              </span>
            }
            key="markers"
          >
            {renderMarkersTab()}
          </TabPane>

          <TabPane
            tab={
              <span>
                <ExperimentOutlined /> Analysis
              </span>
            }
            key="analysis"
          >
            {renderAnalysisTab()}
          </TabPane>

          <TabPane
            tab={
              <span>
                <HistoryOutlined /> History
              </span>
            }
            key="history"
          >
            {renderHistoryTab()}
          </TabPane>
        </Tabs>
      </Modal>

      {scene && (
        <SceneEditModal
          visible={editModalVisible}
          scene={scene}
          onClose={() => {
            setEditModalVisible(false);
          }}
          onSuccess={() => {
            void queryClient.invalidateQueries(['scene', scene.id]);
          }}
        />
      )}
    </>
  );
};
