import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Button, Descriptions, Tag, Space } from 'antd';
import {
  ArrowLeftOutlined,
  EditOutlined,
  RobotOutlined,
} from '@ant-design/icons';

const SceneDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

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
            <Button type="primary" icon={<RobotOutlined />}>
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
