import React, { useState, useCallback } from 'react';
import {
  Card,
  Space,
  Button,
  Spin,
  Empty,
  Typography,
  Pagination,
  Table,
  Input,
  Tag,
} from 'antd';
import {
  UserOutlined,
  ReloadOutlined,
  SearchOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ColumnsType } from 'antd/es/table';
import api from '@/services/api';
import { Performer } from '@/types/models';
import { PerformerDetailModal } from './components/PerformerDetailModal';

const { Title } = Typography;
const { Search } = Input;

interface PerformersResponse {
  items: Performer[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

const PerformersList: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const [selectedPerformer, setSelectedPerformer] = useState<Performer | null>(
    null
  );
  const [searchText, setSearchText] = useState(
    searchParams.get('search') || ''
  );

  // Pagination state from URL
  const page = parseInt(searchParams.get('page') || '1', 10);
  const pageSize = parseInt(searchParams.get('per_page') || '50', 10);
  const sortBy = searchParams.get('sort_by') || 'name';
  const sortOrder = searchParams.get('sort_order') || 'asc';
  const search = searchParams.get('search') || '';

  // Fetch performers
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['performers', page, pageSize, sortBy, sortOrder, search],
    queryFn: async () => {
      const params = new URLSearchParams({
        page: page.toString(),
        per_page: pageSize.toString(),
        sort_by: sortBy,
        sort_order: sortOrder,
      });
      if (search) {
        params.append('search', search);
      }
      const response = await api.get<PerformersResponse>(
        `/entities/performers?${params}`
      );
      return response.data;
    },
  });

  const handleSearch = useCallback(
    (value: string) => {
      const params = new URLSearchParams(searchParams);
      if (value) {
        params.set('search', value);
      } else {
        params.delete('search');
      }
      params.set('page', '1'); // Reset to first page on search
      setSearchParams(params);
    },
    [searchParams, setSearchParams]
  );

  const handlePageChange = useCallback(
    (newPage: number, newPageSize?: number) => {
      const params = new URLSearchParams(searchParams);
      params.set('page', newPage.toString());
      if (newPageSize && newPageSize !== pageSize) {
        params.set('per_page', newPageSize.toString());
      }
      setSearchParams(params);
    },
    [searchParams, setSearchParams, pageSize]
  );

  const handleSortChange = useCallback(
    (column: string) => {
      const params = new URLSearchParams(searchParams);
      if (sortBy === column) {
        params.set('sort_order', sortOrder === 'asc' ? 'desc' : 'asc');
      } else {
        params.set('sort_by', column);
        params.set('sort_order', 'asc');
      }
      setSearchParams(params);
    },
    [searchParams, setSearchParams, sortBy, sortOrder]
  );

  const handleViewScenes = useCallback(
    (performerId: string) => {
      void navigate(`/scenes?performer_ids=${performerId}`);
    },
    [navigate]
  );

  const handleViewDetails = useCallback((performer: Performer) => {
    // Fetch full details
    void (async () => {
      const response = await api.get(`/entities/performers/${performer.id}`);
      setSelectedPerformer(response.data);
    })();
  }, []);

  const columns: ColumnsType<Performer> = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      sorter: true,
      sortOrder:
        sortBy === 'name' ? (sortOrder === 'asc' ? 'ascend' : 'descend') : null,
      render: (name: string) => (
        <Space>
          <UserOutlined />
          <span style={{ fontWeight: 500 }}>{name}</span>
        </Space>
      ),
    },
    {
      title: 'Gender',
      dataIndex: 'gender',
      key: 'gender',
      width: 100,
      render: (gender: string | null) => gender || '-',
    },
    {
      title: 'Scenes',
      dataIndex: 'scene_count',
      key: 'scene_count',
      width: 100,
      align: 'center',
      sorter: true,
      sortOrder:
        sortBy === 'scene_count'
          ? sortOrder === 'asc'
            ? 'ascend'
            : 'descend'
          : null,
      render: (count: number) => <Tag color="blue">{count}</Tag>,
    },
    {
      title: 'Favorite',
      dataIndex: 'favorite',
      key: 'favorite',
      width: 100,
      align: 'center',
      render: (favorite: boolean) => (favorite ? '⭐' : ''),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 200,
      render: (_: unknown, record: Performer) => (
        <Space>
          <Button
            size="small"
            icon={<EyeOutlined />}
            onClick={() => void handleViewDetails(record)}
          >
            Details
          </Button>
          <Button size="small" onClick={() => handleViewScenes(record.id)}>
            View Scenes
          </Button>
        </Space>
      ),
    },
  ];

  const handleTableChange = useCallback(
    (_pagination: unknown, _filters: unknown, sorter: unknown) => {
      if (
        !Array.isArray(sorter) &&
        sorter &&
        typeof sorter === 'object' &&
        'field' in sorter &&
        typeof sorter.field === 'string'
      ) {
        handleSortChange(sorter.field);
      }
    },
    [handleSortChange]
  );

  return (
    <div style={{ padding: '24px' }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* Header */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <Title level={2} style={{ margin: 0 }}>
            Performers
          </Title>
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => void refetch()}
              loading={isLoading}
            >
              Refresh
            </Button>
          </Space>
        </div>

        {/* Search Bar */}
        <Card>
          <Search
            placeholder="Search performers by name..."
            allowClear
            enterButton={<SearchOutlined />}
            size="large"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            onSearch={handleSearch}
            style={{ maxWidth: 600 }}
          />
        </Card>

        {/* Performers Table */}
        <Card>
          {error ? (
            <Empty
              description={`Failed to load performers: ${error.message}`}
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          ) : (
            <Spin spinning={isLoading}>
              <Table
                columns={columns}
                dataSource={data?.items || []}
                rowKey="id"
                pagination={false}
                onChange={handleTableChange}
                onRow={() => ({
                  style: { cursor: 'pointer' },
                })}
              />

              {/* Pagination */}
              {data && data.total > 0 && (
                <div style={{ marginTop: 24, textAlign: 'center' }}>
                  <Pagination
                    current={page}
                    pageSize={pageSize}
                    total={data.total}
                    onChange={handlePageChange}
                    showSizeChanger
                    showTotal={(total: number, range: [number, number]) =>
                      `${range[0]}-${range[1]} of ${total} performers`
                    }
                    pageSizeOptions={['20', '50', '100']}
                  />
                </div>
              )}
            </Spin>
          )}
        </Card>
      </Space>

      {/* Performer Detail Modal */}
      {selectedPerformer && (
        <PerformerDetailModal
          performer={selectedPerformer}
          visible={!!selectedPerformer}
          onClose={() => setSelectedPerformer(null)}
          onViewScenes={handleViewScenes}
        />
      )}
    </div>
  );
};

export default PerformersList;
