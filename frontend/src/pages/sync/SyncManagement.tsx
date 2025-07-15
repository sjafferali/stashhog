import React from 'react';
import {
  Card,
  Button,
  Space,
  Statistic,
  Row,
  Col,
  Alert,
  Timeline,
} from 'antd';
import {
  SyncOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
} from '@ant-design/icons';

const SyncManagement: React.FC = () => {
  const isSyncing = false;

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

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="Total Scenes" value={0} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="Total Performers" value={0} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="Total Tags" value={0} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="Total Studios" value={0} />
          </Card>
        </Col>
      </Row>

      <Card
        title="Sync Controls"
        extra={
          <Space>
            <Button
              type="primary"
              icon={
                isSyncing ? <PauseCircleOutlined /> : <PlayCircleOutlined />
              }
              loading={false}
            >
              {isSyncing ? 'Stop Sync' : 'Start Sync'}
            </Button>
            <Button icon={<SyncOutlined />}>Refresh</Button>
          </Space>
        }
      >
        <p>Last sync: Never</p>
        <p>Scenes to analyze: 0</p>
      </Card>

      <Card title="Recent Sync History" style={{ marginTop: 16 }}>
        <Timeline>
          <Timeline.Item color="green">
            Example sync completed - 2024-01-01 12:00:00
          </Timeline.Item>
          <Timeline.Item color="blue">
            Example sync started - 2024-01-01 11:00:00
          </Timeline.Item>
        </Timeline>
      </Card>
    </div>
  );
};

export default SyncManagement;
