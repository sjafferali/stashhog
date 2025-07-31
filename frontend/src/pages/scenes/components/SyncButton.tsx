import React, { useState } from 'react';
import {
  Button,
  Dropdown,
  Modal,
  Progress,
  Space,
  Typography,
  message,
} from 'antd';
import {
  SyncOutlined,
  DownOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from 'react-query';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import api from '@/services/api';
import apiClient from '@/services/apiClient';
import { SyncStatus, Job } from '@/types/models';
import type { MenuProps } from 'antd';

dayjs.extend(relativeTime);

const { Text } = Typography;

interface SyncButtonProps {
  onSyncComplete?: () => void;
}

export const SyncButton: React.FC<SyncButtonProps> = ({ onSyncComplete }) => {
  const queryClient = useQueryClient();
  const [syncModalVisible, setSyncModalVisible] = useState(false);
  const [currentJob, setCurrentJob] = useState<Job | null>(null);

  // Fetch sync status
  const { data: syncStatus } = useQuery<SyncStatus>(
    'sync-status',
    () => apiClient.getSyncStatus(),
    {
      refetchInterval: () => {
        // TODO: Implement proper sync status check
        return false;
      },
    }
  );

  // Sync mutation
  const syncMutation = useMutation(
    async (fullSync: boolean) => {
      // Call the sync endpoint with force parameter for full sync
      const response = await api.post('/sync/all', null, {
        params: { force: fullSync },
      });
      return response.data;
    },
    {
      onSuccess: (data) => {
        setCurrentJob(data); // The response is the job itself
        setSyncModalVisible(true);
        void message.success('Sync started');
        void queryClient.invalidateQueries('sync-status');
      },
      onError: (error) => {
        // Don't show a duplicate error message here since the API interceptor
        // already handles error notifications globally
        console.error('Sync mutation error:', error);
      },
    }
  );

  // Poll job status
  useQuery(
    ['job', currentJob?.id],
    async () => {
      if (!currentJob?.id) return null;
      const response = await api.get(`/jobs/${currentJob.id}`);
      return response.data;
    },
    {
      enabled:
        !!currentJob?.id &&
        currentJob.status !== 'completed' &&
        currentJob.status !== 'failed',
      refetchInterval: 1000,
      onSuccess: (data: Job) => {
        if (data) {
          setCurrentJob(data);
          if (data.status === 'completed') {
            void message.success('Sync completed successfully');
            setSyncModalVisible(false);
            void queryClient.invalidateQueries(['scenes']);
            void queryClient.invalidateQueries(['sync-status']);
            onSyncComplete?.();
          } else if (data.status === 'failed') {
            // Only show error if there's actually an error message
            // to avoid duplicate notifications from WebSocket
            if (data.error) {
              void message.error('Sync failed: ' + data.error);
            }
            setSyncModalVisible(false);
          }
        }
      },
    }
  );

  const handleFullSync = () => {
    Modal.confirm({
      title: 'Full Sync',
      content:
        'This will sync all data from Stash. This may take a while. Continue?',
      onOk: () => syncMutation.mutate(true),
    });
  };

  const handleIncrementalSync = () => {
    syncMutation.mutate(false);
  };

  const syncMenuItems: MenuProps['items'] = [
    {
      key: 'incremental',
      label: 'Quick Sync',
      icon: <SyncOutlined />,
      onClick: handleIncrementalSync,
    },
    {
      key: 'full',
      label: 'Full Sync',
      icon: <SyncOutlined />,
      onClick: handleFullSync,
    },
    {
      type: 'divider',
    },
    {
      key: 'last-sync',
      label: syncStatus?.sync.last_scene_sync ? (
        <Space>
          <ClockCircleOutlined />
          <Text type="secondary">
            Last sync: {dayjs(syncStatus.sync.last_scene_sync).fromNow()}
          </Text>
        </Space>
      ) : (
        <Text type="secondary">Never synced</Text>
      ),
      disabled: true,
    },
  ];

  const isLoading = syncMutation.isLoading;

  return (
    <>
      <Dropdown menu={{ items: syncMenuItems }} placement="bottomRight">
        <Button
          icon={<SyncOutlined spin={isLoading} />}
          loading={isLoading}
          disabled={false}
        >
          <Space>
            Sync
            <DownOutlined />
          </Space>
        </Button>
      </Dropdown>

      <Modal
        title="Sync Progress"
        open={syncModalVisible}
        onCancel={() => setSyncModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setSyncModalVisible(false)}>
            Close
          </Button>,
        ]}
        width={600}
      >
        {currentJob && (
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <div>
              <Text strong>Status: </Text>
              <Text>{currentJob.status}</Text>
            </div>

            {currentJob.total && currentJob.total > 0 && (
              <>
                <Progress
                  percent={Math.round(
                    currentJob.total
                      ? (currentJob.progress / currentJob.total) * 100
                      : currentJob.progress
                  )}
                  status={
                    currentJob.status === 'failed'
                      ? 'exception'
                      : currentJob.status === 'completed'
                        ? 'success'
                        : 'active'
                  }
                />
                <div>
                  <Text>
                    {currentJob.total
                      ? `${currentJob.progress} / ${currentJob.total} items processed`
                      : `${Math.round(currentJob.progress)}% complete`}
                  </Text>
                </div>
              </>
            )}

            {currentJob.metadata && (
              <div>
                <Text strong>Details:</Text>
                <pre
                  style={{
                    background: '#f5f5f5',
                    padding: '8px',
                    borderRadius: '4px',
                    fontSize: '12px',
                  }}
                >
                  {JSON.stringify(currentJob.metadata, null, 2)}
                </pre>
              </div>
            )}

            {currentJob.error && (
              <div>
                <Text type="danger" strong>
                  Error:{' '}
                </Text>
                <Text type="danger">{currentJob.error}</Text>
              </div>
            )}
          </Space>
        )}
      </Modal>
    </>
  );
};
