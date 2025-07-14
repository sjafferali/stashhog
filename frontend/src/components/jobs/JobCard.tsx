import React from 'react';
import { 
  Card, 
  Progress, 
  Tag, 
  Space, 
  Button, 
  Typography,
  Tooltip,
  Descriptions
} from 'antd';
import { 
  ClockCircleOutlined, 
  CheckCircleOutlined, 
  CloseCircleOutlined,
  SyncOutlined,
  PauseCircleOutlined,
  PlayCircleOutlined,
  RedoOutlined,
  DeleteOutlined
} from '@ant-design/icons';
import { Job } from '@/types/models';
import styles from './JobCard.module.scss';

const { Text, Title } = Typography;

export interface JobCardProps {
  job: Job;
  onCancel?: () => void;
  onRetry?: () => void;
  onDelete?: () => void;
  onPause?: () => void;
  onResume?: () => void;
  compact?: boolean;
  showDetails?: boolean;
}

export const JobCard: React.FC<JobCardProps> = ({
  job,
  onCancel,
  onRetry,
  onDelete,
  onPause,
  onResume,
  compact = false,
  showDetails = true,
}) => {
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
      default:
        return null;
    }
  };

  const getStatusColor = () => {
    switch (job.status) {
      case 'pending':
        return 'default';
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

  const getJobTypeLabel = () => {
    switch (job.type) {
      case 'sync':
        return 'Synchronization';
      case 'analysis':
        return 'Scene Analysis';
      case 'batch_analysis':
        return 'Batch Analysis';
      default:
        return job.type;
    }
  };

  const formatDuration = () => {
    if (!job.started_at) return null;
    
    const start = new Date(job.started_at).getTime();
    const end = job.completed_at ? new Date(job.completed_at).getTime() : Date.now();
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

  const progressPercent = job.total > 0 ? (job.progress / job.total) * 100 : 0;

  const actions = [];
  
  if (job.status === 'running') {
    if (onPause) {
      actions.push(
        <Tooltip key="pause" title="Pause">
          <Button type="text" icon={<PauseCircleOutlined />} onClick={onPause} />
        </Tooltip>
      );
    }
    if (onCancel) {
      actions.push(
        <Tooltip key="cancel" title="Cancel">
          <Button type="text" danger icon={<CloseCircleOutlined />} onClick={onCancel} />
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
  
  if ((job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled') && onDelete) {
    actions.push(
      <Tooltip key="delete" title="Delete">
        <Button type="text" danger icon={<DeleteOutlined />} onClick={onDelete} />
      </Tooltip>
    );
  }

  if (compact) {
    return (
      <div className={styles.compactCard}>
        <div className={styles.compactHeader}>
          <Space>
            {getStatusIcon()}
            <Text strong>{job.name}</Text>
            <Tag color={getStatusColor()}>{job.status}</Tag>
          </Space>
          <Space>{actions}</Space>
        </div>
        {job.status === 'running' && (
          <Progress 
            percent={progressPercent} 
            size="small" 
            format={() => `${job.progress}/${job.total}`}
          />
        )}
      </div>
    );
  }

  return (
    <Card
      className={styles.jobCard}
      title={
        <div className={styles.cardHeader}>
          <Space>
            {getStatusIcon()}
            <Title level={5}>{job.name}</Title>
          </Space>
          <Tag color={getStatusColor()}>{job.status.toUpperCase()}</Tag>
        </div>
      }
      extra={<Space>{actions}</Space>}
    >
      <div className={styles.content}>
        <div className={styles.progressSection}>
          <div className={styles.progressInfo}>
            <Text type="secondary">Progress</Text>
            <Text>{job.progress} / {job.total}</Text>
          </div>
          <Progress 
            percent={progressPercent} 
            status={job.status === 'failed' ? 'exception' : job.status === 'running' ? 'active' : undefined}
          />
        </div>

        {showDetails && (
          <Descriptions column={2} size="small" className={styles.details}>
            <Descriptions.Item label="Type">
              <Tag>{getJobTypeLabel()}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Duration">
              {formatDuration() || 'N/A'}
            </Descriptions.Item>
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
        )}

        {job.error && (
          <div className={styles.error}>
            <Text type="danger" strong>Error:</Text>
            <Text type="danger">{job.error}</Text>
          </div>
        )}

        {job.metadata && Object.keys(job.metadata).length > 0 && (
          <div className={styles.metadata}>
            <Text type="secondary">Additional Information:</Text>
            <Descriptions column={1} size="small">
              {Object.entries(job.metadata).map(([key, value]) => (
                <Descriptions.Item key={key} label={key}>
                  {JSON.stringify(value)}
                </Descriptions.Item>
              ))}
            </Descriptions>
          </div>
        )}
      </div>
    </Card>
  );
};