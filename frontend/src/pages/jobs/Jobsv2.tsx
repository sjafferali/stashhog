import React, { useState, useEffect, useMemo } from 'react';
import {
  Card,
  Table,
  Tag,
  Progress,
  Button,
  Space,
  Tooltip,
  Typography,
  Badge,
  message,
  Empty,
  Segmented,
  Modal,
  Descriptions,
} from 'antd';
import { Link } from 'react-router-dom';
import type { ColumnsType } from 'antd/es/table';
import {
  SyncOutlined,
  CloseCircleOutlined,
  RedoOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ClockCircleOutlined,
  LoadingOutlined,
  TableOutlined,
  AppstoreOutlined,
  VideoCameraOutlined,
  FileTextOutlined,
  CodeOutlined,
} from '@ant-design/icons';
import { apiClient } from '@/services/apiClient';
import { Job } from '@/types/models';
import { HandledDownloadsModal } from '@/components/jobs/HandledDownloadsModal';
import { useWebSocket } from '@/hooks/useWebSocket';
import { getJobTypeLabel, formatJobProgress } from '@/utils/jobUtils';
import styles from './Jobsv2.module.scss';

const { Text, Title } = Typography;

interface JobWithRelationship extends Job {
  key: string;
  isSubJob?: boolean;
  parentJobId?: string;
  parentJobName?: string;
  subJobs?: JobWithRelationship[];
  children?: JobWithRelationship[]; // For table tree structure
}

