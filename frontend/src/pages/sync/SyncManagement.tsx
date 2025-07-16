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
import { SyncStatus } from '@/types/models';

const SyncManagement: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<SyncStatus | null>(null);
  const [syncing, setSyncing] = useState(false);

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

  useEffect(() => {
    void fetchStats();
  }, []);

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

  const isSyncing = false; // TODO: Implement proper sync status check

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

      <Card title="Recent Sync History" style={{ marginTop: 16 }}>
        <Timeline
          items={[
            {
              color: 'green',
              children: 'Example sync completed - 2024-01-01 12:00:00',
            },
            {
              color: 'blue',
              children: 'Example sync started - 2024-01-01 11:00:00',
            },
          ]}
        />
      </Card>
    </div>
  );
};

export default SyncManagement;
