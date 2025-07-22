import React, { useEffect } from 'react';
import {
  Descriptions,
  Tag,
  Space,
  Button,
  Card,
  Row,
  Col,
  Divider,
  Typography,
  Tooltip,
  Rate,
} from 'antd';
import {
  EditOutlined,
  ExperimentOutlined,
  PlayCircleOutlined,
  DownloadOutlined,
  LinkOutlined,
  FolderOpenOutlined,
  ApiOutlined,
} from '@ant-design/icons';
import { Scene } from '@/types/models';
import { SceneCard } from './SceneCard';
import useAppStore from '@/store';
import styles from './SceneDetail.module.scss';

const { Title, Paragraph } = Typography;

export interface SceneDetailProps {
  scene: Scene;
  onEdit?: (field: string) => void;
  onAnalyze?: () => void;
  relatedScenes?: Scene[];
}

export const SceneDetail: React.FC<SceneDetailProps> = ({
  scene,
  onEdit,
  onAnalyze,
  relatedScenes = [],
}) => {
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

  // Check if we have a valid stash URL
  const hasStashUrl = Boolean(
    settings?.stash_url && settings.stash_url.trim() !== ''
  );

  const formatDuration = (seconds?: number) => {
    if (!seconds) return 'N/A';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return 'N/A';
    const size = bytes;
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let unitIndex = 0;
    let value = size;

    while (value >= 1024 && unitIndex < units.length - 1) {
      value /= 1024;
      unitIndex++;
    }

    return `${value.toFixed(2)} ${units[unitIndex]}`;
  };

  const formatBitrate = (bitrate?: number) => {
    if (!bitrate) return 'N/A';
    if (bitrate >= 1000000) {
      return `${(bitrate / 1000000).toFixed(1)} Mbps`;
    }
    return `${(bitrate / 1000).toFixed(0)} Kbps`;
  };

  return (
    <div className={styles.sceneDetail}>
      <Row gutter={[24, 24]}>
        <Col xs={24} lg={16}>
          <Card className={styles.mainCard}>
            <div className={styles.header}>
              <Title level={2}>{scene.title}</Title>
              <Space>
                <Button
                  type="primary"
                  icon={<PlayCircleOutlined />}
                  size="large"
                >
                  Play
                </Button>
                <Button
                  icon={<ExperimentOutlined />}
                  onClick={onAnalyze}
                  loading={false}
                >
                  Analyze
                </Button>
                <Tooltip title="Edit Scene">
                  <Button
                    icon={<EditOutlined />}
                    onClick={() => onEdit?.('all')}
                  />
                </Tooltip>
              </Space>
            </div>

            {scene.details && (
              <>
                <Divider>Description</Divider>
                <Paragraph>{scene.details}</Paragraph>
              </>
            )}

            <Divider>Scene Information</Divider>
            <Descriptions bordered column={{ xs: 1, sm: 2, md: 2 }}>
              <Descriptions.Item label="Date">
                {scene.stash_date
                  ? new Date(scene.stash_date).toLocaleDateString()
                  : 'N/A'}
                {onEdit && (
                  <Button
                    type="link"
                    icon={<EditOutlined />}
                    size="small"
                    onClick={() => onEdit('date')}
                  />
                )}
              </Descriptions.Item>

              <Descriptions.Item label="Director">
                {'N/A'}
                {onEdit && (
                  <Button
                    type="link"
                    icon={<EditOutlined />}
                    size="small"
                    onClick={() => onEdit('director')}
                  />
                )}
              </Descriptions.Item>

              <Descriptions.Item label="Studio">
                {scene.studio ? (
                  <Tag color="blue">{scene.studio.name}</Tag>
                ) : (
                  'N/A'
                )}
                {onEdit && (
                  <Button
                    type="link"
                    icon={<EditOutlined />}
                    size="small"
                    onClick={() => onEdit('studio')}
                  />
                )}
              </Descriptions.Item>

              <Descriptions.Item label="Rating">
                <Rate value={scene.rating || 0} disabled />
                {onEdit && (
                  <Button
                    type="link"
                    icon={<EditOutlined />}
                    size="small"
                    onClick={() => onEdit('rating')}
                  />
                )}
              </Descriptions.Item>

              <Descriptions.Item label="Duration">
                {formatDuration(scene.duration)}
              </Descriptions.Item>

              <Descriptions.Item label="File Size">
                {formatFileSize(scene.size)}
              </Descriptions.Item>

              <Descriptions.Item label="Resolution">
                {scene.width}x{scene.height}
              </Descriptions.Item>

              <Descriptions.Item label="Frame Rate">
                {scene.framerate ? `${scene.framerate} fps` : 'N/A'}
              </Descriptions.Item>

              <Descriptions.Item label="Bitrate">
                {formatBitrate(scene.bitrate)}
              </Descriptions.Item>

              <Descriptions.Item label="Codec">
                {scene.video_codec || 'N/A'}
              </Descriptions.Item>

              <Descriptions.Item label="Organized">
                <Tag color={scene.organized ? 'green' : 'red'}>
                  {scene.organized ? 'Yes' : 'No'}
                </Tag>
              </Descriptions.Item>
            </Descriptions>

            <Divider>Performers</Divider>
            <div className={styles.performers}>
              {scene.performers && scene.performers.length > 0 ? (
                <Space size={8} wrap>
                  {scene.performers.map((performer) => (
                    <Tag key={performer.id} color="purple">
                      {performer.name}
                    </Tag>
                  ))}
                </Space>
              ) : (
                <span className={styles.empty}>No performers</span>
              )}
              {onEdit && (
                <Button
                  type="link"
                  icon={<EditOutlined />}
                  size="small"
                  onClick={() => onEdit('performers')}
                >
                  Edit Performers
                </Button>
              )}
            </div>

            <Divider>Tags</Divider>
            <div className={styles.tags}>
              {scene.tags && scene.tags.length > 0 ? (
                <Space size={8} wrap>
                  {scene.tags.map((tag) => (
                    <Tag key={tag.id}>{tag.name}</Tag>
                  ))}
                </Space>
              ) : (
                <span className={styles.empty}>No tags</span>
              )}
              {onEdit && (
                <Button
                  type="link"
                  icon={<EditOutlined />}
                  size="small"
                  onClick={() => onEdit('tags')}
                >
                  Edit Tags
                </Button>
              )}
            </div>

            <Divider>File Information</Divider>
            <Descriptions bordered column={1}>
              <Descriptions.Item label="File Path">
                <Space>
                  <FolderOpenOutlined />
                  <code>{(scene.paths && scene.paths[0]) || 'N/A'}</code>
                </Space>
              </Descriptions.Item>

              {scene.url && (
                <Descriptions.Item label="URL">
                  <Space>
                    <LinkOutlined />
                    <a
                      href={scene.url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {scene.url}
                    </a>
                  </Space>
                </Descriptions.Item>
              )}

              <Descriptions.Item label="Added to Stash">
                {new Date(scene.stash_created_at).toLocaleString()}
              </Descriptions.Item>

              <Descriptions.Item label="Last Updated">
                {scene.stash_updated_at
                  ? new Date(scene.stash_updated_at).toLocaleString()
                  : 'N/A'}
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          {false && (
            <Card title="Analysis Results" className={styles.sideCard}>
              {scene.analysis_results?.map((result) => (
                <div key={result.id} className={styles.analysisResult}>
                  <Tag color="blue">{result.plan?.name || 'Analysis'}</Tag>
                  <div className={styles.extractedData}>
                    {Object.entries(result.extracted_data).map(
                      ([key, value]) => (
                        <div key={key}>
                          <strong>{key}:</strong> {JSON.stringify(value)}
                        </div>
                      )
                    )}
                  </div>
                </div>
              ))}
            </Card>
          )}

          {relatedScenes.length > 0 && (
            <Card title="Related Scenes" className={styles.sideCard}>
              <div className={styles.relatedScenes}>
                {relatedScenes.map((relatedScene) => (
                  <SceneCard
                    key={relatedScene.id}
                    scene={relatedScene}
                    showDetails={false}
                  />
                ))}
              </div>
            </Card>
          )}

          <Card title="Actions" className={styles.sideCard}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Button icon={<DownloadOutlined />} style={{ width: '100%' }}>
                Download
              </Button>
              <Button
                icon={<LinkOutlined />}
                style={{ width: '100%' }}
                onClick={handleOpenInStash}
                disabled={!hasStashUrl}
              >
                Open in Stash
              </Button>
              <Button
                icon={<ApiOutlined />}
                style={{ width: '100%' }}
                onClick={handleOpenInAPI}
              >
                Open in API
              </Button>
              <Button danger style={{ width: '100%' }}>
                Delete Scene
              </Button>
            </Space>
          </Card>
        </Col>
      </Row>
    </div>
  );
};
