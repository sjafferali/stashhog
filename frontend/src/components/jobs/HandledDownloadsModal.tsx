import React, { useState, useEffect, useCallback } from 'react';
import {
  Modal,
  Table,
  Typography,
  Spin,
  message,
  Space,
  Tag,
  Tooltip,
  Button,
} from 'antd';
import {
  FileOutlined,
  FolderOpenOutlined,
  ClockCircleOutlined,
  CopyOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { apiClient } from '@/services/apiClient';

const { Text, Title } = Typography;

interface HandledDownload {
  id: number;
  timestamp: string;
  download_name: string;
  destination_path: string;
}

interface HandledDownloadsModalProps {
  jobId: string;
  visible: boolean;
  onClose: () => void;
}

export const HandledDownloadsModal: React.FC<HandledDownloadsModalProps> = ({
  jobId,
  visible,
  onClose,
}) => {
  const [loading, setLoading] = useState(false);
  const [downloads, setDownloads] = useState<HandledDownload[]>([]);
  const [totalDownloads, setTotalDownloads] = useState(0);

  const fetchHandledDownloads = useCallback(async () => {
    setLoading(true);
    try {
      const response = await apiClient.getJobHandledDownloads(jobId);
      setDownloads(response.downloads);
      setTotalDownloads(response.total_downloads);
    } catch (error) {
      console.error('Failed to fetch handled downloads:', error);
      void message.error('Failed to fetch handled downloads');
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    if (visible && jobId) {
      void fetchHandledDownloads();
    }
  }, [visible, jobId, fetchHandledDownloads]);

  const columns: ColumnsType<HandledDownload> = [
    {
      title: 'File Name',
      dataIndex: 'download_name',
      key: 'download_name',
      render: (name: string) => (
        <Space>
          <FileOutlined />
          <Text strong>{name}</Text>
        </Space>
      ),
    },
    {
      title: 'Destination Path',
      dataIndex: 'destination_path',
      key: 'destination_path',
      render: (path: string) => (
        <Space>
          <FolderOpenOutlined />
          <Tooltip title={path}>
            <Text
              style={{
                maxWidth: '400px',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                display: 'inline-block',
              }}
              copyable={{
                text: path,
                icon: <CopyOutlined />,
              }}
            >
              {path}
            </Text>
          </Tooltip>
        </Space>
      ),
    },
    {
      title: 'Processed At',
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 200,
      render: (timestamp: string) => (
        <Space>
          <ClockCircleOutlined />
          <Text>{new Date(timestamp).toLocaleString()}</Text>
        </Space>
      ),
    },
  ];

  return (
    <Modal
      title={
        <Space>
          <FileOutlined />
          <Title level={4} style={{ margin: 0 }}>
            Processed Files
          </Title>
          <Tag color="blue">{totalDownloads} files</Tag>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      width={900}
      footer={[
        <Button key="close" onClick={onClose}>
          Close
        </Button>,
      ]}
    >
      {loading ? (
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <Spin size="large" />
        </div>
      ) : (
        <Table
          columns={columns}
          dataSource={downloads}
          rowKey="id"
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `Total ${total} files`,
          }}
          scroll={{ x: 800 }}
        />
      )}
    </Modal>
  );
};
