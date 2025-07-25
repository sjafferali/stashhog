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
  message,
  Empty,
  Select,
  Collapse,
} from 'antd';
import { Link, useSearchParams } from 'react-router-dom';
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
  VideoCameraOutlined,
} from '@ant-design/icons';
import { apiClient } from '@/services/apiClient';
import { Job } from '@/types/models';
import {
  AnalysisJobResult,
  AnalysisJobResultData,
} from '@/components/jobs/AnalysisJobResult';
import { useWebSocket } from '@/hooks/useWebSocket';
import {
  getJobTypeLabel,
  getJobTypeColor,
  JOB_TYPE_LABELS,
} from '@/utils/jobUtils';
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
  const [searchParams, setSearchParams] = useSearchParams();
  const [statusFilter, setStatusFilter] = useState<string | undefined>(
    searchParams.get('status') || undefined
  );
  const [typeFilter, setTypeFilter] = useState<string | undefined>(
    searchParams.get('type') || undefined
  );
  const { lastMessage } = useWebSocket('/api/jobs/ws');

  const fetchJobs = async () => {
    try {
      setLoading(true);
      const response = await apiClient.getJobs({ limit: 50 });
      // Ensure we always have an array
      const jobsArray = Array.isArray(response) ? response : [];
      setJobs(jobsArray);
    } catch (error) {
      console.error('Failed to fetch jobs:', error);
      void message.error('Failed to fetch jobs');
      setJobs([]); // Ensure state is always an array
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

  // Handle WebSocket updates for real-time job changes
  useEffect(() => {
    if (lastMessage && typeof lastMessage === 'object') {
      const update = lastMessage as { type: string; job: Job };

      if (update.type === 'job_update' && update.job) {
        setJobs((prevJobs) => {
          const jobIndex = prevJobs.findIndex((j) => j.id === update.job.id);

          if (jobIndex >= 0) {
            // Update existing job
            const newJobs = [...prevJobs];
            newJobs[jobIndex] = update.job;
            return newJobs;
          } else {
            // Add new job at the beginning
            return [update.job, ...prevJobs];
          }
        });

        // Also update selected job if it's the same one
        if (selectedJob && selectedJob.id === update.job.id) {
          setSelectedJob(update.job);
        }
      }
    }
  }, [lastMessage, selectedJob]);

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

  const getJobSceneIds = (job: Job): string[] | null => {
    // Check different places where scene IDs might be stored

    // 1. Check metadata.scene_ids (for sync jobs)
    if (job.metadata?.scene_ids && Array.isArray(job.metadata.scene_ids)) {
      return job.metadata.scene_ids as string[];
    }

    // 2. Check parameters.scene_ids (for some sync jobs)
    if (job.parameters?.scene_ids && Array.isArray(job.parameters.scene_ids)) {
      return job.parameters.scene_ids as string[];
    }

    // 3. For analysis jobs, check if we have analyzed_scene_ids in result
    if (
      job.result?.analyzed_scene_ids &&
      Array.isArray(job.result.analyzed_scene_ids)
    ) {
      return job.result.analyzed_scene_ids as string[];
    }

    // 4. For analysis jobs with scenes_analyzed count but no explicit IDs
    // We can't determine specific scene IDs in this case
    if (job.type === 'scene_analysis' || job.type === 'analysis') {
      // Check if there's a way to get scene IDs from the result
      if (job.result?.scene_ids && Array.isArray(job.result.scene_ids)) {
        return job.result.scene_ids as string[];
      }
    }

    return null;
  };

  const shouldShowViewScenesButton = (job: Job): boolean => {
    // Check if this is a qualifying job type
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

    // Check if we can extract scene IDs
    const sceneIds = getJobSceneIds(job);
    return sceneIds !== null && sceneIds.length > 0;
  };

  const expandedRowRender = (record: Job) => {
    const hasLargeContent =
      record.result && JSON.stringify(record.result).length > 1000;

    return (
      <div className={styles.expandedContent}>
        {hasLargeContent && (
          <div
            style={{
              textAlign: 'right',
              marginBottom: 8,
              fontSize: 12,
              color: '#8c8c8c',
              fontStyle: 'italic',
            }}
          >
            Scroll to see more content ↓
          </div>
        )}
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
            {record.type === 'scene_analysis' || record.type === 'analysis' ? (
              <>
                <AnalysisJobResult
                  result={record.result as unknown as AnalysisJobResultData}
                />
                {((record.result &&
                  'plan_id' in record.result &&
                  record.result.plan_id) ||
                  (record.metadata &&
                    'plan_id' in record.metadata &&
                    record.metadata.plan_id)) && (
                  <div style={{ marginTop: 16 }}>
                    <Link
                      to={`/analysis/plans/${
                        (record.result && 'plan_id' in record.result
                          ? record.result.plan_id
                          : record.metadata?.plan_id) as string
                      }`}
                    >
                      <Button type="primary" icon={<FileTextOutlined />}>
                        View{' '}
                        {record.status === 'running' ? 'Current' : 'Created'}{' '}
                        Analysis Plan
                      </Button>
                    </Link>
                  </div>
                )}
              </>
            ) : (
              <pre className={styles.resultPreview}>
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
        return <Tag color={getJobTypeColor(type)}>{getJobTypeLabel(type)}</Tag>;
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
      width: 250,
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

          {(record.type === 'scene_analysis' || record.type === 'analysis') &&
          ((record.status === 'completed' &&
            record.result &&
            'plan_id' in record.result &&
            record.result.plan_id) ||
            (record.status === 'running' &&
              record.metadata &&
              'plan_id' in record.metadata &&
              record.metadata.plan_id)) ? (
            <Tooltip title="View Plan">
              <Link
                to={`/analysis/plans/${
                  (record.result && 'plan_id' in record.result
                    ? record.result.plan_id
                    : record.metadata?.plan_id) as string
                }`}
              >
                <Button
                  type="text"
                  icon={<FileTextOutlined />}
                  size="small"
                  style={{ color: '#1890ff' }}
                />
              </Link>
            </Tooltip>
          ) : null}

          {shouldShowViewScenesButton(record) && (
            <Tooltip title="View Impacted Scenes">
              <Link
                to={`/scenes?scene_ids=${getJobSceneIds(record)?.join(',') || ''}`}
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
    () =>
      (Array.isArray(jobs) ? jobs : []).map((job) => ({ ...job, key: job.id })),
    [jobs]
  );

  // Filter jobs by status and type
  const filteredJobs = useMemo(() => {
    let filtered = jobsWithKeys;

    if (statusFilter) {
      filtered = filtered.filter((job) => job.status === statusFilter);
    }

    if (typeFilter) {
      filtered = filtered.filter((job) => job.type === typeFilter);
    }

    return filtered;
  }, [jobsWithKeys, statusFilter, typeFilter]);

  const runningJobs = jobsWithKeys.filter((job) => job.status === 'running');
  const pendingJobs = jobsWithKeys.filter((job) => job.status === 'pending');
  const failedJobs = jobsWithKeys.filter((job) => job.status === 'failed');

  const handleStatusFilterChange = (value: string | undefined) => {
    setStatusFilter(value);
    updateSearchParams({ status: value, type: typeFilter });
  };

  const handleTypeFilterChange = (value: string | undefined) => {
    setTypeFilter(value);
    updateSearchParams({ status: statusFilter, type: value });
  };

  const updateSearchParams = (params: { status?: string; type?: string }) => {
    const newParams: Record<string, string> = {};
    if (params.status) newParams.status = params.status;
    if (params.type) newParams.type = params.type;
    setSearchParams(newParams);
  };

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
          <Space>
            <Select
              placeholder="Filter by status"
              allowClear
              value={statusFilter}
              onChange={handleStatusFilterChange}
              style={{ width: 150 }}
              options={[
                { label: 'All', value: undefined },
                { label: 'Pending', value: 'pending' },
                { label: 'Running', value: 'running' },
                { label: 'Completed', value: 'completed' },
                { label: 'Failed', value: 'failed' },
                { label: 'Cancelled', value: 'cancelled' },
              ]}
            />
            <Select
              placeholder="Filter by type"
              allowClear
              value={typeFilter}
              onChange={handleTypeFilterChange}
              style={{ width: 180 }}
              options={[
                { label: 'All', value: undefined },
                ...Object.entries(JOB_TYPE_LABELS).map(([value, label]) => ({
                  label,
                  value,
                })),
              ]}
            />
            <Button
              icon={<SyncOutlined />}
              onClick={() => void fetchJobs()}
              loading={loading}
            >
              Refresh
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={filteredJobs}
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
        bodyStyle={{
          maxHeight: 'calc(80vh - 108px)',
          overflowY: 'auto',
          overflowX: 'hidden',
          position: 'relative',
        }}
        className={styles.jobDetailModalWrapper}
      >
        {selectedJob && (
          <div className={styles.jobDetailModal}>
            <Collapse defaultActiveKey={['basic', 'result']}>
              <Collapse.Panel header="Basic Information" key="basic">
                <Descriptions bordered column={2} size="small">
                  <Descriptions.Item label="Job ID" span={2}>
                    <Text copyable>{selectedJob.id}</Text>
                  </Descriptions.Item>
                  <Descriptions.Item label="Type">
                    <Tag color={getJobTypeColor(selectedJob.type)}>
                      {getJobTypeLabel(selectedJob.type)}
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
                  <div style={{ marginTop: 16 }}>
                    <Alert
                      message="Last Message"
                      description={selectedJob.metadata.last_message}
                      type="info"
                      showIcon
                    />
                  </div>
                )}

                {selectedJob.error && (
                  <div style={{ marginTop: 16 }}>
                    <Alert
                      message="Job Failed"
                      description={selectedJob.error}
                      type="error"
                      showIcon
                    />
                  </div>
                )}
              </Collapse.Panel>

              {selectedJob.parameters &&
                Object.keys(selectedJob.parameters).length > 0 && (
                  <Collapse.Panel header="Parameters" key="parameters">
                    <pre className={styles.codeBlock}>
                      {JSON.stringify(selectedJob.parameters, null, 2)}
                    </pre>
                  </Collapse.Panel>
                )}

              {selectedJob.result &&
                Object.keys(selectedJob.result).length > 0 && (
                  <Collapse.Panel header="Result" key="result">
                    {selectedJob.type === 'scene_analysis' ||
                    selectedJob.type === 'analysis' ? (
                      <>
                        <AnalysisJobResult
                          result={
                            selectedJob.result as unknown as AnalysisJobResultData
                          }
                        />
                        {((selectedJob.result &&
                          'plan_id' in selectedJob.result &&
                          selectedJob.result.plan_id) ||
                          (selectedJob.metadata &&
                            'plan_id' in selectedJob.metadata &&
                            selectedJob.metadata.plan_id)) && (
                          <div style={{ marginTop: 16 }}>
                            <Link
                              to={`/analysis/plans/${
                                (selectedJob.result &&
                                'plan_id' in selectedJob.result
                                  ? selectedJob.result.plan_id
                                  : selectedJob.metadata?.plan_id) as string
                              }`}
                            >
                              <Button
                                type="primary"
                                icon={<FileTextOutlined />}
                              >
                                View{' '}
                                {selectedJob.status === 'running'
                                  ? 'Current'
                                  : 'Created'}{' '}
                                Analysis Plan
                              </Button>
                            </Link>
                          </div>
                        )}
                      </>
                    ) : (
                      <pre className={styles.codeBlock}>
                        {JSON.stringify(selectedJob.result, null, 2)}
                      </pre>
                    )}
                  </Collapse.Panel>
                )}

              {selectedJob.metadata &&
                Object.keys(selectedJob.metadata).length > 1 && (
                  <Collapse.Panel header="Metadata" key="metadata">
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
                  </Collapse.Panel>
                )}
            </Collapse>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default JobMonitor;
