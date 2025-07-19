import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  Card,
  Button,
  Descriptions,
  Tag,
  Space,
  Modal,
  message,
  Spin,
  Tabs,
  List,
  Empty,
  Typography,
} from 'antd';
import {
  ArrowLeftOutlined,
  EditOutlined,
  RobotOutlined,
  LinkOutlined,
  InfoCircleOutlined,
  ExperimentOutlined,
} from '@ant-design/icons';
import { useMutation, useQueryClient, useQuery } from 'react-query';
import dayjs from 'dayjs';
import api from '@/services/api';
import apiClient from '@/services/apiClient';
import useAppStore from '@/store';
import { Scene, AnalysisResult } from '@/types/models';
import { SceneEditModal } from '@/components/scenes/SceneEditModal';
import {
  AnalysisTypeSelector,
  AnalysisTypeOptions,
} from '@/components/forms/AnalysisTypeSelector';

const { TabPane } = Tabs;
const { Text } = Typography;

const SceneDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { settings, loadSettings, isLoaded } = useAppStore();
  const [activeTab, setActiveTab] = useState('overview');
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [analysisOptions, setAnalysisOptions] = useState<AnalysisTypeOptions>({
    detectPerformers: true,
    detectStudios: true,
    detectTags: true,
    detectDetails: false,
    detectVideoTags: false,
  });

  // Fetch scene data
  const { data: scene, isLoading: isLoadingScene } = useQuery<Scene>(
    ['scene', id],
    () => apiClient.getScene(Number(id)),
    {
      enabled: !!id,
    }
  );

  // Fetch analysis results for the scene
  const { data: analysisResults } = useQuery<AnalysisResult[]>(
    ['scene-analysis', id],
    async () => {
      const response = await api.get(`/analysis/scenes/${id}/results`);
      return response.data;
    },
    {
      enabled: !!id,
    }
  );

  // Load settings if not already loaded
  useEffect(() => {
    if (!isLoaded) {
      void loadSettings();
    }
  }, [isLoaded, loadSettings]);

  const handleOpenInStash = () => {
    const stashUrl = settings?.stash_url || '';
    if (stashUrl && id) {
      // Remove trailing slash from stash_url if present
      const baseUrl = stashUrl.replace(/\/$/, '');
      const fullUrl = `${baseUrl}/scenes/${id}`;
      window.open(fullUrl, '_blank');
    }
  };

  // Check if we have a valid stash URL
  const hasStashUrl = Boolean(
    settings?.stash_url && settings.stash_url.trim() !== ''
  );

  console.log('Scene Detail - Settings:', settings);
  console.log('Scene Detail - hasStashUrl:', hasStashUrl);
  console.log('Scene Detail - stash_url:', settings?.stash_url);

  // Analyze mutation
  const analyzeMutation = useMutation(
    async (options: AnalysisTypeOptions) => {
      const response = await api.post('/analysis/generate', {
        scene_ids: [id || '0'],
        plan_name: `Scene #${id} Analysis - ${new Date().toISOString()}`,
        options: {
          detect_performers: options.detectPerformers,
          detect_studios: options.detectStudios,
          detect_tags: options.detectTags,
          detect_details: options.detectDetails,
          confidence_threshold: 0.7,
        },
      });
      return response.data;
    },
    {
      onSuccess: () => {
        void message.success('Started analysis for scene');
        void queryClient.invalidateQueries('jobs');
        void queryClient.invalidateQueries(['scene-analysis', id]);
      },
      onError: () => {
        void message.error('Failed to start analysis');
      },
    }
  );

  const handleAnalyze = () => {
    Modal.confirm({
      title: 'Analyze Scene',
      content: (
        <Space direction="vertical" style={{ width: '100%' }}>
          <p>Analyze this scene with the following options:</p>
          <AnalysisTypeSelector
            value={analysisOptions}
            onChange={setAnalysisOptions}
          />
        </Space>
      ),
      onOk: () => {
        analyzeMutation.mutate(analysisOptions);
      },
      width: 500,
    });
  };

  // Helper functions
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

  const formatFileSize = (bytes?: number): string => {
    if (!bytes) return 'N/A';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let size = bytes;
    let unitIndex = 0;
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }
    return `${size.toFixed(2)} ${units[unitIndex]}`;
  };

  const formatBitrate = (bitrate?: number): string => {
    if (!bitrate) return 'N/A';
    if (bitrate >= 1000000) {
      return `${(bitrate / 1000000).toFixed(2)} Mbps`;
    }
    return `${(bitrate / 1000).toFixed(0)} kbps`;
  };

  const getFilePath = (scene?: Scene): string => {
    if (!scene) return 'N/A';
    // Check if there's a file_path field (actual file path from Stash)
    if (scene.file_path) return scene.file_path;
    // Check if there's a path field (legacy)
    if (scene.path) return scene.path;
    // Otherwise show the first path from paths array which might be a URL
    if (scene.paths && scene.paths.length > 0) return scene.paths[0];
    return 'N/A';
  };

  if (isLoadingScene) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
      </div>
    );
  }

  const renderOverviewTab = () => (
    <Descriptions bordered column={2}>
      <Descriptions.Item label="Title" span={2}>
        {scene?.title || 'N/A'}
      </Descriptions.Item>
      <Descriptions.Item label="Date">
        {scene?.stash_date
          ? new Date(scene.stash_date).toLocaleDateString()
          : 'N/A'}
      </Descriptions.Item>
      <Descriptions.Item label="Duration">
        {formatDuration(scene?.duration)}
      </Descriptions.Item>
      <Descriptions.Item label="Resolution">
        {scene?.width && scene?.height
          ? `${scene.width}x${scene.height}`
          : 'N/A'}
      </Descriptions.Item>
      <Descriptions.Item label="File Size">
        {formatFileSize(scene?.size)}
      </Descriptions.Item>
      <Descriptions.Item label="Frame Rate">
        {scene?.framerate ? `${scene.framerate} fps` : 'N/A'}
      </Descriptions.Item>
      <Descriptions.Item label="Bitrate">
        {formatBitrate(scene?.bitrate)}
      </Descriptions.Item>
      <Descriptions.Item label="Video Codec">
        {scene?.video_codec || scene?.codec || 'N/A'}
      </Descriptions.Item>
      <Descriptions.Item label="Studio">
        {scene?.studio?.name || 'N/A'}
      </Descriptions.Item>
      <Descriptions.Item label="File Path" span={2}>
        <div style={{ wordBreak: 'break-all' }}>{getFilePath(scene)}</div>
      </Descriptions.Item>
      {scene?.details && (
        <Descriptions.Item label="Details" span={2}>
          {scene.details}
        </Descriptions.Item>
      )}
      <Descriptions.Item label="Performers" span={2}>
        {scene?.performers && scene.performers.length > 0 ? (
          <Space wrap>
            {scene.performers.map((performer) => (
              <Tag key={performer.id} color="blue">
                {performer.name}
              </Tag>
            ))}
          </Space>
        ) : (
          'None'
        )}
      </Descriptions.Item>
      <Descriptions.Item label="Tags" span={2}>
        {scene?.tags && scene.tags.length > 0 ? (
          <Space wrap>
            {scene.tags.map((tag) => (
              <Tag key={tag.id}>{tag.name}</Tag>
            ))}
          </Space>
        ) : (
          'None'
        )}
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
                {result.plan?.id ? (
                  <Link to={`/analysis/plans/${result.plan.id}`}>
                    <Tag color="blue" style={{ cursor: 'pointer' }}>
                      {result.plan?.name || 'Unknown'}
                    </Tag>
                  </Link>
                ) : (
                  <Tag>{result.plan?.name || 'Unknown'}</Tag>
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

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => {
            void navigate('/scenes');
          }}
        >
          Back
        </Button>
        <h1 style={{ margin: 0 }}>Scene Detail</h1>
      </Space>

      <Card
        title={scene?.title || `Scene #${id}`}
        extra={
          <Space>
            <Button
              icon={<EditOutlined />}
              onClick={() => setEditModalVisible(true)}
            >
              Edit
            </Button>
            <Button
              icon={<LinkOutlined />}
              onClick={handleOpenInStash}
              disabled={!hasStashUrl}
            >
              Open in Stash
            </Button>
            <Button
              type="primary"
              icon={<RobotOutlined />}
              onClick={handleAnalyze}
              loading={analyzeMutation.isLoading}
            >
              Analyze
            </Button>
          </Space>
        }
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
                <ExperimentOutlined /> Analysis
              </span>
            }
            key="analysis"
          >
            {renderAnalysisTab()}
          </TabPane>
        </Tabs>
      </Card>

      {scene && (
        <SceneEditModal
          visible={editModalVisible}
          scene={scene}
          onClose={() => setEditModalVisible(false)}
          onSuccess={() => {
            void queryClient.invalidateQueries(['scene', id]);
          }}
        />
      )}
    </div>
  );
};

export default SceneDetail;
