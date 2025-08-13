import React from 'react';
import {
  Card,
  Progress,
  Tag,
  Space,
  Button,
  Typography,
  Tooltip,
  Descriptions,
  Collapse,
} from 'antd';
import {
  ClockCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  PauseCircleOutlined,
  RedoOutlined,
  DeleteOutlined,
  FileTextOutlined,
  VideoCameraOutlined,
  CodeOutlined,
} from '@ant-design/icons';
import { Link } from 'react-router-dom';
import { Job } from '@/types/models';

// Type for process_downloads job result
interface ProcessDownloadsResult {
  total_files_linked?: number;
  total_files_under_duration?: number;
  total_files_skipped?: number;
  synced_items?: number;
}
import {
  getJobTypeLabel,
  getJobTypeColor,
  formatJobProgress,
} from '@/utils/jobUtils';
import { WorkflowJobCard } from './WorkflowJobCard';
import styles from './JobCard.module.scss';

const { Text, Title } = Typography;

export interface JobCardProps {
  job: Job;
  onCancel?: () => void;
  onRetry?: () => void;
  onDelete?: () => void;
  onPause?: () => void;
  onResume?: () => void;
  onViewRawData?: () => void;
  onViewProcessedFiles?: () => void;
  compact?: boolean;
  showDetails?: boolean;
}

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
  if (
    job.result?.scenes_analyzed &&
    typeof job.result.scenes_analyzed === 'number'
  ) {
    // Check if there's a scene_ids in result
    if (job.result?.scene_ids && Array.isArray(job.result.scene_ids)) {
      return job.result.scene_ids as string[];
    }
  }

  return null;
};

