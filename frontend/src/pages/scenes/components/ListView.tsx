import React, { useMemo, useCallback } from 'react';
import { Table, Tag, Space, Button, Checkbox, Typography, Image, Tooltip } from 'antd';
import { 
  EyeOutlined, 
  ExperimentOutlined,
  CheckCircleOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';
import { ColumnsType } from 'antd/es/table';
import { useSearchParams } from 'react-router-dom';
import { Scene } from '@/types/models';
import { useScenesStore } from '@/store/slices/scenes';
import dayjs from 'dayjs';

const { Text } = Typography;

interface ListViewProps {
  scenes: Scene[];
  onSceneSelect: (scene: Scene) => void;
}

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

export const ListView: React.FC<ListViewProps> = ({ scenes, onSceneSelect }) => {
  const [searchParams, setSearchParams] = useSearchParams();
  const { selectedScenes, toggleSceneSelection, selectAllScenes, clearSelection } = useScenesStore();
  
  const sortBy = searchParams.get('sort_by') || 'created_at';
  const sortDir = searchParams.get('sort_dir') || 'desc';

  const handleSortChange = useCallback((column: string) => {
    const params = new URLSearchParams(searchParams);
    
    if (sortBy === column) {
      // Toggle direction if same column
      params.set('sort_dir', sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      // New column, default to desc
      params.set('sort_by', column);
      params.set('sort_dir', 'desc');
    }
    
    setSearchParams(params);
  }, [searchParams, setSearchParams, sortBy, sortDir]);

  const columns: ColumnsType<Scene> = useMemo(() => [
    {
      title: () => (
        <Checkbox
          checked={scenes.length > 0 && scenes.every(s => selectedScenes.has(s.id.toString()))}
          indeterminate={scenes.some(s => selectedScenes.has(s.id.toString())) && 
                        !scenes.every(s => selectedScenes.has(s.id.toString()))}
          onChange={(e) => {
            if (e.target.checked) {
              selectAllScenes(scenes.map(s => s.id.toString()));
            } else {
              clearSelection();
            }
          }}
        />
      ),
      key: 'selection',
      width: 50,
      fixed: 'left',
      render: (_, record) => (
        <Checkbox
          checked={selectedScenes.has(record.id.toString())}
          onClick={(e) => e.stopPropagation()}
          onChange={() => toggleSceneSelection(record.id.toString())}
        />
      ),
    },
    {
      title: 'Thumbnail',
      key: 'thumbnail',
      width: 120,
      render: (_, record) => (
        <Image
          width={100}
          height={60}
          src={`/api/scenes/${record.id}/thumbnail`}
          alt={record.title || 'Scene thumbnail'}
          preview={false}
          style={{ objectFit: 'cover', borderRadius: 4 }}
          fallback="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        />
      ),
    },
    {
      title: 'Title',
      dataIndex: 'title',
      key: 'title',
      sorter: true,
      sortOrder: sortBy === 'title' ? (sortDir === 'asc' ? 'ascend' : 'descend') : null,
      render: (title, record) => (
        <Space direction="vertical" size="small">
          <Text strong>{title || 'Untitled'}</Text>
          {record.path && (
            <Text type="secondary" ellipsis style={{ fontSize: 12, maxWidth: 300 }}>
              {record.path}
            </Text>
          )}
        </Space>
      ),
    },
    {
      title: 'Studio',
      key: 'studio',
      width: 150,
      render: (_, record) => record.studio ? (
        <Tag color="blue">{record.studio.name}</Tag>
      ) : null,
    },
    {
      title: 'Performers',
      key: 'performers',
      width: 200,
      render: (_, record) => (
        <Space size="small" wrap>
          {record.performers?.map(performer => (
            <Tag key={performer.id} color="pink">
              {performer.name}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: 'Tags',
      key: 'tags',
      width: 200,
      render: (_, record) => (
        <Space size="small" wrap>
          {record.tags?.slice(0, 3).map(tag => (
            <Tag key={tag.id} color="green">
              {tag.name}
            </Tag>
          ))}
          {record.tags && record.tags.length > 3 && (
            <Tag>+{record.tags.length - 3} more</Tag>
          )}
        </Space>
      ),
    },
    {
      title: 'Date',
      dataIndex: 'date',
      key: 'date',
      width: 120,
      sorter: true,
      sortOrder: sortBy === 'date' ? (sortDir === 'asc' ? 'ascend' : 'descend') : null,
      render: (date) => date ? dayjs(date).format('YYYY-MM-DD') : 'N/A',
    },
    {
      title: 'Duration',
      dataIndex: 'duration',
      key: 'duration',
      width: 100,
      sorter: true,
      sortOrder: sortBy === 'duration' ? (sortDir === 'asc' ? 'ascend' : 'descend') : null,
      render: (duration) => formatDuration(duration),
    },
    {
      title: 'Status',
      key: 'status',
      width: 100,
      render: (_, record) => (
        <Space>
          {record.organized && (
            <Tooltip title="Organized">
              <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 16 }} />
            </Tooltip>
          )}
          {record.details && (
            <Tooltip title="Has details">
              <InfoCircleOutlined style={{ color: '#1890ff', fontSize: 16 }} />
            </Tooltip>
          )}
        </Space>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 120,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          <Button
            size="small"
            icon={<EyeOutlined />}
            onClick={(e) => {
              e.stopPropagation();
              onSceneSelect(record);
            }}
          >
            View
          </Button>
          <Button
            size="small"
            icon={<ExperimentOutlined />}
            onClick={(e) => {
              e.stopPropagation();
              // TODO: Implement analyze action
            }}
          >
            Analyze
          </Button>
        </Space>
      ),
    },
  ], [scenes, selectedScenes, sortBy, sortDir, onSceneSelect, toggleSceneSelection, selectAllScenes, clearSelection]);

  const handleTableChange = useCallback((pagination: any, filters: any, sorter: any) => {
    if (sorter.field) {
      handleSortChange(sorter.field);
    }
  }, [handleSortChange]);

  return (
    <Table
      columns={columns}
      dataSource={scenes}
      rowKey="id"
      pagination={false}
      onChange={handleTableChange}
      scroll={{ x: 1200 }}
      onRow={(record) => ({
        onClick: () => onSceneSelect(record),
        style: { cursor: 'pointer' },
      })}
      rowClassName={(record) => 
        selectedScenes.has(record.id.toString()) ? 'ant-table-row-selected' : ''
      }
    />
  );
};