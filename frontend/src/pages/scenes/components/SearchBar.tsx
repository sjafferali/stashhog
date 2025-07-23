import React, { useState, useEffect, useCallback, ChangeEvent } from 'react';
import { Input, Button, Space, Badge } from 'antd';
import {
  SearchOutlined,
  FilterOutlined,
  ClearOutlined,
} from '@ant-design/icons';
import { useSearchParams } from 'react-router-dom';
import { useDebounce } from '@/hooks/useDebounce';

interface SearchBarProps {
  onToggleAdvancedFilters: () => void;
  showingAdvancedFilters: boolean;
  activeFilterCount?: number;
}

export const SearchBar: React.FC<SearchBarProps> = ({
  onToggleAdvancedFilters,
  showingAdvancedFilters,
  activeFilterCount = 0,
}) => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialSearch = searchParams.get('search') || '';
  const [searchValue, setSearchValue] = useState(initialSearch);
  const debouncedSearchValue = useDebounce(searchValue, 500);

  // Update URL when debounced search value changes
  useEffect(() => {
    const params = new URLSearchParams(searchParams);

    if (debouncedSearchValue) {
      params.set('search', debouncedSearchValue);
      params.set('page', '1'); // Reset to first page on search
    } else {
      params.delete('search');
    }

    setSearchParams(params);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedSearchValue]); // Deliberately omitting searchParams and setSearchParams to avoid infinite loops

  const handleClearSearch = useCallback(() => {
    setSearchValue('');
  }, []);

  const handleClearAllFilters = useCallback(() => {
    // Clear all filter-related params but keep pagination
    const params = new URLSearchParams();
    const page = searchParams.get('page');
    const perPage = searchParams.get('per_page');

    if (page) params.set('page', page);
    if (perPage) params.set('per_page', perPage);

    setSearchParams(params);
    setSearchValue('');
  }, [searchParams, setSearchParams]);

  const hasActiveFilters = activeFilterCount > 0 || searchValue !== '';

  return (
    <div style={{ display: 'flex', gap: '8px', width: '100%' }}>
      <Input
        size="large"
        placeholder="Search scenes by title, path, or details..."
        prefix={<SearchOutlined />}
        value={searchValue}
        onChange={(e: ChangeEvent<HTMLInputElement>) =>
          setSearchValue(e.target.value)
        }
        onPressEnter={() => {
          // Force immediate search on Enter
          const params = new URLSearchParams(searchParams);
          if (searchValue) {
            params.set('search', searchValue);
            params.set('page', '1');
          } else {
            params.delete('search');
          }
          setSearchParams(params);
        }}
        suffix={
          searchValue && (
            <ClearOutlined
              onClick={handleClearSearch}
              style={{ cursor: 'pointer', color: '#999' }}
            />
          )
        }
        style={{ flex: 1 }}
      />

      <Space size="small">
        <Badge count={activeFilterCount} offset={[-2, 2]}>
          <Button
            size="large"
            icon={<FilterOutlined />}
            type={showingAdvancedFilters ? 'primary' : 'default'}
            onClick={onToggleAdvancedFilters}
          >
            Filters
          </Button>
        </Badge>

        {hasActiveFilters && (
          <Button
            size="large"
            icon={<ClearOutlined />}
            onClick={handleClearAllFilters}
            danger
          >
            Clear All
          </Button>
        )}
      </Space>
    </div>
  );
};
