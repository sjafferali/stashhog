import React from 'react';
import { Card, Button, Space, Statistic, Row, Col, Modal, message } from 'antd';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from 'react-query';
import {
  BulbOutlined,
  FileTextOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import api from '@/services/api';
import { apiClient } from '@/services/apiClient';

const Analysis: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Fetch analysis statistics
  const { data: analysisStats } = useQuery('analysisStats', () =>
    apiClient.getAnalysisStats()
  );

  // Batch analysis mutation
  const batchAnalysisMutation = useMutation(
    async () => {
      const response = await api.post('/analysis/generate', {
        filters: {
          analyzed: false,
        },
        plan_name: `Batch Analysis - Unanalyzed Scenes - ${new Date().toISOString()}`,
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
        void message.success('Started batch analysis for unanalyzed scenes');
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
      content: 'This will analyze all unanalyzed scenes. Continue?',
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
