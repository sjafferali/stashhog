import React, { useState, useEffect } from 'react';
import {
  Card,
  Badge,
  Progress,
  Button,
  Space,
  Tooltip,
  Tag,
  Typography,
  Row,
  Col,
  Collapse,
  message,
} from 'antd';
import {
  PlayCircleOutlined,
  ClockCircleOutlined,
  StopOutlined,
  InfoCircleOutlined,
  CloseCircleOutlined,
  RedoOutlined,
  FileTextOutlined,
  VideoCameraOutlined,
  LoadingOutlined,
  UpOutlined,
  DownOutlined,
} from '@ant-design/icons';
import { Link } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import { Job } from '@/types/models';
import { getJobTypeLabel, getJobTypeColor } from '@/utils/jobUtils';

const { Text } = Typography;

interface ActiveJobsSectionProps {
  onCancel: (jobId: string) => Promise<void>;
  onRetry: (jobId: string) => Promise<void>;
  onRefresh: () => void;
  className?: string;
}

const ActiveJobsSection: React.FC<ActiveJobsSectionProps> = ({
  onCancel,
  onRetry,
  onRefresh,
  className,
}) => {
  const [activeJobs, setActiveJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  const fetchActiveJobs = async () => {
    try {
      setLoading(true);
      const jobs = await apiClient.getActiveJobs();
      setActiveJobs(jobs);
    } catch (error) {
      console.error('Failed to fetch active jobs:', error);
      void message.error('Failed to fetch active jobs');
      setActiveJobs([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchActiveJobs();

    // Set up auto-refresh every 2 seconds for active jobs
    const interval = setInterval(() => {
      void fetchActiveJobs();
    }, 2000);

    return () => {
      clearInterval(interval);
    };
  }, []);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <LoadingOutlined style={{ color: '#1890ff' }} />;
      case 'pending':
        return <ClockCircleOutlined style={{ color: '#faad14' }} />;
      case 'cancelling':
        return <StopOutlined style={{ color: '#ff7a45' }} />;
      default:
        return <InfoCircleOutlined />;
    }
  };

  const formatDuration = (start?: string) => {
    if (!start) return '-';
    const startTime = new Date(start).getTime();
    const endTime = Date.now();
    const duration = endTime - startTime;

    const seconds = Math.floor(duration / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) {
      return `${hours}h ${minutes % 60}m`;
    } else if (minutes > 0) {
      return `${minutes}m ${seconds % 60}s`;
    } else {
      return `${seconds}s`;
    }
  };

  const getJobSceneIds = (job: Job): string[] | null => {
    if (job.metadata?.scene_ids && Array.isArray(job.metadata.scene_ids)) {
      return job.metadata.scene_ids as string[];
    }
    if (job.parameters?.scene_ids && Array.isArray(job.parameters.scene_ids)) {
      return job.parameters.scene_ids as string[];
    }
    return null;
  };

  const shouldShowViewScenesButton = (job: Job): boolean => {
    const qualifyingTypes = [
      'sync',
      'sync_scenes',
      'scene_sync',
      'analysis',
      'scene_analysis',
      'apply_plan',
    ];

    if (!qualifyingTypes.includes(job.type)) {
      return false;
    }

    const sceneIds = getJobSceneIds(job);
    return sceneIds !== null && sceneIds.length > 0;
  };

  if (activeJobs.length === 0) {
    return null; // Don't show section if no active jobs
  }

  const runningCount = activeJobs.filter(
    (job) => job.status === 'running'
  ).length;
  const pendingCount = activeJobs.filter(
    (job) => job.status === 'pending'
  ).length;
  const cancellingCount = activeJobs.filter(
    (job) => job.status === 'cancelling'
  ).length;

  return (
    <Card
      className={className}
      title={
        <Space>
          <PlayCircleOutlined />
          <span>Active Jobs</span>
          <Badge count={runningCount} showZero={false} color="blue" />
          <Badge count={pendingCount} showZero={false} color="orange" />
          <Badge count={cancellingCount} showZero={false} color="red" />
        </Space>
      }
      extra={
        <Space>
          <Button
            type="text"
            size="small"
            icon={collapsed ? <DownOutlined /> : <UpOutlined />}
            onClick={() => setCollapsed(!collapsed)}
          >
            {collapsed ? 'Show' : 'Hide'}
          </Button>
          <Button
            type="text"
            size="small"
            icon={<LoadingOutlined />}
            onClick={onRefresh}
            loading={loading}
          />
        </Space>
      }
      size="small"
      style={{ marginBottom: 16 }}
    >
      <Collapse
        ghost
        activeKey={collapsed ? [] : ['active']}
        onChange={(keys) => setCollapsed(!keys.includes('active'))}
      >
        <Collapse.Panel key="active" header="">
          {loading && activeJobs.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '20px' }}>
              <LoadingOutlined style={{ fontSize: 24 }} />
            </div>
          ) : (
            <Row gutter={[16, 16]}>
              {activeJobs.map((job) => (
                <Col key={job.id} xs={24} sm={24} md={12} lg={8} xl={6}>
                  <Card
                    size="small"
                    style={{
                      borderLeft: `4px solid ${
                        job.status === 'running'
                          ? '#1890ff'
                          : job.status === 'pending'
                            ? '#faad14'
                            : '#ff7a45'
                      }`,
                    }}
                  >
                    <div style={{ marginBottom: 8 }}>
                      <Space>
                        {getStatusIcon(job.status)}
                        <Tag color={getJobTypeColor(job.type)}>
                          {getJobTypeLabel(job.type)}
                        </Tag>
                      </Space>
                    </div>

                    <div style={{ marginBottom: 12 }}>
                      <Progress
                        percent={Math.round(job.progress || 0)}
                        status={
                          job.status === 'running'
                            ? 'active'
                            : job.status === 'cancelling'
                              ? 'exception'
                              : 'normal'
                        }
                        size="small"
                        format={(percent: number) => `${percent}%`}
                      />

                      {job.processed_items !== undefined &&
                        job.total !== undefined &&
                        job.total !== null && (
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            {job.processed_items} / {job.total} items
                          </Text>
                        )}
                    </div>

                    {job.metadata?.last_message && (
                      <div style={{ marginBottom: 8 }}>
                        <Text
                          type="secondary"
                          style={{
                            fontSize: 12,
                            display: 'block',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                          title={job.metadata.last_message}
                        >
                          {job.metadata.last_message}
                        </Text>
                      </div>
                    )}

                    <div style={{ marginBottom: 8 }}>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        Running for {formatDuration(job.started_at)}
                      </Text>
                    </div>

                    <Space size="small" wrap>
                      <Tooltip title="View Details">
                        <Button
                          type="text"
                          icon={<InfoCircleOutlined />}
                          size="small"
                        />
                      </Tooltip>

                      {(job.type === 'scene_analysis' ||
                        job.type === 'analysis' ||
                        job.type === 'non_ai_analysis') &&
                        job.metadata &&
                        'plan_id' in job.metadata &&
                        job.metadata.plan_id && (
                          <Tooltip title="View Plan">
                            <Link
                              to={`/analysis/plans/${String(job.metadata.plan_id)}`}
                            >
                              <Button
                                type="text"
                                icon={<FileTextOutlined />}
                                size="small"
                                style={{ color: '#1890ff' }}
                              />
                            </Link>
                          </Tooltip>
                        )}

                      {shouldShowViewScenesButton(job) && (
                        <Tooltip title="View Impacted Scenes">
                          <Link
                            to={`/scenes?scene_ids=${getJobSceneIds(job)?.join(',') || ''}`}
                          >
                            <Button
                              type="text"
                              icon={<VideoCameraOutlined />}
                              size="small"
                              style={{ color: '#52c41a' }}
                            />
                          </Link>
                        </Tooltip>
                      )}

                      {['running', 'pending'].includes(job.status) && (
                        <Tooltip title="Cancel Job">
                          <Button
                            type="text"
                            danger
                            icon={<CloseCircleOutlined />}
                            size="small"
                            onClick={() => void onCancel(job.id)}
                          />
                        </Tooltip>
                      )}

                      {job.status === 'failed' && (
                        <Tooltip title="Retry Job">
                          <Button
                            type="text"
                            icon={<RedoOutlined />}
                            size="small"
                            onClick={() => void onRetry(job.id)}
                          />
                        </Tooltip>
                      )}
                    </Space>
                  </Card>
                </Col>
              ))}
            </Row>
          )}
        </Collapse.Panel>
      </Collapse>
    </Card>
  );
};

export default ActiveJobsSection;
