import React, { useEffect, useState } from 'react';
import {
  Card,
  Button,
  Space,
  Statistic,
  Row,
  Col,
  Alert,
  Timeline,
  Spin,
} from 'antd';
import {
  SyncOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
} from '@ant-design/icons';
import apiClient from '@/services/apiClient';
import api from '@/services/api';
import { SyncStatus } from '@/types/models';

interface SyncHistoryItem {
  id: string;
  entity_type: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  total_items: number;
  processed_items: number;
  created_items: number;
  updated_items: number;
  skipped_items: number;
  failed_items: number;
  error: string | null;
}

const SyncManagement: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<SyncStatus | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncHistory, setSyncHistory] = useState<SyncHistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const fetchStats = async () => {
    try {
      setLoading(true);
      const data = await apiClient.getSyncStatus();
      setStats(data);
    } catch (error) {
      console.error('Failed to fetch sync stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchSyncHistory = async () => {
    try {
      setHistoryLoading(true);
      const response = await api.get('/sync/history', {
        params: { limit: 10 },
      });
      setSyncHistory(response.data);
    } catch (error) {
      console.error('Failed to fetch sync history:', error);
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    void fetchStats();
    void fetchSyncHistory();
  }, []);

  // Auto-refresh when syncing
  useEffect(() => {
    if (stats?.is_syncing) {
      const interval = setInterval(() => {
        void fetchStats();
        void fetchSyncHistory();
      }, 5000); // Refresh every 5 seconds
      return () => clearInterval(interval);
    }
  }, [stats?.is_syncing]);

  const handleStartSync = async () => {
    try {
      setSyncing(true);
      await apiClient.startSync();
      await fetchStats();
    } catch (error) {
      console.error('Failed to start sync:', error);
    } finally {
      setSyncing(false);
    }
  };

  const handleStopSync = async () => {
    try {
      await apiClient.stopSync();
      await fetchStats();
    } catch (error) {
      console.error('Failed to stop sync:', error);
    }
  };

  const isSyncing = stats?.is_syncing || false;

  return (
    <div>
      <h1>Sync Management</h1>

      <Alert
        message="Sync Status"
        description={
          isSyncing ? 'Sync is currently running...' : 'Sync is idle'
        }
        type={isSyncing ? 'info' : 'success'}
        showIcon
        style={{ marginBottom: 24 }}
      />

      <Spin spinning={loading}>
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic title="Total Scenes" value={stats?.scene_count || 0} />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="Total Performers"
                value={stats?.performer_count || 0}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic title="Total Tags" value={stats?.tag_count || 0} />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="Total Studios"
                value={stats?.studio_count || 0}
              />
            </Card>
          </Col>
        </Row>
      </Spin>

      <Card
        title="Sync Controls"
        extra={
          <Space>
            <Button
              type="primary"
              icon={
                isSyncing ? <PauseCircleOutlined /> : <PlayCircleOutlined />
              }
              loading={syncing}
              onClick={() =>
                void (isSyncing ? handleStopSync() : handleStartSync())
              }
            >
              {isSyncing ? 'Stop Sync' : 'Start Sync'}
            </Button>
            <Button icon={<SyncOutlined />} onClick={() => void fetchStats()}>
              Refresh
            </Button>
          </Space>
        }
      >
        <p>
          Last scene sync:{' '}
          {stats?.last_scene_sync
            ? new Date(stats.last_scene_sync).toLocaleString()
            : 'Never'}
        </p>
        <p>Pending scenes: {stats?.pending_scenes || 0}</p>
      </Card>

      <Card
        title="Recent Sync History"
        style={{ marginTop: 16 }}
        loading={historyLoading}
      >
        {syncHistory.length > 0 ? (
          <Timeline
            items={syncHistory.map((item) => {
              const getColor = () => {
                if (item.status === 'completed') return 'green';
                if (item.status === 'failed') return 'red';
                if (item.status === 'running') return 'blue';
                return 'gray';
              };

              const getDescription = () => {
                const parts = [];
                parts.push(`${item.entity_type} sync`);
                if (item.status === 'completed') {
                  parts.push(
                    `Processed: ${item.processed_items}/${item.total_items}`
                  );
                  if (item.created_items > 0) {
                    parts.push(`Created: ${item.created_items}`);
                  }
                  if (item.updated_items > 0) {
                    parts.push(`Updated: ${item.updated_items}`);
                  }
                  if (item.failed_items > 0) {
                    parts.push(`Failed: ${item.failed_items}`);
                  }
                }
                if (item.error) {
                  parts.push(`Error: ${item.error}`);
                }
                return parts.join(' - ');
              };

              const getTime = () => {
                const time = item.completed_at || item.started_at;
                return time ? new Date(time).toLocaleString() : 'Unknown time';
              };

              return {
                color: getColor(),
                children: `${getDescription()} - ${getTime()}`,
              };
            })}
          />
        ) : (
          <p>No sync history available</p>
        )}
      </Card>
    </div>
  );
};

export default SyncManagement;
