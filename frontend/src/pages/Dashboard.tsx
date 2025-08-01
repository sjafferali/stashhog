import React, { useEffect, useState } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Spin,
  Button,
  Badge,
  Space,
  Alert,
  Typography,
  Progress,
  Timeline,
  Tag,
} from 'antd';
import {
  VideoCameraOutlined,
  UserOutlined,
  TagsOutlined,
  HomeOutlined,
  SyncOutlined,
  ExperimentOutlined,
  FileSearchOutlined,
  PlayCircleOutlined,
  FolderOutlined,
  RightOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  ExclamationCircleOutlined,
  StopOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import apiClient from '@/services/apiClient';
import { SyncStatus, ActionableItem } from '@/types/models';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';

dayjs.extend(relativeTime);

const { Title, Text, Paragraph } = Typography;

interface ProcessedTorrent {
  name: string;
  file_count: number;
  processed_at: string;
}

const Dashboard: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<SyncStatus | null>(null);
  const [syncingScenes, setSyncingScenes] = useState(false);
  const [analyzingScenes] = useState(false);
  const [recentTorrents, setRecentTorrents] = useState<ProcessedTorrent[]>([]);
  const navigate = useNavigate();

  const fetchStats = async () => {
    try {
      const data = await apiClient.getSyncStatus();
      setStats(data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  };

  const fetchRecentTorrents = async () => {
    try {
      const data = await apiClient.getRecentProcessedTorrents(10);
      setRecentTorrents(data.torrents);
    } catch (error) {
      console.error('Failed to fetch recent torrents:', error);
    }
  };

  useEffect(() => {
    const loadInitialStats = async () => {
      try {
        setLoading(true);
        await Promise.all([fetchStats(), fetchRecentTorrents()]);
      } finally {
        setLoading(false);
      }
    };

    void loadInitialStats();
  }, []);

  // Auto-refresh when there are running jobs
  useEffect(() => {
    if (
      stats?.jobs?.running_jobs?.length &&
      stats.jobs.running_jobs.length > 0
    ) {
      const interval = setInterval(() => {
        void fetchStats();
      }, 3000); // Refresh every 3 seconds
      return () => clearInterval(interval);
    }
  }, [stats?.jobs?.running_jobs]);

  const handleAction = async (item: ActionableItem) => {
    if (item.route) {
      void navigate(item.route);
      return;
    }

    switch (item.action) {
      case 'sync_scenes':
        setSyncingScenes(true);
        try {
          await apiClient.startSync();
          // Refresh stats after sync
          await fetchStats();
        } catch (error) {
          console.error('Failed to start sync:', error);
        } finally {
          setSyncingScenes(false);
        }
        break;

      case 'analyze_scenes':
        // Navigate to scenes page instead of analyzing
        void navigate('/scenes');
        break;

      case 'analyze_videos':
        void navigate('/analysis/generate?video_analysis=true');
        break;
    }
  };

  const getActionIcon = (type: string) => {
    switch (type) {
      case 'sync':
        return <SyncOutlined />;
      case 'analysis':
        return <ExperimentOutlined />;
      case 'organization':
        return <FolderOutlined />;
      case 'system':
        return <ExclamationCircleOutlined />;
      default:
        return <FileSearchOutlined />;
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'error';
      case 'medium':
        return 'warning';
      case 'low':
        return 'default';
      default:
        return 'default';
    }
  };

  const getJobIcon = (status: string) => {
    switch (status) {
      case 'running':
      case 'pending':
        return <LoadingOutlined spin />;
      case 'completed':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'failed':
        return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
      case 'cancelled':
        return <StopOutlined style={{ color: '#faad14' }} />;
      default:
        return <ClockCircleOutlined />;
    }
  };

  const getJobTypeLabel = (type: string) => {
    switch (type) {
      case 'sync':
      case 'sync_all':
        return 'Full Sync';
      case 'sync_scenes':
      case 'scene_sync':
        return 'Scene Sync';
      case 'analysis':
        return 'Scene Analysis';
      case 'apply_plan':
        return 'Apply Analysis Plan';
      default:
        return type;
    }
  };

  const getJobStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'processing';
      case 'pending':
        return 'default';
      case 'completed':
        return 'success';
      case 'failed':
        return 'error';
      case 'cancelled':
        return 'warning';
      default:
        return 'default';
    }
  };

  if (loading || !stats) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
      </div>
    );
  }

  const visibleItems = stats.actionable_items.filter((item) => item.visible);

  return (
    <div>
      <Title level={2}>Dashboard</Title>

      {/* Summary Statistics */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Scenes"
              value={stats.summary.scene_count}
              prefix={<VideoCameraOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Performers"
              value={stats.summary.performer_count}
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Tags"
              value={stats.summary.tag_count}
              prefix={<TagsOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Studios"
              value={stats.summary.studio_count}
              prefix={<HomeOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Running Jobs */}
      {stats.jobs.running_jobs.length > 0 && (
        <Card
          title={
            <Space>
              <LoadingOutlined spin />
              Running Operations ({stats.jobs.running_jobs.length})
            </Space>
          }
          style={{ marginBottom: 24 }}
        >
          <Timeline
            items={stats.jobs.running_jobs.map((job) => ({
              color: 'blue',
              dot: getJobIcon(job.status),
              children: (
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Space>
                    <Text strong>{getJobTypeLabel(job.type)}</Text>
                    <Tag color={getJobStatusColor(job.status)}>
                      {job.status}
                    </Tag>
                  </Space>
                  {job.progress !== undefined && (
                    <Progress
                      percent={Math.round(job.progress)}
                      size="small"
                      status="active"
                    />
                  )}
                  {job.created_at && (
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      Started {dayjs(job.created_at).fromNow()}
                    </Text>
                  )}
                </Space>
              ),
            }))}
          />
        </Card>
      )}

      {/* Active Operations Alert */}
      {(stats.sync.is_syncing || stats.analysis.is_analyzing) &&
        !stats.jobs.running_jobs.length && (
          <Alert
            message="Operations in Progress"
            description={
              <Space direction="vertical">
                {stats.sync.is_syncing && (
                  <Text>
                    <SyncOutlined spin /> Sync operation is running...
                  </Text>
                )}
                {stats.analysis.is_analyzing && (
                  <Text>
                    <ExperimentOutlined spin /> Analysis operation is running...
                  </Text>
                )}
              </Space>
            }
            type="info"
            showIcon
            style={{ marginBottom: 24 }}
          />
        )}

      {/* Actionable Items */}
      {visibleItems.length > 0 && (
        <>
          <Title level={3} style={{ marginBottom: 16 }}>
            <FileSearchOutlined /> Action Required
          </Title>

          <Row gutter={[16, 16]}>
            {visibleItems.map((item) => (
              <Col xs={24} sm={12} lg={8} key={item.id}>
                <Card
                  hoverable
                  style={{ height: '100%' }}
                  actions={[
                    <Button
                      key="action"
                      type={item.priority === 'high' ? 'primary' : 'default'}
                      danger={item.priority === 'high'}
                      icon={getActionIcon(item.type)}
                      loading={
                        (item.action === 'sync_scenes' && syncingScenes) ||
                        (item.action === 'analyze_scenes' && analyzingScenes)
                      }
                      onClick={() => void handleAction(item)}
                    >
                      {item.action_label}
                    </Button>,
                  ]}
                >
                  <Card.Meta
                    avatar={
                      <Badge
                        count={item.count}
                        showZero
                        color={getPriorityColor(item.priority)}
                      >
                        <div style={{ fontSize: 24, padding: 8 }}>
                          {getActionIcon(item.type)}
                        </div>
                      </Badge>
                    }
                    title={item.title}
                    description={item.description}
                  />
                </Card>
              </Col>
            ))}
          </Row>
        </>
      )}

      {/* Progress Overview */}
      <Title level={3} style={{ marginTop: 32, marginBottom: 16 }}>
        <PlayCircleOutlined /> Progress Overview
      </Title>
      <Row gutter={[16, 16]}>
        <Col xs={24} md={12}>
          <Card title="Analysis Progress">
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <Text>Scene Analysis</Text>
                <Progress
                  percent={Math.round(
                    ((stats.summary.scene_count -
                      stats.analysis.scenes_not_analyzed) /
                      stats.summary.scene_count) *
                      100
                  )}
                  status={
                    stats.analysis.scenes_not_analyzed === 0
                      ? 'success'
                      : 'active'
                  }
                />
              </div>
              <div>
                <Text>Video Analysis</Text>
                <Progress
                  percent={Math.round(
                    ((stats.summary.scene_count -
                      stats.analysis.scenes_not_video_analyzed) /
                      stats.summary.scene_count) *
                      100
                  )}
                  status={
                    stats.analysis.scenes_not_video_analyzed === 0
                      ? 'success'
                      : 'normal'
                  }
                />
              </div>
            </Space>
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card title="Metadata Quality">
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <Text>Scene Organization</Text>
                <Progress
                  percent={Math.round(
                    ((stats.summary.scene_count -
                      stats.organization.unorganized_scenes) /
                      stats.summary.scene_count) *
                      100
                  )}
                  status={
                    stats.organization.unorganized_scenes === 0
                      ? 'success'
                      : 'normal'
                  }
                />
              </div>
              <div>
                <Text>Scene Details</Text>
                <Progress
                  percent={Math.round(
                    ((stats.summary.scene_count -
                      stats.metadata.scenes_missing_details) /
                      stats.summary.scene_count) *
                      100
                  )}
                  status={
                    stats.metadata.scenes_missing_details === 0
                      ? 'success'
                      : 'normal'
                  }
                />
              </div>
              <div>
                <Text>Studio Assignment</Text>
                <Progress
                  percent={Math.round(
                    ((stats.summary.scene_count -
                      stats.metadata.scenes_without_studio) /
                      stats.summary.scene_count) *
                      100
                  )}
                  status={
                    stats.metadata.scenes_without_studio === 0
                      ? 'success'
                      : 'normal'
                  }
                />
              </div>
            </Space>
          </Card>
        </Col>
      </Row>

      {/* Recently Completed Jobs */}
      {stats.jobs.completed_jobs.length > 0 && (
        <Card
          title="Recent Operations"
          style={{ marginTop: 24 }}
          extra={
            <Button
              type="link"
              onClick={() => void navigate('/jobs')}
              icon={<RightOutlined />}
            >
              View All
            </Button>
          }
        >
          <Timeline
            items={stats.jobs.completed_jobs.slice(0, 5).map((job) => ({
              color:
                job.status === 'completed'
                  ? 'green'
                  : job.status === 'failed'
                    ? 'red'
                    : 'orange',
              dot: getJobIcon(job.status),
              children: (
                <Space direction="vertical">
                  <Space>
                    <Text>{getJobTypeLabel(job.type)}</Text>
                    <Tag color={getJobStatusColor(job.status)}>
                      {job.status}
                    </Tag>
                  </Space>
                  {job.error && (
                    <Paragraph
                      type="danger"
                      ellipsis={{ rows: 2, expandable: true }}
                      style={{ marginBottom: 0 }}
                    >
                      {job.error}
                    </Paragraph>
                  )}
                  {job.completed_at && (
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {dayjs(job.completed_at).fromNow()}
                    </Text>
                  )}
                </Space>
              ),
            }))}
          />
        </Card>
      )}

      {/* Data Quality Issues */}
      {(stats.metadata.scenes_without_files > 0 ||
        stats.metadata.scenes_without_performers > 0 ||
        stats.metadata.scenes_without_tags > 0) && (
        <Card
          title={
            <Space>
              <ExclamationCircleOutlined style={{ color: '#faad14' }} />
              Data Quality Issues
            </Space>
          }
          style={{ marginTop: 24 }}
        >
          <Row gutter={[16, 16]}>
            {stats.metadata.scenes_without_files > 0 && (
              <Col xs={24} sm={8}>
                <Statistic
                  title="Scenes Without Files"
                  value={stats.metadata.scenes_without_files}
                  prefix={<ExclamationCircleOutlined />}
                  valueStyle={{ color: '#ff4d4f' }}
                />
              </Col>
            )}
            {stats.metadata.scenes_without_performers > 0 && (
              <Col xs={24} sm={8}>
                <Statistic
                  title="Scenes Without Performers"
                  value={stats.metadata.scenes_without_performers}
                  prefix={<UserOutlined />}
                  valueStyle={{ color: '#faad14' }}
                />
              </Col>
            )}
            {stats.metadata.scenes_without_tags > 0 && (
              <Col xs={24} sm={8}>
                <Statistic
                  title="Scenes Without Tags"
                  value={stats.metadata.scenes_without_tags}
                  prefix={<TagsOutlined />}
                  valueStyle={{ color: '#faad14' }}
                />
              </Col>
            )}
          </Row>
        </Card>
      )}

      {/* Recently Processed Torrents */}
      {recentTorrents.length > 0 && (
        <Card
          title={
            <Space>
              <PlayCircleOutlined />
              Recently Processed Torrents
            </Space>
          }
          style={{ marginTop: 24 }}
        >
          <Timeline
            items={recentTorrents.map((torrent) => ({
              color: 'green',
              dot: <CheckCircleOutlined />,
              children: (
                <Space direction="vertical">
                  <Space>
                    <Text strong>{torrent.name}</Text>
                    <Tag color="blue">{torrent.file_count} files</Tag>
                  </Space>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    Processed {dayjs(torrent.processed_at).fromNow()}
                  </Text>
                </Space>
              ),
            }))}
          />
        </Card>
      )}
    </div>
  );
};

export default Dashboard;