const Jobsv2: React.FC = () => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(false);
  const [viewMode, setViewMode] = useState<'card' | 'table'>('card');
  const [expandedRowKeys, setExpandedRowKeys] = useState<string[]>([]);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [rawDataModalVisible, setRawDataModalVisible] = useState(false);
  const [handledDownloadsModalVisible, setHandledDownloadsModalVisible] =
    useState(false);
  const [selectedHandledDownloadsJobId, setSelectedHandledDownloadsJobId] =
    useState<string | null>(null);
  const { lastMessage } = useWebSocket('/api/jobs/ws');

  const fetchJobs = async () => {
    try {
      const response = await apiClient.getJobs({ limit: 100 });
      setJobs(response.jobs);
    } catch (error) {
      console.error('Failed to fetch jobs:', error);
      void message.error('Failed to fetch jobs');
      setJobs([]);
    }
  };

  useEffect(() => {
    setLoading(true);
    void fetchJobs().finally(() => setLoading(false));

    const interval = setInterval(() => {
      void fetchJobs();
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  // Handle WebSocket updates
  useEffect(() => {
    if (lastMessage && typeof lastMessage === 'object') {
      const update = lastMessage as { type: string; job: Job };

      if (update.type === 'job_update' && update.job) {
        setJobs((prevJobs) => {
          const jobIndex = prevJobs.findIndex((j) => j.id === update.job.id);

          if (jobIndex >= 0) {
            const newJobs = [...prevJobs];
            newJobs[jobIndex] = update.job;
            return newJobs;
          } else {
            return [update.job, ...prevJobs];
          }
        });
      }
    }
  }, [lastMessage]);

  // Process jobs to establish relationships
  const processedJobs = useMemo(() => {
    const jobsWithRelationships: JobWithRelationship[] = jobs.map((job) => ({
      ...job,
      key: job.id,
      isSubJob: !!job.metadata?.parent_job_id,
      parentJobId: job.metadata?.parent_job_id as string | undefined,
    }));

    // Create a map for quick lookup
    const jobMap = new Map<string, JobWithRelationship>();
    jobsWithRelationships.forEach((job) => {
      jobMap.set(job.id, job);
    });

    // Establish parent-child relationships
    const rootJobs: JobWithRelationship[] = [];
    jobsWithRelationships.forEach((job) => {
      if (job.parentJobId) {
        const parentJob = jobMap.get(job.parentJobId);
        if (parentJob) {
          if (!parentJob.subJobs) {
            parentJob.subJobs = [];
          }
          if (!parentJob.children) {
            parentJob.children = [];
          }
          job.parentJobName = parentJob.name || getJobTypeLabel(parentJob.type);
          parentJob.subJobs.push(job);
          parentJob.children.push(job);
        } else {
          // Parent job not found, treat as root job
          rootJobs.push(job);
        }
      } else {
        rootJobs.push(job);
      }
    });

    // Sort sub-jobs by created_at to maintain execution order
    jobsWithRelationships.forEach((job) => {
      if (job.subJobs && job.subJobs.length > 0) {
        job.subJobs.sort(
          (a, b) =>
            new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
        );
      }
      if (job.children && job.children.length > 0) {
        job.children.sort(
          (a, b) =>
            new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
        );
      }
    });

    // Sort root jobs by created_at desc
    rootJobs.sort(
      (a, b) =>
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );

    return rootJobs;
  }, [jobs]);

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

  const showRawJobData = (job: Job) => {
    setSelectedJob(job);
    setRawDataModalVisible(true);
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
        return null;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'orange';
      case 'running':
        return 'processing';
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

  const formatDuration = (start?: string, end?: string) => {
    if (!start) return '-';
    const startTime = new Date(start).getTime();
    const endTime = end ? new Date(end).getTime() : Date.now();
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

  const getJobTypeIndicator = (job: JobWithRelationship) => {
    if (job.type === 'process_new_scenes') {
      return <Tag color="purple">WORKFLOW</Tag>;
    } else if (job.isSubJob) {
      return <Tag color="cyan">SUB-JOB</Tag>;
    } else {
      return <Tag color="green">STANDALONE</Tag>;
    }
  };

  const renderJobCard = (
    job: JobWithRelationship,
    isSubJob = false,
    isFirstSubJob = false,
    isLastSubJob = false,
    subJobIndex = 0
  ) => {
    const isWorkflow = job.type === 'process_new_scenes';

    return (
      <div key={job.id} className={styles.jobCardWrapper}>
        {isSubJob && (
          <div
            className={`${styles.subjobConnector} ${
              isFirstSubJob ? styles.firstSubjob : ''
            } ${isLastSubJob ? styles.lastSubjob : ''}`}
          >
            <div className={styles.connectorLine}>
              <div className={styles.stepNumber}>{subJobIndex}</div>
            </div>
          </div>
        )}
        <Card
          className={`${styles.jobCard} ${isWorkflow ? styles.workflowJob : ''} ${
            isSubJob ? styles.subjob : ''
          }`}
          title={
            <div className={styles.cardHeader}>
              <Space>
                {getStatusIcon(job.status)}
                <Text strong>{job.name || getJobTypeLabel(job.type)}</Text>
                {getJobTypeIndicator(job)}
              </Space>
              <Tag color={getStatusColor(job.status)}>
                {job.status.toUpperCase()}
              </Tag>
            </div>
          }
          extra={
            <Space>
              <Tooltip title="View Raw Data">
                <Button
                  type="text"
                  icon={<CodeOutlined />}
                  size="small"
                  onClick={() => showRawJobData(job)}
                />
              </Tooltip>
              {job.status === 'running' && (
                <Button
                  type="text"
                  danger
                  icon={<CloseCircleOutlined />}
                  size="small"
                  onClick={() => void handleCancel(job.id)}
                />
              )}
              {job.status === 'failed' && (
                <Button
                  type="text"
                  icon={<RedoOutlined />}
                  size="small"
                  onClick={() => void handleRetry(job.id)}
                />
              )}
            </Space>
          }
        >
          {isSubJob && job.parentJobName && (
            <div className={styles.subjobIndicator}>
              <Text type="secondary">
                SUB-JOB OF: {job.parentJobName}
                {job.metadata?.workflow_step_number && (
                  <span>
                    {' '}
                    • Step {job.metadata.workflow_step_number as number}
                  </span>
                )}
              </Text>
            </div>
          )}

          {isWorkflow &&
            job.metadata?.current_step &&
            job.metadata?.total_steps && (
              <div className={styles.workflowStep}>
                <div className={styles.workflowStepHeader}>
                  <Text strong>
                    Workflow Step {job.metadata.current_step as number} of{' '}
                    {job.metadata.total_steps as number}
                  </Text>
                </div>
                <Text>{job.metadata.step_name as string}</Text>
                <div className={styles.workflowProgress}>
                  {Array.from({
                    length: job.metadata.total_steps as number,
                  }).map((_, index) => (
                    <div
                      key={index}
                      className={`${styles.workflowProgressStep} ${
                        index < (job.metadata?.current_step as number)
                          ? styles.completed
                          : index === (job.metadata?.current_step as number) - 1
                            ? styles.active
                            : ''
                      }`}
                    />
                  ))}
                </div>
              </div>
            )}

          <div className={styles.progressSection}>
            <Progress
              percent={job.progress}
              status={
                job.status === 'failed'
                  ? 'exception'
                  : job.status === 'completed'
                    ? 'success'
                    : 'active'
              }
            />
            <Text type="secondary">
              {formatJobProgress(
                job.type,
                job.processed_items,
                job.total,
                job.progress
              )}
            </Text>
          </div>

          <div className={styles.jobMeta}>
            <Space size="middle">
              <Text type="secondary">
                <ClockCircleOutlined />{' '}
                {formatDuration(job.started_at, job.completed_at)}
              </Text>
              <Text type="secondary">
                Created: {new Date(job.created_at).toLocaleTimeString()}
              </Text>
            </Space>
          </div>

          <div className={styles.jobId}>
            <Text copyable type="secondary" style={{ fontSize: '11px' }}>
              Job ID: {job.id}
            </Text>
          </div>

          {job.error && (
            <div className={styles.error}>
              <Text type="danger">{job.error}</Text>
            </div>
          )}

          {/* Action buttons */}
          <Space className={styles.actionButtons} wrap>
            {/* Analysis Plan Link */}
            {(job.type === 'scene_analysis' || job.type === 'analysis') &&
            ((job.status === 'completed' &&
              job.result &&
              'plan_id' in job.result &&
              job.result.plan_id) ||
              (job.status === 'running' &&
                job.metadata &&
                'plan_id' in job.metadata &&
                job.metadata.plan_id)) ? (
              <Link
                to={`/analysis/plans/${
                  (job.result && 'plan_id' in job.result
                    ? job.result.plan_id
                    : job.metadata?.plan_id) as string
                }`}
              >
                <Button icon={<FileTextOutlined />} size="small">
                  View Analysis Plan
                </Button>
              </Link>
            ) : null}

            {/* View Scenes Link */}
            {shouldShowViewScenesButton(job) && getJobSceneIds(job) ? (
              <Link
                to={`/scenes?scene_ids=${getJobSceneIds(job)?.join(',') || ''}`}
              >
                <Button icon={<VideoCameraOutlined />} size="small">
                  View {getJobSceneIds(job)?.length || 0} Scenes
                </Button>
              </Link>
            ) : null}

            {/* View Processed Files for process_downloads jobs */}
            {job.type === 'process_downloads' &&
            job.processed_items !== undefined &&
            job.processed_items !== null &&
            job.processed_items > 0 ? (
              <Button
                icon={<FileTextOutlined />}
                size="small"
                style={{ color: '#722ed1' }}
                onClick={() => {
                  setSelectedHandledDownloadsJobId(job.id);
                  setHandledDownloadsModalVisible(true);
                }}
              >
                View {job.processed_items} Files
              </Button>
            ) : null}
          </Space>
        </Card>

        {/* Render sub-jobs */}
        {job.subJobs && job.subJobs.length > 0 && (
          <div className={styles.subjobsContainer}>
            {job.subJobs.map((subJob, index) =>
              renderJobCard(
                subJob,
                true,
                index === 0,
                index === (job.subJobs?.length ?? 0) - 1,
                index + 1
              )
            )}
          </div>
        )}
      </div>
    );
  };

  // Helper function to get job scene IDs (similar to JobMonitor)
  const getJobSceneIds = (job: Job): string[] | null => {
    // Check metadata.scene_ids (for sync jobs)
    if (job.metadata?.scene_ids && Array.isArray(job.metadata.scene_ids)) {
      return job.metadata.scene_ids as string[];
    }

    // Check parameters.scene_ids (for some sync jobs)
    if (job.parameters?.scene_ids && Array.isArray(job.parameters.scene_ids)) {
      return job.parameters.scene_ids as string[];
    }

    // For analysis jobs, check if we have analyzed_scene_ids in result
    if (
      job.result?.analyzed_scene_ids &&
      Array.isArray(job.result.analyzed_scene_ids)
    ) {
      return job.result.analyzed_scene_ids as string[];
    }

    // For analysis jobs with scenes_analyzed count but no explicit IDs
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

  // Table columns
  const columns: ColumnsType<JobWithRelationship> = [
    {
      title: 'Job Name',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: JobWithRelationship) => (
        <Space>
          <Text strong>{name || getJobTypeLabel(record.type)}</Text>
        </Space>
      ),
    },
    {
      title: 'Type',
      key: 'type',
      width: 140,
      render: (_: unknown, record: JobWithRelationship) =>
        getJobTypeIndicator(record),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => (
        <Space>
          {getStatusIcon(status)}
          <Tag color={getStatusColor(status)}>{status.toUpperCase()}</Tag>
        </Space>
      ),
    },
    {
      title: 'Progress',
      key: 'progress',
      width: 200,
      render: (_: unknown, record: Job) => (
        <div>
          <Progress
            percent={record.progress}
            size="small"
            status={
              record.status === 'failed'
                ? 'exception'
                : record.status === 'completed'
                  ? 'success'
                  : 'active'
            }
          />
          <Text type="secondary" style={{ fontSize: 12 }}>
            {formatJobProgress(
              record.type,
              record.processed_items,
              record.total,
              record.progress
            )}
          </Text>
        </div>
      ),
    },
    {
      title: 'Duration',
      key: 'duration',
      width: 100,
      render: (_: unknown, record: Job) => (
        <Text type="secondary">
          {formatDuration(record.started_at, record.completed_at)}
        </Text>
      ),
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 150,
      render: (date: string) => (
        <Tooltip title={new Date(date).toLocaleString()}>
          <Text>{new Date(date).toLocaleTimeString()}</Text>
        </Tooltip>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 250,
      render: (_: unknown, record: Job) => (
        <Space>
          {/* View Raw Data */}
          <Tooltip title="View Raw Data">
            <Button
              type="text"
              icon={<CodeOutlined />}
              size="small"
              onClick={() => showRawJobData(record)}
            />
          </Tooltip>

          {/* Analysis Plan Icon Link */}
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

          {/* View Scenes Icon Link */}
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

          {/* View Processed Files for process_downloads jobs */}
          {record.type === 'process_downloads' &&
            record.processed_items !== undefined &&
            record.processed_items !== null &&
            record.processed_items > 0 && (
              <Tooltip title="View Processed Files">
                <Button
                  type="text"
                  icon={<FileTextOutlined />}
                  size="small"
                  style={{ color: '#722ed1' }}
                  onClick={() => {
                    setSelectedHandledDownloadsJobId(record.id);
                    setHandledDownloadsModalVisible(true);
                  }}
                />
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

  return (
    <div className={styles.jobsv2}>
      <div className={styles.header}>
        <Title level={2}>Jobs v2</Title>
        <Space>
          <Badge
            count={jobs.filter((j) => j.status === 'running').length}
            showZero
            color="blue"
          >
            <Tag color="blue">Running</Tag>
          </Badge>
          <Badge
            count={jobs.filter((j) => j.status === 'pending').length}
            showZero
            color="orange"
          >
            <Tag color="orange">Pending</Tag>
          </Badge>
          <Badge
            count={jobs.filter((j) => j.status === 'failed').length}
            showZero
            color="red"
          >
            <Tag color="red">Failed</Tag>
          </Badge>
        </Space>
      </div>

      <Card
        extra={
          <Space>
            <Segmented
              value={viewMode}
              options={[
                {
                  label: 'Hierarchical Cards',
                  value: 'card',
                  icon: <AppstoreOutlined />,
                },
                {
                  label: 'Hierarchical Table',
                  value: 'table',
                  icon: <TableOutlined />,
                },
              ]}
              onChange={(value: string) =>
                setViewMode(value as 'card' | 'table')
              }
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
        {viewMode === 'card' ? (
          <div className={styles.cardView}>
            {loading ? (
              <div style={{ textAlign: 'center', padding: '40px' }}>
                <LoadingOutlined style={{ fontSize: 24 }} />
              </div>
            ) : processedJobs.length === 0 ? (
              <Empty description="No jobs found" />
            ) : (
              processedJobs.map((job) => renderJobCard(job))
            )}
          </div>
        ) : (
          <Table
            columns={columns}
            dataSource={processedJobs}
            loading={loading}
            rowKey="key"
            pagination={{
              pageSize: 20,
              showSizeChanger: true,
              showTotal: (total) => `Total ${total} jobs`,
            }}
            expandable={{
              expandedRowKeys,
              onExpandedRowsChange: setExpandedRowKeys,
              rowExpandable: (record) =>
                !!(record.children && record.children.length > 0),
            }}
            rowClassName={(record) => {
              if (record.type === 'process_new_scenes')
                return styles.tableWorkflowRow;
              if (record.isSubJob) return styles.tableSubjobRow;
              return '';
            }}
          />
        )}
      </Card>

      {/* Raw Job Data Modal */}
      <Modal
        title={
          <Space>
            <CodeOutlined />
            Raw Job Data
          </Space>
        }
        open={rawDataModalVisible}
        onCancel={() => {
          setRawDataModalVisible(false);
          setSelectedJob(null);
        }}
        footer={[
          <Button
            key="close"
            onClick={() => {
              setRawDataModalVisible(false);
              setSelectedJob(null);
            }}
          >
            Close
          </Button>,
        ]}
        width={800}
        bodyStyle={{
          maxHeight: 'calc(80vh - 108px)',
          overflowY: 'auto',
        }}
      >
        {selectedJob && (
          <div>
            <Descriptions bordered column={1} size="small">
              <Descriptions.Item label="Job ID">
                <Text copyable>{selectedJob.id}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="Name">
                {selectedJob.name || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="Type">
                <Tag>{getJobTypeLabel(selectedJob.type)}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Status">
                <Tag color={getStatusColor(selectedJob.status)}>
                  {selectedJob.status.toUpperCase()}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Progress">
                {selectedJob.progress}%
              </Descriptions.Item>
              <Descriptions.Item label="Created At">
                {new Date(selectedJob.created_at).toLocaleString()}
              </Descriptions.Item>
              {selectedJob.started_at && (
                <Descriptions.Item label="Started At">
                  {new Date(selectedJob.started_at).toLocaleString()}
                </Descriptions.Item>
              )}
              {selectedJob.completed_at && (
                <Descriptions.Item label="Completed At">
                  {new Date(selectedJob.completed_at).toLocaleString()}
                </Descriptions.Item>
              )}
            </Descriptions>

            <Title level={5} style={{ marginTop: 16 }}>
              Full JSON Data
            </Title>
            <pre
              style={{
                background: '#f5f5f5',
                padding: '12px',
                borderRadius: '4px',
                overflow: 'auto',
                fontSize: '12px',
                fontFamily: 'monospace',
              }}
            >
              {JSON.stringify(selectedJob, null, 2)}
            </pre>
          </div>
        )}
      </Modal>

      {/* Handled Downloads Modal */}
      {selectedHandledDownloadsJobId && (
        <HandledDownloadsModal
          jobId={selectedHandledDownloadsJobId}
          visible={handledDownloadsModalVisible}
          onClose={() => {
            setHandledDownloadsModalVisible(false);
            setSelectedHandledDownloadsJobId(null);
          }}
        />
      )}
    </div>
  );
};

export default Jobsv2;
