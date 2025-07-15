import React, { useState, useEffect } from 'react';
import {
  Modal,
  Progress,
  Alert,
  List,
  Space,
  Typography,
  Button,
  Divider,
  Tag,
  Result,
  Timeline,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { useWebSocket } from '@/hooks/useWebSocket';

const { Text, Title } = Typography;

export interface ApplyProgress {
  total: number;
  completed: number;
  failed: number;
  inProgress: boolean;
  currentScene?: string;
  errors?: Array<{
    sceneId: string;
    field: string;
    error: string;
  }>;
}

export interface ApplyPlanModalProps {
  visible: boolean;
  planId: number;
  planName: string;
  acceptedChanges: number;
  totalScenes: number;
  onCancel: () => void;
  onApply: () => Promise<{ job_id?: string }>;
  onComplete?: () => void;
}

interface ProgressUpdate {
  type: 'progress' | 'complete' | 'error';
  jobId: string;
  current: number;
  total: number;
  scene?: string;
  error?: string;
}

const ApplyPlanModal: React.FC<ApplyPlanModalProps> = ({
  visible,
  planId: _planId,
  planName,
  acceptedChanges,
  totalScenes,
  onCancel,
  onApply,
  onComplete,
}) => {
  const [stage, setStage] = useState<'confirm' | 'progress' | 'complete'>(
    'confirm'
  );
  const [progress, setProgress] = useState<ApplyProgress>({
    total: acceptedChanges,
    completed: 0,
    failed: 0,
    inProgress: false,
    errors: [],
  });
  const [jobId, setJobId] = useState<string | null>(null);

  // WebSocket for progress updates
  const { message: wsMessage } = useWebSocket(
    jobId ? `/ws/jobs/${jobId}` : null
  );

  useEffect(() => {
    if (wsMessage) {
      const update = wsMessage as ProgressUpdate;

      if (update.type === 'progress') {
        setProgress((prev) => ({
          ...prev,
          completed: update.current,
          currentScene: update.scene,
        }));
      } else if (update.type === 'complete') {
        setProgress((prev) => ({
          ...prev,
          completed: update.total,
          inProgress: false,
        }));
        setStage('complete');
        onComplete?.();
      } else if (update.type === 'error') {
        setProgress((prev) => ({
          ...prev,
          failed: prev.failed + 1,
          errors: [
            ...(prev.errors || []),
            {
              sceneId: update.scene || '',
              field: '',
              error: update.error || 'Unknown error',
            },
          ],
        }));
      }
    }
  }, [wsMessage, onComplete]);

  const handleApply = async () => {
    setStage('progress');
    setProgress((prev) => ({ ...prev, inProgress: true }));

    try {
      const result = await onApply();

      if (result.job_id) {
        setJobId(result.job_id);
      } else {
        // Synchronous completion
        setProgress((prev) => ({
          ...prev,
          completed: prev.total,
          inProgress: false,
        }));
        setStage('complete');
        onComplete?.();
      }
    } catch {
      setProgress((prev) => ({
        ...prev,
        inProgress: false,
        failed: prev.total,
      }));
      Modal.error({
        title: 'Failed to Apply Changes',
        content:
          'An error occurred while applying the changes. Please try again.',
      });
    }
  };

  const handleClose = () => {
    setStage('confirm');
    setProgress({
      total: acceptedChanges,
      completed: 0,
      failed: 0,
      inProgress: false,
      errors: [],
    });
    setJobId(null);
    onCancel();
  };

  const renderConfirmStage = () => (
    <>
      <Alert
        message="Confirm Application"
        description={`You are about to apply ${acceptedChanges} changes to ${totalScenes} scenes. This will update the metadata in your Stash instance.`}
        type="warning"
        showIcon
        style={{ marginBottom: 16 }}
      />

      <Title level={5}>Summary of Changes</Title>
      <List
        size="small"
        dataSource={[
          { label: 'Plan Name', value: planName },
          { label: 'Total Changes', value: acceptedChanges.toString() },
          { label: 'Affected Scenes', value: totalScenes.toString() },
          {
            label: 'Estimated Time',
            value: `${Math.ceil(acceptedChanges * 0.5)} seconds`,
          },
        ]}
        renderItem={(item: { label: string; value: string }) => (
          <List.Item>
            <Text strong>{item.label}:</Text> {item.value}
          </List.Item>
        )}
      />

      <Divider />

      <Alert
        message="Important"
        description="Changes will be applied to your Stash instance and cannot be automatically undone. Make sure you have a backup if needed."
        type="info"
        showIcon
      />
    </>
  );

  const renderProgressStage = () => {
    const percent =
      progress.total > 0 ? (progress.completed / progress.total) * 100 : 0;
    const status =
      progress.failed > 0
        ? 'exception'
        : progress.inProgress
          ? 'active'
          : 'success';

    return (
      <>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <div>
            <Text>Applying changes to Stash...</Text>
            <Progress
              percent={Math.round(percent)}
              status={status}
              strokeColor={{
                '0%': '#108ee9',
                '100%': '#87d068',
              }}
            />
          </div>

          <Space>
            <Tag color="success">
              <CheckCircleOutlined /> Completed: {progress.completed}
            </Tag>
            {progress.failed > 0 && (
              <Tag color="error">
                <CloseCircleOutlined /> Failed: {progress.failed}
              </Tag>
            )}
            <Tag color="processing">
              <ClockCircleOutlined /> Remaining:{' '}
              {progress.total - progress.completed - progress.failed}
            </Tag>
          </Space>

          {progress.currentScene && (
            <Alert
              message="Current Scene"
              description={progress.currentScene}
              type="info"
              icon={<LoadingOutlined />}
            />
          )}

          {progress.errors && progress.errors.length > 0 && (
            <>
              <Divider />
              <Title level={5}>Errors</Title>
              <Timeline>
                {progress.errors.map((error, index) => (
                  <Timeline.Item
                    key={index}
                    color="red"
                    dot={<CloseCircleOutlined />}
                  >
                    <Text type="danger">
                      Scene {error.sceneId}: {error.error}
                    </Text>
                  </Timeline.Item>
                ))}
              </Timeline>
            </>
          )}
        </Space>
      </>
    );
  };

  const renderCompleteStage = () => {
    const success = progress.failed === 0;

    return (
      <Result
        status={success ? 'success' : 'warning'}
        title={
          success
            ? 'Changes Applied Successfully'
            : 'Changes Applied with Errors'
        }
        subTitle={
          success
            ? `All ${progress.completed} changes have been applied successfully.`
            : `${progress.completed} changes applied successfully, ${progress.failed} failed.`
        }
        extra={[
          <Button type="primary" key="close" onClick={handleClose}>
            Close
          </Button>,
        ]}
      />
    );
  };

  return (
    <Modal
      title={
        stage === 'confirm'
          ? 'Apply Changes'
          : stage === 'progress'
            ? 'Applying Changes...'
            : 'Application Complete'
      }
      visible={visible}
      onCancel={stage === 'confirm' ? onCancel : undefined}
      closable={stage !== 'progress'}
      maskClosable={false}
      width={600}
      footer={
        stage === 'confirm'
          ? [
              <Button key="cancel" onClick={onCancel}>
                Cancel
              </Button>,
              <Button
                key="apply"
                type="primary"
                onClick={() => void handleApply()}
              >
                Apply Changes
              </Button>,
            ]
          : stage === 'progress'
            ? [
                <Button key="background" disabled>
                  Running in Background...
                </Button>,
              ]
            : null
      }
    >
      {stage === 'confirm' && renderConfirmStage()}
      {stage === 'progress' && renderProgressStage()}
      {stage === 'complete' && renderCompleteStage()}
    </Modal>
  );
};

export default ApplyPlanModal;
