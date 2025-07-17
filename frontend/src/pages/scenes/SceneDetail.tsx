import React, { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Button, Descriptions, Tag, Space, Modal, message } from 'antd';
import {
  ArrowLeftOutlined,
  EditOutlined,
  RobotOutlined,
  LinkOutlined,
} from '@ant-design/icons';
import { useMutation, useQueryClient } from 'react-query';
import api from '@/services/api';
import useAppStore from '@/store';

const SceneDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { settings, loadSettings, isLoaded } = useAppStore();

  // Load settings if not already loaded
  useEffect(() => {
    if (!isLoaded) {
      void loadSettings();
    }
  }, [isLoaded, loadSettings]);

  const handleOpenInStash = () => {
    if (settings?.stash_url && id) {
      // Remove trailing slash from stash_url if present
      const baseUrl = settings.stash_url.replace(/\/$/, '');
      const stashUrl = `${baseUrl}/scenes/${id}`;
      window.open(stashUrl, '_blank');
    }
  };

  // Analyze mutation
  const analyzeMutation = useMutation(
    async () => {
      const response = await api.post('/analysis/generate', {
        scene_ids: [id || '0'],
        plan_name: `Scene #${id} Analysis - ${new Date().toISOString()}`,
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
        void message.success('Started analysis for scene');
        void queryClient.invalidateQueries('jobs');
      },
      onError: () => {
        void message.error('Failed to start analysis');
      },
    }
  );

  const handleAnalyze = () => {
    Modal.confirm({
      title: 'Analyze Scene',
      content: 'Are you sure you want to analyze this scene?',
      onOk: () => {
        analyzeMutation.mutate();
      },
    });
  };

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => {
            void navigate('/scenes');
          }}
        >
          Back
        </Button>
        <h1 style={{ margin: 0 }}>Scene Detail</h1>
      </Space>

      <Card
        title={`Scene #${id}`}
        extra={
          <Space>
            <Button icon={<EditOutlined />}>Edit</Button>
            <Button
              icon={<LinkOutlined />}
              onClick={handleOpenInStash}
              disabled={!settings?.stash_url}
            >
              Open in Stash
            </Button>
            <Button
              type="primary"
              icon={<RobotOutlined />}
              onClick={handleAnalyze}
              loading={analyzeMutation.isLoading}
            >
              Analyze
            </Button>
          </Space>
        }
      >
        <Descriptions bordered>
          <Descriptions.Item label="Title">Loading...</Descriptions.Item>
          <Descriptions.Item label="Date">-</Descriptions.Item>
          <Descriptions.Item label="Duration">-</Descriptions.Item>
          <Descriptions.Item label="Resolution">-</Descriptions.Item>
          <Descriptions.Item label="File Size">-</Descriptions.Item>
          <Descriptions.Item label="Path" span={3}>
            -
          </Descriptions.Item>
          <Descriptions.Item label="Tags" span={3}>
            <Tag>Example Tag</Tag>
          </Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  );
};

export default SceneDetail;
