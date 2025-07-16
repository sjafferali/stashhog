import React from 'react';
import { Card, Button, Space, Statistic, Row, Col, Modal, message } from 'antd';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQueryClient } from 'react-query';
import {
  BulbOutlined,
  FileTextOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import api from '@/services/api';

const Analysis: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Batch analysis mutation
  const batchAnalysisMutation = useMutation(
    async () => {
      const response = await api.post('/analysis/generate', {
        filters: {
          organized: false,
        },
        options: {
          detect_performers: true,
          detect_studios: true,
          detect_tags: true,
          detect_details: true,
          use_ai: true,
          confidence_threshold: 0.7,
        },
      });
      return response.data;
    },
    {
      onSuccess: () => {
        void message.success('Started batch analysis for unorganized scenes');
        void queryClient.invalidateQueries('jobs');
        void navigate('/jobs');
      },
      onError: () => {
        void message.error('Failed to start batch analysis');
      },
    }
  );

  const handleBatchAnalysis = () => {
    Modal.confirm({
      title: 'Run Batch Analysis',
      content: 'This will analyze all unorganized scenes. Continue?',
      onOk: () => {
        batchAnalysisMutation.mutate();
      },
    });
  };

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
              value={0}
              suffix="/ 0"
              prefix={<BulbOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={8}>
          <Card>
            <Statistic
              title="Analysis Plans"
              value={0}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={8}>
          <Card>
            <Statistic
              title="Pending Analysis"
              value={0}
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
          <Button
            onClick={handleBatchAnalysis}
            loading={batchAnalysisMutation.isLoading}
          >
            Run Batch Analysis
          </Button>
          <Button onClick={handleViewResults}>View Recent Results</Button>
        </Space>
      </Card>
    </div>
  );
};

export default Analysis;
