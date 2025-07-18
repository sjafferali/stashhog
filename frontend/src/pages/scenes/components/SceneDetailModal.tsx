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
} from 'antd';
import {
  FileOutlined,
  InfoCircleOutlined,
  ExperimentOutlined,
  HistoryOutlined,
  LinkOutlined,
  // ExportOutlined,
  EditOutlined,
  // SyncOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { Link } from 'react-router-dom';
import dayjs from 'dayjs';
import api from '@/services/api';
import { Scene, AnalysisResult } from '@/types/models';
import useAppStore from '@/store';
import { SceneThumbnail } from '@/components/common/SceneThumbnail';
import { SceneEditModal } from '@/components/scenes/SceneEditModal';

const { TabPane } = Tabs;
const { Text, Paragraph } = Typography;

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
    async () => {
      const response = await api.post('/analysis/generate', {
        scene_ids: [scene.id],
        plan_name: `Scene #${scene.id} Analysis - ${new Date().toISOString()}`,
        options: {
          detect_performers: true,
          detect_studios: true,
          detect_tags: true,
          detect_details: true,
          use_ai: true,
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

  const handleAnalyze = () => {
    Modal.confirm({
      title: 'Analyze Scene',
      content: 'Are you sure you want to analyze this scene?',
      onOk: () => {
        analyzeMutation.mutate();
      },
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
        {/* Thumbnail */}
        <div style={{ textAlign: 'center' }}>
          <SceneThumbnail
            sceneId={scene.id}
            title={scene.title || 'Scene thumbnail'}
            width={400}
          />
        </div>

        {/* Basic Info */}
        <Descriptions bordered column={2}>
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

          <Descriptions.Item label="Date">
            {fullScene?.stash_date
              ? dayjs(fullScene.stash_date).format('YYYY-MM-DD')
              : 'N/A'}
          </Descriptions.Item>

          <Descriptions.Item label="Duration">
            {formatDuration(fullScene?.duration)}
          </Descriptions.Item>

          <Descriptions.Item label="File Size">
            {formatFileSize(fullScene?.size?.toString())}
          </Descriptions.Item>

          <Descriptions.Item label="Resolution">
            {fullScene?.width && fullScene?.height
              ? `${fullScene.width}x${fullScene.height}`
              : 'N/A'}
          </Descriptions.Item>

          <Descriptions.Item label="Frame Rate">
            {fullScene?.framerate ? `${fullScene.framerate} fps` : 'N/A'}
          </Descriptions.Item>

          <Descriptions.Item label="Codec">
            {fullScene?.codec || 'N/A'}
          </Descriptions.Item>

          <Descriptions.Item label="Bitrate">
            {fullScene?.bitrate ? `${fullScene.bitrate} kbps` : 'N/A'}
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

  const renderFilesTab = () => (
    <Descriptions bordered column={1}>
      <Descriptions.Item label="Path(s)">
        {fullScene?.paths && fullScene.paths.length > 0 ? (
          <Space direction="vertical" size="small">
            {fullScene.paths.map((path, index) => (
              <Text key={index} code>
                {path}
              </Text>
            ))}
          </Space>
        ) : (
          <Text>N/A</Text>
        )}
      </Descriptions.Item>

      <Descriptions.Item label="ID">
        <Text copyable>{fullScene?.id || 'N/A'}</Text>
      </Descriptions.Item>

      <Descriptions.Item label="Perceptual Hash">
        <Text code type="secondary">
          Not synchronized from Stash
        </Text>
      </Descriptions.Item>

      <Descriptions.Item label="File Modified">
        {fullScene?.file_mod_time
          ? dayjs(fullScene.file_mod_time).format('YYYY-MM-DD HH:mm:ss')
          : 'N/A'}
      </Descriptions.Item>

      <Descriptions.Item label="Created in Stash">
        {fullScene?.stash_created_at
          ? dayjs(fullScene.stash_created_at).format('YYYY-MM-DD HH:mm:ss')
          : 'N/A'}
      </Descriptions.Item>

      <Descriptions.Item label="Updated in Stash">
        {fullScene?.stash_updated_at
          ? dayjs(fullScene.stash_updated_at).format('YYYY-MM-DD HH:mm:ss')
          : 'N/A'}
      </Descriptions.Item>
    </Descriptions>
  );

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