export const JobCard: React.FC<JobCardProps> = ({
  job,
  onCancel,
  onRetry,
  onDelete,
  onPause,
  onResume: _onResume,
  onViewRawData,
  onViewProcessedFiles,
  compact = false,
  showDetails = true,
}) => {
  // Use WorkflowJobCard for workflow jobs
  if (job.type === 'process_new_scenes' && !compact) {
    return (
      <WorkflowJobCard
        job={job}
        onCancel={onCancel}
        onRetry={onRetry}
        onDelete={onDelete}
      />
    );
  }

  const getStatusIcon = () => {
    switch (job.status) {
      case 'pending':
        return <ClockCircleOutlined />;
      case 'running':
        return <SyncOutlined spin />;
      case 'completed':
        return <CheckCircleOutlined />;
      case 'failed':
        return <CloseCircleOutlined />;
      case 'cancelled':
        return <CloseCircleOutlined />;
      case 'cancelling':
        return <PauseCircleOutlined />;
      default:
        return null;
    }
  };

  const getStatusColor = () => {
    switch (job.status) {
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
      case 'cancelling':
        return 'orange';
      default:
        return 'default';
    }
  };

  const formatDuration = () => {
    if (!job.started_at) return null;

    const start = new Date(job.started_at).getTime();
    const end = job.completed_at
      ? new Date(job.completed_at).getTime()
      : Date.now();
    const duration = end - start;

    const seconds = Math.floor(duration / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) {
      return `${hours}h ${minutes % 60}m`;
    }
    if (minutes > 0) {
      return `${minutes}m ${seconds % 60}s`;
    }
    return `${seconds}s`;
  };

  const progressPercent = job.progress; // job.progress is already a percentage (0-100)

  const actions = [];

  // Add view raw data button if handler is provided
  if (onViewRawData) {
    actions.push(
      <Tooltip key="raw" title="View Raw Data">
        <Button type="text" icon={<CodeOutlined />} onClick={onViewRawData} />
      </Tooltip>
    );
  }

  // Add view processed files button for process_downloads jobs
  if (
    onViewProcessedFiles &&
    job.type === 'process_downloads' &&
    job.processed_items !== undefined &&
    job.processed_items !== null &&
    job.processed_items > 0
  ) {
    actions.push(
      <Tooltip key="processed-files" title="View Processed Files">
        <Button
          type="text"
          icon={<FileTextOutlined />}
          onClick={onViewProcessedFiles}
          style={{ color: '#722ed1' }}
        />
      </Tooltip>
    );
  }

  if (job.status === 'running' || job.status === 'cancelling') {
    if (onPause && job.status === 'running') {
      actions.push(
        <Tooltip key="pause" title="Pause">
          <Button
            type="text"
            icon={<PauseCircleOutlined />}
            onClick={onPause}
          />
        </Tooltip>
      );
    }
    if (onCancel && job.status === 'running') {
      actions.push(
        <Tooltip key="cancel" title="Cancel">
          <Button
            type="text"
            danger
            icon={<CloseCircleOutlined />}
            onClick={onCancel}
          />
        </Tooltip>
      );
    }
  }

  if (job.status === 'failed' && onRetry) {
    actions.push(
      <Tooltip key="retry" title="Retry">
        <Button type="text" icon={<RedoOutlined />} onClick={onRetry} />
      </Tooltip>
    );
  }

  if (
    (job.status === 'completed' ||
      job.status === 'failed' ||
      job.status === 'cancelled') &&
    onDelete
  ) {
    actions.push(
      <Tooltip key="delete" title="Delete">
        <Button
          type="text"
          danger
          icon={<DeleteOutlined />}
          onClick={onDelete}
        />
      </Tooltip>
    );
  }

  if (compact) {
    return (
      <div className={styles.compactCard} data-status={job.status}>
        <div className={styles.compactHeader}>
          <Space>
            {getStatusIcon()}
            <Text strong>{job.name || getJobTypeLabel(job.type)}</Text>
            <Tag color={getStatusColor()}>{job.status}</Tag>
          </Space>
          <Space>{actions}</Space>
        </div>
        {(job.status === 'running' ||
          job.status === 'cancelling' ||
          job.status === 'cancelled') && (
          <Progress
            percent={progressPercent}
            size="small"
            status={
              job.status === 'cancelling' || job.status === 'cancelled'
                ? 'exception'
                : 'active'
            }
            strokeColor={job.status === 'cancelled' ? '#ff4d4f' : undefined}
            format={() =>
              formatJobProgress(
                job.type,
                job.processed_items,
                job.total,
                job.progress
              )
            }
          />
        )}
      </div>
    );
  }

  return (
    <Card
      className={styles.jobCard}
      data-status={job.status}
      title={
        <div className={styles.cardHeader}>
          <Space>
            {getStatusIcon()}
            <Title level={5}>{job.name || getJobTypeLabel(job.type)}</Title>
          </Space>
          <Tag color={getStatusColor()}>{job.status.toUpperCase()}</Tag>
        </div>
      }
      extra={<Space>{actions}</Space>}
    >
      <div className={styles.content}>
        {/* Basic Info Section - Always Visible */}
        <div className={styles.basicInfo}>
          {/* Job ID Section */}
          <div className={styles.jobIdSection}>
            <Text type="secondary">Job ID: </Text>
            <Text
              copyable
              style={{
                fontFamily: 'monospace',
                fontSize: '12px',
                wordBreak: 'break-all',
              }}
            >
              {job.id}
            </Text>
          </div>

          <div className={styles.progressSection}>
            <div className={styles.progressInfo}>
              <Text type="secondary">Progress</Text>
              <Text>
                {formatJobProgress(
                  job.type,
                  job.processed_items,
                  job.total,
                  job.progress
                )}
              </Text>
            </div>
            <Progress
              percent={progressPercent}
              status={
                job.status === 'failed'
                  ? 'exception'
                  : job.status === 'cancelling' || job.status === 'cancelled'
                    ? 'exception'
                    : job.status === 'running'
                      ? 'active'
                      : undefined
              }
              strokeColor={job.status === 'cancelled' ? '#ff4d4f' : undefined}
            />
          </div>

          <div className={styles.quickInfo}>
            <Space size="middle" wrap>
              <Tooltip title="Job Type">
                <Tag color={getJobTypeColor(job.type)}>
                  {getJobTypeLabel(job.type)}
                </Tag>
              </Tooltip>
              <Tooltip title="Duration">
                <Text type="secondary">
                  <ClockCircleOutlined /> {formatDuration() || 'Just started'}
                </Text>
              </Tooltip>
              <Tooltip title="Created">
                <Text type="secondary">
                  {new Date(job.created_at).toLocaleTimeString()}
                </Text>
              </Tooltip>
            </Space>
          </div>
        </div>

        {/* Error Section */}
        {job.error && (
          <div className={styles.error}>
            <Text type="danger" strong>
              Error:
            </Text>
            <Text type="danger">{job.error}</Text>
          </div>
        )}

        {/* Process Downloads Result Summary */}
        {job.type === 'process_downloads' &&
          job.result &&
          job.status === 'completed' && (
            <div className={styles.resultSummary} style={{ marginTop: 16 }}>
              <Space size="small" wrap>
                <Tag color="green">
                  Files Linked:{' '}
                  {(job.result as ProcessDownloadsResult).total_files_linked ||
                    0}
                </Tag>
                <Tag color="orange">
                  Files Under 30s:{' '}
                  {(job.result as ProcessDownloadsResult)
                    .total_files_under_duration || 0}
                </Tag>
                <Tag color="gray">
                  Files Skipped:{' '}
                  {(job.result as ProcessDownloadsResult).total_files_skipped ||
                    0}
                </Tag>
                {(() => {
                  const syncedItems = (job.result as ProcessDownloadsResult)
                    .synced_items;
                  return syncedItems && syncedItems > 0 ? (
                    <Tag color="blue">Torrents Synced: {syncedItems}</Tag>
                  ) : null;
                })()}
              </Space>
            </div>
          )}

        {/* Expandable Details Section */}
        {showDetails && (
          <div className={styles.detailsCollapse}>
            <Collapse ghost>
              <Collapse.Panel header="View Details" key="1">
                <Descriptions
                  column={2}
                  size="small"
                  className={styles.details}
                >
                  <Descriptions.Item label="Created">
                    {new Date(job.created_at).toLocaleString()}
                  </Descriptions.Item>
                  {job.started_at && (
                    <Descriptions.Item label="Started">
                      {new Date(job.started_at).toLocaleString()}
                    </Descriptions.Item>
                  )}
                  {job.completed_at && (
                    <Descriptions.Item label="Completed" span={2}>
                      {new Date(job.completed_at).toLocaleString()}
                    </Descriptions.Item>
                  )}
                </Descriptions>

                {/* Metadata */}
                {job.metadata && Object.keys(job.metadata).length > 0 && (
                  <>
                    <Text
                      type="secondary"
                      style={{
                        display: 'block',
                        marginTop: 16,
                        marginBottom: 8,
                      }}
                    >
                      Additional Information
                    </Text>
                    <Descriptions column={1} size="small">
                      {Object.entries(job.metadata).map(([key, value]) => {
                        // Special handling for scene_ids
                        if (key === 'scene_ids' && Array.isArray(value)) {
                          return (
                            <Descriptions.Item key={key} label="Scene IDs">
                              <div className={styles.sceneIdsContainer}>
                                {value.length > 10 ? (
                                  <>
                                    <div className={styles.sceneIdsList}>
                                      {(value as string[])
                                        .slice(0, 10)
                                        .map((id: string, idx: number) => (
                                          <Tag key={idx}>{id}</Tag>
                                        ))}
                                    </div>
                                    <Text
                                      type="secondary"
                                      style={{ fontSize: '12px' }}
                                    >
                                      and {value.length - 10} more...
                                    </Text>
                                  </>
                                ) : (
                                  <div className={styles.sceneIdsList}>
                                    {(value as string[]).map(
                                      (id: string, idx: number) => (
                                        <Tag key={idx}>{id}</Tag>
                                      )
                                    )}
                                  </div>
                                )}
                              </div>
                            </Descriptions.Item>
                          );
                        }

                        // Default rendering for other metadata
                        return (
                          <Descriptions.Item key={key} label={key}>
                            {typeof value === 'string' ? (
                              value
                            ) : typeof value === 'object' && value !== null ? (
                              <pre style={{ margin: 0, fontSize: '12px' }}>
                                {JSON.stringify(value, null, 2)}
                              </pre>
                            ) : (
                              String(value)
                            )}
                          </Descriptions.Item>
                        );
                      })}
                    </Descriptions>
                  </>
                )}

                {/* Parameters */}
                {job.parameters && Object.keys(job.parameters).length > 0 && (
                  <>
                    <Text
                      type="secondary"
                      style={{
                        display: 'block',
                        marginTop: 16,
                        marginBottom: 8,
                      }}
                    >
                      Parameters
                    </Text>
                    <Descriptions column={1} size="small">
                      {Object.entries(job.parameters).map(([key, value]) => {
                        // Special handling for scene_ids
                        if (key === 'scene_ids' && Array.isArray(value)) {
                          return (
                            <Descriptions.Item key={key} label="Scene IDs">
                              <div className={styles.sceneIdsContainer}>
                                {value.length > 10 ? (
                                  <>
                                    <div className={styles.sceneIdsList}>
                                      {(value as string[])
                                        .slice(0, 10)
                                        .map((id: string, idx: number) => (
                                          <Tag key={idx}>{id}</Tag>
                                        ))}
                                    </div>
                                    <Text
                                      type="secondary"
                                      style={{ fontSize: '12px' }}
                                    >
                                      and {value.length - 10} more...
                                    </Text>
                                  </>
                                ) : (
                                  <div className={styles.sceneIdsList}>
                                    {(value as string[]).map(
                                      (id: string, idx: number) => (
                                        <Tag key={idx}>{id}</Tag>
                                      )
                                    )}
                                  </div>
                                )}
                              </div>
                            </Descriptions.Item>
                          );
                        }

                        // Default rendering for other parameters
                        return (
                          <Descriptions.Item key={key} label={key}>
                            {typeof value === 'string' ? (
                              value
                            ) : typeof value === 'object' && value !== null ? (
                              <pre style={{ margin: 0, fontSize: '12px' }}>
                                {JSON.stringify(value, null, 2)}
                              </pre>
                            ) : (
                              String(value)
                            )}
                          </Descriptions.Item>
                        );
                      })}
                    </Descriptions>
                  </>
                )}
              </Collapse.Panel>
            </Collapse>
          </div>
        )}

        {/* Action Buttons */}
        {(job.result &&
          (job.type === 'scene_analysis' ||
            job.type === 'analysis' ||
            job.type === 'non_ai_analysis') &&
          'plan_id' in job.result &&
          job.result.plan_id) ||
        (job.metadata &&
          (job.type === 'scene_analysis' ||
            job.type === 'analysis' ||
            job.type === 'non_ai_analysis') &&
          'plan_id' in job.metadata &&
          job.metadata.plan_id) ||
        (job.parameters &&
          (job.type === 'scene_analysis' ||
            job.type === 'analysis' ||
            job.type === 'non_ai_analysis') &&
          'plan_id' in job.parameters &&
          job.parameters.plan_id) ? (
          <div className={styles.planLink}>
            <Link
              to={`/analysis/plans/${
                (job.result?.plan_id ||
                  job.metadata?.plan_id ||
                  job.parameters?.plan_id) as string
              }`}
            >
              <Button type="primary" icon={<FileTextOutlined />}>
                View Created Analysis Plan
              </Button>
            </Link>
          </div>
        ) : null}

        {(() => {
          const sceneIds = getJobSceneIds(job);
          if (sceneIds && sceneIds.length > 0) {
            return (
              <div className={styles.scenesLink}>
                <Link to={`/scenes?scene_ids=${sceneIds.join(',')}`}>
                  <Button type="default" icon={<VideoCameraOutlined />}>
                    View {sceneIds.length} Scene
                    {sceneIds.length !== 1 ? 's' : ''}
                  </Button>
                </Link>
              </div>
            );
          }
          return null;
        })()}
      </div>
    </Card>
  );
};
