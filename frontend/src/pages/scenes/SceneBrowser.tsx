import React, { useState, useCallback, useMemo } from 'react';
import { Card, Space, Button, Spin, Empty, Typography, Pagination } from 'antd';
import {
  AppstoreOutlined,
  UnorderedListOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useSearchParams } from 'react-router-dom';
import { useScenes } from './hooks/useScenes';
import { useSceneFilters } from './hooks/useSceneFilters';
import { SearchBar } from './components/SearchBar';
import { AdvancedFilters } from './components/AdvancedFilters';
import { SceneListContainer } from './components/SceneListContainer';
import { SceneActions } from './components/SceneActions';
import { SyncButton } from './components/SyncButton';
import { SceneDetailModal } from './components/SceneDetailModal';
import { mergeWithQueryParams } from './utils/filters';
import { Scene } from '@/types/models';
import { useScenesStore } from '@/store/slices/scenes';

const { Title } = Typography;

const SceneBrowser: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [selectedScene, setSelectedScene] = useState<Scene | null>(null);

  const { filters, activeFilterCount } = useSceneFilters();
  const { viewMode, setViewMode, selectedScenes, clearSelection } =
    useScenesStore();

  // Pagination state from URL
  const page = parseInt(searchParams.get('page') || '1', 10);
  const pageSize = parseInt(searchParams.get('per_page') || '20', 10);
  const sortBy = searchParams.get('sort_by') || 'created_at';
  const sortOrder = (searchParams.get('sort_order') || 'desc') as
    | 'asc'
    | 'desc';

  // Build query params
  const queryParams = useMemo(
    () =>
      mergeWithQueryParams(filters, {
        page,
        per_page: pageSize,
        sort_by: sortBy,
        sort_order: sortOrder,
      }),
    [filters, page, pageSize, sortBy, sortOrder]
  );

  // Fetch scenes
  const { data, isLoading, error, refetch } = useScenes(queryParams);

  const handleSceneSelect = useCallback((scene: Scene) => {
    setSelectedScene(scene);
  }, []);

  const handleCloseModal = useCallback(() => {
    setSelectedScene(null);
  }, []);

  const toggleViewMode = useCallback(() => {
    setViewMode(viewMode === 'grid' ? 'list' : 'grid');
  }, [viewMode, setViewMode]);

  const handleToggleFilters = useCallback(() => {
    setShowAdvancedFilters(!showAdvancedFilters);
  }, [showAdvancedFilters]);

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
            Scenes
          </Title>
          <Space>
            <SyncButton onSyncComplete={() => void refetch()} />
            <Button
              icon={<ReloadOutlined />}
              onClick={() => void refetch()}
              loading={isLoading}
            >
              Refresh
            </Button>
            <Button
              icon={
                viewMode === 'grid' ? (
                  <UnorderedListOutlined />
                ) : (
                  <AppstoreOutlined />
                )
              }
              onClick={toggleViewMode}
            >
              {viewMode === 'grid' ? 'List View' : 'Grid View'}
            </Button>
          </Space>
        </div>

        {/* Search Bar */}
        <SearchBar
          onToggleAdvancedFilters={handleToggleFilters}
          showingAdvancedFilters={showAdvancedFilters}
          activeFilterCount={activeFilterCount}
        />

        {/* Advanced Filters */}
        {showAdvancedFilters && <AdvancedFilters />}

        {/* Bulk Actions */}
        {selectedScenes.size > 0 && (
          <SceneActions
            selectedCount={selectedScenes.size}
            onClearSelection={clearSelection}
          />
        )}

        {/* Scene List */}
        <Card>
          {error ? (
            <Empty
              description={`Failed to load scenes: ${error.message}`}
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          ) : (
            <Spin spinning={isLoading}>
              <SceneListContainer
                scenes={data?.items || []}
                viewMode={viewMode}
                onSceneSelect={handleSceneSelect}
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
                      `${range[0]}-${range[1]} of ${total} scenes`
                    }
                    pageSizeOptions={['10', '20', '50', '100']}
                  />
                </div>
              )}
            </Spin>
          )}
        </Card>
      </Space>

      {/* Scene Detail Modal */}
      {selectedScene && (
        <SceneDetailModal
          scene={selectedScene}
          visible={!!selectedScene}
          onClose={handleCloseModal}
        />
      )}
    </div>
  );
};

export default SceneBrowser;
