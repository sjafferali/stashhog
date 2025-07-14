import React, { useState, useCallback } from 'react';
import { Box, Container, Stack, IconButton, Tooltip, Typography } from '@mui/material';
import { GridView as GridViewIcon, ViewList as ListViewIcon } from '@mui/icons-material';
import { useSearchParams } from 'react-router-dom';
import { useSceneFilters } from './hooks/useSceneFilters';
import { SearchBar } from './components/SearchBar';
import { AdvancedFilters } from './components/AdvancedFilters';
import { SceneListContainer } from './components/SceneListContainer';
import { SceneActions } from './components/SceneActions';
import { SyncButton } from './components/SyncButton';
import { SceneDetailModal } from './components/SceneDetailModal';
import { Scene } from '../../types/api';
import { useScenesStore } from '../../store/slices/scenes';

export function ScenesPage() {
  const [searchParams] = useSearchParams();
  const filters = useSceneFilters();
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [selectedScene, setSelectedScene] = useState<Scene | null>(null);
  
  const { viewMode, setViewMode, selectedScenes, clearSelection } = useScenesStore();

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
    <Container maxWidth={false} sx={{ py: 3 }}>
      <Stack spacing={3}>
        {/* Header */}
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h4" component="h1">
            Scenes
          </Typography>
          <Stack direction="row" spacing={1}>
            <SyncButton />
            <Tooltip title={viewMode === 'grid' ? 'List view' : 'Grid view'}>
              <IconButton onClick={toggleViewMode}>
                {viewMode === 'grid' ? <ListViewIcon /> : <GridViewIcon />}
              </IconButton>
            </Tooltip>
          </Stack>
        </Box>

        {/* Search Bar */}
        <SearchBar 
          onToggleAdvancedFilters={handleToggleFilters}
          showingAdvancedFilters={showAdvancedFilters}
        />

        {/* Advanced Filters */}
        {showAdvancedFilters && (
          <AdvancedFilters filters={filters} />
        )}

        {/* Bulk Actions */}
        {selectedScenes.size > 0 && (
          <SceneActions 
            selectedCount={selectedScenes.size}
            onClearSelection={clearSelection}
          />
        )}

        {/* Scene List */}
        <SceneListContainer
          filters={filters}
          viewMode={viewMode}
          onSceneSelect={handleSceneSelect}
        />
      </Stack>

      {/* Scene Detail Modal */}
      {selectedScene && (
        <SceneDetailModal
          scene={selectedScene}
          open={!!selectedScene}
          onClose={handleCloseModal}
        />
      )}
    </Container>
  );
}