import React from 'react';
import { Card, Button, Space, Statistic, Row, Col } from 'antd';
import { useNavigate } from 'react-router-dom';
import { useQuery } from 'react-query';
import {
  BulbOutlined,
  FileTextOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import { apiClient } from '@/services/apiClient';

const Analysis: React.FC = () => {
  const navigate = useNavigate();

  // Fetch analysis statistics
  const { data: analysisStats } = useQuery('analysisStats', () =>
    apiClient.getAnalysisStats()
  );

  const handleViewResults = () => {
    void navigate('/analysis/plans');
  };

  return (
    <div>
      <h1>Analysis Overview</h1>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={8}>
          <Card>
            <Statistic
              title="Scenes Analyzed"
              value={analysisStats?.analyzed_scenes || 0}
              suffix={`/ ${analysisStats?.total_scenes || 0}`}
              prefix={<BulbOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={8}>
          <Card>
            <Statistic
              title="Analysis Plans"
              value={analysisStats?.total_plans || 0}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={8}>
          <Card>
            <Statistic
              title="Pending Analysis"
              value={analysisStats?.pending_analysis || 0}
              prefix={<RocketOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Card title="Quick Actions">
        <Space>
          <Button
            type="primary"
            onClick={() => {
              void navigate('/analysis/plans');
            }}
          >
            Manage Plans
          </Button>
          <Button onClick={handleViewResults}>View Recent Results</Button>
        </Space>
      </Card>
    </div>
  );
};

export default Analysis;
