import React, { useState } from 'react';
import { 
  Modal, 
  Tabs, 
  Descriptions, 
  Tag, 
  Space, 
  Button, 
  Image,
  List,
  Typography,
  Divider,
  Timeline,
  Empty,
  Spin
} from 'antd';
import { 
  FileOutlined, 
  InfoCircleOutlined, 
  ExperimentOutlined,
  HistoryOutlined,
  ExportOutlined,
  EditOutlined,
  SyncOutlined
} from '@ant-design/icons';
import { useQuery } from 'react-query';
import dayjs from 'dayjs';
import api from '@/services/api';
import { Scene, AnalysisResult } from '@/types/models';

const { TabPane } = Tabs;
const { Text, Title, Paragraph } = Typography;

interface SceneDetailModalProps {
  scene: Scene;
  visible: boolean;
  onClose: () => void;
}

export const SceneDetailModal: React.FC<SceneDetailModalProps> = ({ 
  scene, 
  visible, 
  onClose 
}) => {
  const [activeTab, setActiveTab] = useState('overview');

  // Fetch full scene details with analysis results
  const { data: fullScene, isLoading } = useQuery<Scene>(
    ['scene', scene.id],
    async () => {
      const response = await api.get(`/scenes/${scene.id}`);
      return response.data;
    },
    {
      enabled: visible,
    }
  );

  const formatFileSize = (bytes?: string): string => {
    if (!bytes) return 'N/A';
    const size = parseInt(bytes, 10);
    if (isNaN(size)) return 'N/A';
    
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let unitIndex = 0;
    let formattedSize = size;
    
    while (formattedSize >= 1024 && unitIndex < units.length - 1) {
      formattedSize /= 1024;
      unitIndex++;
    }
    
    return `${formattedSize.toFixed(1)} ${units[unitIndex]}`;
  };

  const formatDuration = (seconds?: number): string => {
    if (!seconds) return 'N/A';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  const renderOverviewTab = () => (
    <Spin spinning={isLoading}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* Thumbnail */}
        <div style={{ textAlign: 'center' }}>
          <Image
            width={400}
            src={`/api/scenes/${scene.id}/thumbnail`}
            alt={scene.title || 'Scene thumbnail'}
            fallback="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
          />
        </div>

        {/* Basic Info */}
        <Descriptions bordered column={2}>
          <Descriptions.Item label="Title" span={2}>
            {fullScene?.title || 'Untitled'}
          </Descriptions.Item>
          
          <Descriptions.Item label="Studio">
            {fullScene?.studio ? (
              <Tag color="blue">{fullScene.studio.name}</Tag>
            ) : 'N/A'}
          </Descriptions.Item>
          
          <Descriptions.Item label="Date">
            {fullScene?.date || 'N/A'}
          </Descriptions.Item>
          
          <Descriptions.Item label="Duration">
            {formatDuration(fullScene?.duration)}
          </Descriptions.Item>
          
          <Descriptions.Item label="File Size">
            {formatFileSize(fullScene?.size)}
          </Descriptions.Item>
          
          <Descriptions.Item label="Resolution">
            {fullScene?.width && fullScene?.height ? 
              `${fullScene.width}x${fullScene.height}` : 'N/A'}
          </Descriptions.Item>
          
          <Descriptions.Item label="Frame Rate">
            {fullScene?.framerate ? `${fullScene.framerate} fps` : 'N/A'}
          </Descriptions.Item>
          
          <Descriptions.Item label="Codec">
            {fullScene?.codec || 'N/A'}
          </Descriptions.Item>
          
          <Descriptions.Item label="Bitrate">
            {fullScene?.bitrate ? `${fullScene.bitrate} kbps` : 'N/A'}
          </Descriptions.Item>
        </Descriptions>

        {/* Performers */}
        {fullScene?.performers && fullScene.performers.length > 0 && (
          <>
            <Divider>Performers</Divider>
            <Space wrap>
              {fullScene.performers.map(performer => (
                <Tag key={performer.id} color="pink" style={{ margin: '2px' }}>
                  {performer.name}
                </Tag>
              ))}
            </Space>
          </>
        )}

        {/* Tags */}
        {fullScene?.tags && fullScene.tags.length > 0 && (
          <>
            <Divider>Tags</Divider>
            <Space wrap>
              {fullScene.tags.map(tag => (
                <Tag key={tag.id} color="green" style={{ margin: '2px' }}>
                  {tag.name}
                </Tag>
              ))}
            </Space>
          </>
        )}

        {/* Details */}
        {fullScene?.details && (
          <>
            <Divider>Details</Divider>
            <Paragraph>{fullScene.details}</Paragraph>
          </>
        )}
      </Space>
    </Spin>
  );

  const renderFilesTab = () => (
    <Descriptions bordered column={1}>
      <Descriptions.Item label="Path">
        <Text code>{fullScene?.path || 'N/A'}</Text>
      </Descriptions.Item>
      
      <Descriptions.Item label="Stash ID">
        <Text copyable>{fullScene?.stash_id || 'N/A'}</Text>
      </Descriptions.Item>
      
      <Descriptions.Item label="Perceptual Hash">
        <Text code>{fullScene?.phash || 'N/A'}</Text>
      </Descriptions.Item>
      
      <Descriptions.Item label="File Modified">
        {fullScene?.file_mod_time ? 
          dayjs(fullScene.file_mod_time).format('YYYY-MM-DD HH:mm:ss') : 'N/A'}
      </Descriptions.Item>
      
      <Descriptions.Item label="Created">
        {dayjs(fullScene?.created_at).format('YYYY-MM-DD HH:mm:ss')}
      </Descriptions.Item>
      
      <Descriptions.Item label="Updated">
        {dayjs(fullScene?.updated_at).format('YYYY-MM-DD HH:mm:ss')}
      </Descriptions.Item>
    </Descriptions>
  );

  const renderAnalysisTab = () => {
    const analysisResults = fullScene?.analysis_results || [];

    if (analysisResults.length === 0) {
      return (
        <Empty
          description="No analysis results yet"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        >
          <Button type="primary" icon={<ExperimentOutlined />}>
            Analyze Scene
          </Button>
        </Empty>
      );
    }

    return (
      <List
        dataSource={analysisResults}
        renderItem={(result: AnalysisResult) => (
          <List.Item>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Space>
                <Text strong>Plan:</Text>
                <Tag>{result.plan?.name || 'Unknown'}</Tag>
                <Text type="secondary">
                  {dayjs(result.created_at).format('YYYY-MM-DD HH:mm:ss')}
                </Text>
              </Space>
              
              {result.extracted_data && (
                <Descriptions size="small" bordered column={1}>
                  {result.extracted_data.title && (
                    <Descriptions.Item label="Title">
                      {result.extracted_data.title}
                    </Descriptions.Item>
                  )}
                  
                  {result.extracted_data.date && (
                    <Descriptions.Item label="Date">
                      {result.extracted_data.date}
                    </Descriptions.Item>
                  )}
                  
                  {result.extracted_data.performers && (
                    <Descriptions.Item label="Performers">
                      {result.extracted_data.performers.join(', ')}
                    </Descriptions.Item>
                  )}
                  
                  {result.extracted_data.tags && (
                    <Descriptions.Item label="Tags">
                      {result.extracted_data.tags.join(', ')}
                    </Descriptions.Item>
                  )}
                  
                  {result.extracted_data.studio && (
                    <Descriptions.Item label="Studio">
                      {result.extracted_data.studio}
                    </Descriptions.Item>
                  )}
                  
                  {result.extracted_data.details && (
                    <Descriptions.Item label="Details">
                      {result.extracted_data.details}
                    </Descriptions.Item>
                  )}
                </Descriptions>
              )}
              
              <Space size="small">
                <Text type="secondary">Model: {result.model_used}</Text>
                <Text type="secondary">Time: {result.processing_time}s</Text>
              </Space>
            </Space>
          </List.Item>
        )}
      />
    );
  };

  const renderHistoryTab = () => (
    <Timeline>
      <Timeline.Item color="green">
        <Text strong>Scene Created</Text>
        <br />
        <Text type="secondary">
          {dayjs(fullScene?.created_at).format('YYYY-MM-DD HH:mm:ss')}
        </Text>
      </Timeline.Item>
      
      {fullScene?.analyzed_at && (
        <Timeline.Item color="blue">
          <Text strong>First Analysis</Text>
          <br />
          <Text type="secondary">
            {dayjs(fullScene.analyzed_at).format('YYYY-MM-DD HH:mm:ss')}
          </Text>
        </Timeline.Item>
      )}
      
      {fullScene?.analysis_results?.map((result, index) => (
        <Timeline.Item key={result.id}>
          <Text strong>Analysis #{index + 1}</Text>
          <br />
          <Text type="secondary">
            {dayjs(result.created_at).format('YYYY-MM-DD HH:mm:ss')}
          </Text>
          <br />
          <Text type="secondary">Plan: {result.plan?.name || 'Unknown'}</Text>
        </Timeline.Item>
      ))}
      
      <Timeline.Item>
        <Text strong>Last Updated</Text>
        <br />
        <Text type="secondary">
          {dayjs(fullScene?.updated_at).format('YYYY-MM-DD HH:mm:ss')}
        </Text>
      </Timeline.Item>
    </Timeline>
  );

  return (
    <Modal
      title={
        <Space>
          <FileOutlined />
          {scene.title || 'Scene Details'}
        </Space>
      }
      open={visible}
      onCancel={onClose}
      width={800}
      footer={[
        <Button key="close" onClick={onClose}>
          Close
        </Button>,
        <Button key="edit" icon={<EditOutlined />}>
          Edit
        </Button>,
        <Button key="analyze" type="primary" icon={<ExperimentOutlined />}>
          Analyze
        </Button>,
      ]}
    >
      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        <TabPane 
          tab={<span><InfoCircleOutlined /> Overview</span>} 
          key="overview"
        >
          {renderOverviewTab()}
        </TabPane>
        
        <TabPane 
          tab={<span><FileOutlined /> Files/Paths</span>} 
          key="files"
        >
          {renderFilesTab()}
        </TabPane>
        
        <TabPane 
          tab={<span><ExperimentOutlined /> Analysis</span>} 
          key="analysis"
        >
          {renderAnalysisTab()}
        </TabPane>
        
        <TabPane 
          tab={<span><HistoryOutlined /> History</span>} 
          key="history"
        >
          {renderHistoryTab()}
        </TabPane>
      </Tabs>
    </Modal>
  );
};