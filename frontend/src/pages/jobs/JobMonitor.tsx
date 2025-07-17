import React, { useState, useEffect, useMemo } from 'react';
import {
  Card,
  Table,
  Tag,
  Progress,
  Button,
  Space,
  Tooltip,
  Modal,
  Descriptions,
  Typography,
  Row,
  Col,
  Alert,
  Badge,
  Divider,
  message,
  Empty,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  SyncOutlined,
  CloseCircleOutlined,
  RedoOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ClockCircleOutlined,
  LoadingOutlined,
  ExpandOutlined,
  FileTextOutlined,
  BugOutlined,
} from '@ant-design/icons';
import { apiClient } from '@/services/apiClient';
import { Job } from '@/types/models';
import {
  AnalysisJobResult,
  AnalysisJobResultData,
} from '@/components/jobs/AnalysisJobResult';
import styles from './JobMonitor.module.scss';

const { Text, Title, Paragraph } = Typography;

interface JobWithExpanded extends Job {
  key: string;
}

const JobMonitor: React.FC = () => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(false);
  const [expandedRowKeys, setExpandedRowKeys] = useState<string[]>([]);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [_refreshInterval, setRefreshInterval] =
    useState<NodeJS.Timeout | null>(null);

  const fetchJobs = async () => {
    try {
      setLoading(true);
      const jobs = await apiClient.getJobs({ limit: 50 });
      setJobs(jobs);
    } catch (error) {
      console.error('Failed to fetch jobs:', error);
      void message.error('Failed to fetch jobs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchJobs();

    // Set up auto-refresh every 5 seconds
    const interval = setInterval(() => {
      void fetchJobs();
    }, 5000);
    setRefreshInterval(interval);

    return () => {
      if (interval) {
        clearInterval(interval);
      }
    };
  }, []);

  const handleCancel = async (jobId: string) => {
    try {
      await apiClient.cancelJob(jobId);
      void message.success('Job cancelled successfully');
      await fetchJobs();
    } catch (error) {
      console.error('Failed to cancel job:', error);
      void message.error('Failed to cancel job');
    }
  };

  const handleRetry = async (jobId: string) => {
    try {
      await apiClient.retryJob(jobId);
      void message.success('Job retry initiated');
      await fetchJobs();
    } catch (error) {
      console.error('Failed to retry job:', error);
      void message.error('Failed to retry job');
    }
  };

  const showJobDetails = (job: Job) => {
    setSelectedJob(job);
    setDetailModalVisible(true);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'failed':
        return <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />;
      case 'running':
        return <LoadingOutlined style={{ color: '#1890ff' }} />;
      case 'pending':
        return <ClockCircleOutlined style={{ color: '#faad14' }} />;
      case 'cancelled':
        return <CloseCircleOutlined style={{ color: '#ff7a45' }} />;
      default:
        return <InfoCircleOutlined />;
    }
  };

  const getJobTypeColor = (type: string) => {
    if (type.includes('sync')) return 'blue';
    if (type.includes('analysis')) return 'green';
    if (type.includes('test')) return 'purple';
    return 'default';
  };

  const formatDuration = (start?: string, end?: string) => {
    if (!start) return '-';
    const startTime = new Date(start).getTime();
    const endTime = end ? new Date(end).getTime() : Date.now();
    const duration = endTime - startTime;

    const seconds = Math.floor(duration / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) {
      return `${hours}h ${minutes % 60}m ${seconds % 60}s`;
    } else if (minutes > 0) {
      return `${minutes}m ${seconds % 60}s`;
    } else {
      return `${seconds}s`;
    }
  };

  const expandedRowRender = (record: Job) => {
    return (
      <div className={styles.expandedContent}>
        <Row gutter={[16, 16]}>
          <Col span={12}>
            <Card size="small" title="Job Information">
              <Descriptions column={1} size="small">
                <Descriptions.Item label="Job ID">
                  {record.id}
                </Descriptions.Item>
                {record.name && (
                  <Descriptions.Item label="Name">
                    {record.name}
                  </Descriptions.Item>
                )}
                <Descriptions.Item label="Duration">
                  {formatDuration(record.started_at, record.completed_at)}
                </Descriptions.Item>
                <Descriptions.Item label="Progress">
                  {record.processed_items && record.total ? (
                    <Text>
                      {record.processed_items} / {record.total} items
                    </Text>
                  ) : (
                    <Text>{record.progress}%</Text>
                  )}
                </Descriptions.Item>
              </Descriptions>
            </Card>
          </Col>

          <Col span={12}>
            <Card size="small" title="Status & Messages">
              {record.metadata?.last_message && (
                <div style={{ marginBottom: 16 }}>
                  <Text strong>Last Message:</Text>
                  <Paragraph
                    style={{
                      marginTop: 8,
                      padding: 8,
                      background: '#f5f5f5',
                      borderRadius: 4,
                    }}
                  >
                    {record.metadata.last_message}
                  </Paragraph>
                </div>
              )}

              {record.error && (
                <Alert
                  message="Error Details"
                  description={record.error}
                  type="error"
                  showIcon
                  icon={<BugOutlined />}
                />
              )}
            </Card>
          </Col>
        </Row>

        {record.result && Object.keys(record.result).length > 0 && (
          <Card
            size="small"
            title="Result Details"
            style={{ marginTop: 16 }}
            extra={
              <Button
                type="link"
                size="small"
                icon={<ExpandOutlined />}
                onClick={() => showJobDetails(record)}
              >
                View Full Details
              </Button>
            }
          >
            {record.type === 'scene_analysis' ||
            record.type === 'batch_analysis' ||
            record.type === 'analysis' ? (
              <AnalysisJobResult
                result={record.result as unknown as AnalysisJobResultData}
              />
            ) : (
              <pre style={{ maxHeight: 200, overflow: 'auto' }}>
                {JSON.stringify(record.result, null, 2)}
              </pre>
            )}
          </Card>
        )}
      </div>
    );
  };

  const columns: ColumnsType<JobWithExpanded> = [
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string, record: JobWithExpanded) => {
        const icon = getStatusIcon(status);
        const lastMessage = record.metadata?.last_message;

        return (
          <Space>
            {icon}
            <Tag
              color={
                status === 'completed'
                  ? 'success'
                  : status === 'failed'
                    ? 'error'
                    : status === 'running'
                      ? 'processing'
                      : status === 'cancelled'
                        ? 'warning'
                        : 'default'
              }
            >
              {status.toUpperCase()}
            </Tag>
            {lastMessage && status === 'running' && (
              <Tooltip title={lastMessage}>
                <Badge status="processing" />
              </Tooltip>
            )}
          </Space>
        );
      },
    },
    {
      title: 'Job Type',
      dataIndex: 'type',
      key: 'type',
      width: 150,
      render: (type: string) => {
        const typeLabels: Record<string, string> = {
          sync_all: 'Full Sync',
          scene_sync: 'Scene Sync',
          scene_analysis: 'Scene Analysis',
          batch_analysis: 'Batch Analysis',
          sync_scenes: 'Sync Scenes',
          sync_performers: 'Sync Performers',
          sync_tags: 'Sync Tags',
          sync_studios: 'Sync Studios',
          analysis: 'Analysis',
          apply_plan: 'Apply Plan',
          settings_test: 'Settings Test',
        };

        return (
          <Tag color={getJobTypeColor(type)}>
            {typeLabels[type] || type.replace(/_/g, ' ').toUpperCase()}
          </Tag>
        );
      },
    },
    {
      title: 'Progress',
      key: 'progress',
      width: 200,
      render: (_: unknown, record: Job) => {
        const percent = Math.round(record.progress || 0);
        const hasMessage = !!record.metadata?.last_message;

        return (
          <div style={{ minWidth: 150 }}>
            <Progress
              percent={percent}
              status={
                record.status === 'failed'
                  ? 'exception'
                  : record.status === 'completed'
                    ? 'success'
                    : 'active'
              }
              size="small"
              format={(percent: number | undefined) => (
                <Space size={4}>
                  <span>{percent}%</span>
                  {hasMessage && record.status === 'running' && (
                    <Tooltip
                      title={record.metadata?.last_message}
                      placement="top"
                    >
                      <FileTextOutlined style={{ fontSize: 12 }} />
                    </Tooltip>
                  )}
                </Space>
              )}
            />
            {record.processed_items !== undefined && record.total && (
              <Text type="secondary" style={{ fontSize: 12 }}>
                {record.processed_items} / {record.total} items
              </Text>
            )}
          </div>
        );
      },
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => (
        <Tooltip title={new Date(date).toLocaleString()}>
          <Text>{new Date(date).toLocaleTimeString()}</Text>
        </Tooltip>
      ),
    },
    {
      title: 'Duration',
      key: 'duration',
      width: 120,
      render: (_: unknown, record: Job) => (
        <Text type="secondary">
          {formatDuration(record.started_at, record.completed_at)}
        </Text>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 200,
      render: (_: unknown, record: Job) => (
        <Space>
          <Tooltip title="View Details">
            <Button
              type="text"
              icon={<InfoCircleOutlined />}
              size="small"
              onClick={() => showJobDetails(record)}
            />
          </Tooltip>

          {record.status === 'running' && (
            <Tooltip title="Cancel Job">
              <Button
                type="text"
                danger
                icon={<CloseCircleOutlined />}
                size="small"
                onClick={() => void handleCancel(record.id)}
              />
            </Tooltip>
          )}

          {record.status === 'failed' && (
            <Tooltip title="Retry Job">
              <Button
                type="text"
                icon={<RedoOutlined />}
                size="small"
                onClick={() => void handleRetry(record.id)}
              />
            </Tooltip>
          )}
        </Space>
      ),
    },
  ];

  // Add keys to jobs for table
  const jobsWithKeys = useMemo(
    () => jobs.map((job) => ({ ...job, key: job.id })),
    [jobs]
  );

  // Filter jobs by status
  const runningJobs = jobsWithKeys.filter((job) => job.status === 'running');
  const pendingJobs = jobsWithKeys.filter((job) => job.status === 'pending');
  const failedJobs = jobsWithKeys.filter((job) => job.status === 'failed');

  return (
    <div className={styles.jobMonitor}>
      <div className={styles.header}>
        <Title level={2}>Job Monitor</Title>
        <Space>
          <Badge count={runningJobs.length} showZero color="blue">
            <Tag color="blue">Running</Tag>
          </Badge>
          <Badge count={pendingJobs.length} showZero color="orange">
            <Tag color="orange">Pending</Tag>
          </Badge>
          <Badge count={failedJobs.length} showZero color="red">
            <Tag color="red">Failed</Tag>
          </Badge>
        </Space>
      </div>

      <Card
        className={styles.mainCard}
        extra={
          <Button
            icon={<SyncOutlined />}
            onClick={() => void fetchJobs()}
            loading={loading}
          >
            Refresh
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={jobsWithKeys}
          loading={loading}
          rowKey="key"
          expandable={{
            expandedRowRender,
            expandedRowKeys,
            onExpandedRowsChange: setExpandedRowKeys,
            expandRowByClick: true,
            rowExpandable: (record: JobWithExpanded) =>
              !!record.metadata?.last_message ||
              !!record.error ||
              !!record.result,
          }}
          pagination={{
            pageSize: 20,
            showSizeChanger: true,
            showTotal: (total) => `Total ${total} jobs`,
          }}
          locale={{
            emptyText: (
              <Empty
                description="No jobs found"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            ),
          }}
        />
      </Card>

      {/* Job Detail Modal */}
      <Modal
        title={
          <Space>
            <InfoCircleOutlined />
            Job Details
          </Space>
        }
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            Close
          </Button>,
        ]}
        width={800}
      >
        {selectedJob && (
          <div className={styles.jobDetailModal}>
            <Descriptions
              bordered
              column={2}
              size="small"
              style={{ marginBottom: 16 }}
            >
              <Descriptions.Item label="Job ID" span={2}>
                <Text copyable>{selectedJob.id}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="Type">
                <Tag color={getJobTypeColor(selectedJob.type)}>
                  {selectedJob.type.replace(/_/g, ' ').toUpperCase()}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Status">
                <Space>
                  {getStatusIcon(selectedJob.status)}
                  <Tag
                    color={
                      selectedJob.status === 'completed'
                        ? 'success'
                        : selectedJob.status === 'failed'
                          ? 'error'
                          : selectedJob.status === 'running'
                            ? 'processing'
                            : 'default'
                    }
                  >
                    {selectedJob.status.toUpperCase()}
                  </Tag>
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="Progress" span={2}>
                <Progress
                  percent={selectedJob.progress}
                  status={
                    selectedJob.status === 'failed'
                      ? 'exception'
                      : selectedJob.status === 'completed'
                        ? 'success'
                        : 'active'
                  }
                />
              </Descriptions.Item>
              <Descriptions.Item label="Created">
                {new Date(selectedJob.created_at).toLocaleString()}
              </Descriptions.Item>
              <Descriptions.Item label="Duration">
                {formatDuration(
                  selectedJob.started_at,
                  selectedJob.completed_at
                )}
              </Descriptions.Item>
            </Descriptions>

            {selectedJob.metadata?.last_message && (
              <>
                <Divider orientation="left">Last Message</Divider>
                <Alert
                  message={selectedJob.metadata.last_message}
                  type="info"
                  showIcon
                />
              </>
            )}

            {selectedJob.error && (
              <>
                <Divider orientation="left">Error Details</Divider>
                <Alert
                  message="Job Failed"
                  description={selectedJob.error}
                  type="error"
                  showIcon
                />
              </>
            )}

            {selectedJob.parameters &&
              Object.keys(selectedJob.parameters).length > 0 && (
                <>
                  <Divider orientation="left">Parameters</Divider>
                  <pre className={styles.codeBlock}>
                    {JSON.stringify(selectedJob.parameters, null, 2)}
                  </pre>
                </>
              )}

            {selectedJob.result &&
              Object.keys(selectedJob.result).length > 0 && (
                <>
                  <Divider orientation="left">Result</Divider>
                  {selectedJob.type === 'scene_analysis' ||
                  selectedJob.type === 'batch_analysis' ||
                  selectedJob.type === 'analysis' ? (
                    <AnalysisJobResult
                      result={
                        selectedJob.result as unknown as AnalysisJobResultData
                      }
                    />
                  ) : (
                    <pre className={styles.codeBlock}>
                      {JSON.stringify(selectedJob.result, null, 2)}
                    </pre>
                  )}
                </>
              )}

            {selectedJob.metadata &&
              Object.keys(selectedJob.metadata).length > 1 && (
                <>
                  <Divider orientation="left">Metadata</Divider>
                  <pre className={styles.codeBlock}>
                    {JSON.stringify(
                      Object.fromEntries(
                        Object.entries(selectedJob.metadata).filter(
                          ([key]) => key !== 'last_message'
                        )
                      ),
                      null,
                      2
                    )}
                  </pre>
                </>
              )}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default JobMonitor;
