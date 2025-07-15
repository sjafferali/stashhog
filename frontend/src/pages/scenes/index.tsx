import { useState, useCallback } from 'react';
import {
  // Space,
  // Button,
  Typography,
  Tooltip,
} from 'antd';
import { AppstoreOutlined, UnorderedListOutlined } from '@ant-design/icons';
// import { useSearchParams } from 'react-router-dom';
// import { useSceneFilters } from './hooks/useSceneFilters';
import { SearchBar } from './components/SearchBar';
import { AdvancedFilters } from './components/AdvancedFilters';
import { SceneListContainer } from './components/SceneListContainer';
import { SceneActions } from './components/SceneActions';
import { SyncButton } from './components/SyncButton';
import { SceneDetailModal } from './components/SceneDetailModal';
import { Scene } from '../../types/models';
import { useScenesStore } from '../../store/slices/scenes';

type ViewMode = 'grid' | 'list';

export function ScenesPage() {
  // const [searchParams] = useSearchParams();
  // const filters = useSceneFilters();
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [selectedScene, setSelectedScene] = useState<Scene | null>(null);

  const { selectedScenes, clearSelection } = useScenesStore();
  const [viewMode, setViewMode] = useState<ViewMode>('grid');

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

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        {/* Header */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <Typography.Title level={2}>Scenes</Typography.Title>
          <div style={{ display: 'flex', gap: '8px' }}>
            <SyncButton />
            <Tooltip title={viewMode === 'grid' ? 'List view' : 'Grid view'}>
              <div onClick={toggleViewMode} style={{ cursor: 'pointer' }}>
                {viewMode === 'grid' ? (
                  <UnorderedListOutlined />
                ) : (
                  <AppstoreOutlined />
                )}
              </div>
            </Tooltip>
          </div>
        </div>

        {/* Search Bar */}
        <SearchBar
          onToggleAdvancedFilters={handleToggleFilters}
          showingAdvancedFilters={showAdvancedFilters}
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
        <SceneListContainer
          scenes={[]}
          viewMode={viewMode}
          onSceneSelect={handleSceneSelect}
        />
      </div>

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
}
