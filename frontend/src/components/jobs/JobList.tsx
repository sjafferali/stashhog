import React, { useState, useEffect } from 'react';
import { 
  List, 
  Space, 
  Button, 
  Select, 
  Tag,
  Empty,
  Pagination,
  Spin,
  Input,
  DatePicker
} from 'antd';
import { 
  FilterOutlined, 
  ReloadOutlined,
  SortAscendingOutlined,
  SortDescendingOutlined,
  SearchOutlined
} from '@ant-design/icons';
import { Job } from '@/types/models';
import { JobCard } from './JobCard';
import { LoadingSpinner } from '../common';
import styles from './JobList.module.scss';

const { RangePicker } = DatePicker;

export interface JobListProps {
  jobs: Job[];
  onJobClick?: (job: Job) => void;
  showFilters?: boolean;
  autoRefresh?: boolean;
  refreshInterval?: number;
  loading?: boolean;
  onRefresh?: () => void;
  onCancel?: (jobId: string) => void;
  onRetry?: (jobId: string) => void;
  onDelete?: (jobId: string) => void;
  pageSize?: number;
}

interface JobFilters {
  status?: string[];
  type?: string[];
  search?: string;
  dateRange?: [Date, Date];
}

export const JobList: React.FC<JobListProps> = ({
  jobs,
  onJobClick,
  showFilters = true,
  autoRefresh = true,
  refreshInterval = 5000,
  loading = false,
  onRefresh,
  onCancel,
  onRetry,
  onDelete,
  pageSize = 10,
}) => {
  const [filters, setFilters] = useState<JobFilters>({});
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [sortBy, setSortBy] = useState<'created_at' | 'updated_at'>('created_at');
  const [currentPage, setCurrentPage] = useState(1);
  const [showActiveFilters, setShowActiveFilters] = useState(false);

  useEffect(() => {
    if (autoRefresh && onRefresh) {
      const interval = setInterval(() => {
        const hasRunningJobs = jobs.some(job => job.status === 'running' || job.status === 'pending');
        if (hasRunningJobs) {
          onRefresh();
        }
      }, refreshInterval);

      return () => clearInterval(interval);
    }
  }, [autoRefresh, refreshInterval, onRefresh, jobs]);

  const handleFilterChange = (key: keyof JobFilters, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setCurrentPage(1);
  };

  const clearFilters = () => {
    setFilters({});
    setCurrentPage(1);
  };

  const toggleSortOrder = () => {
    setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc');
  };

  const filteredJobs = jobs.filter(job => {
    if (filters.status && filters.status.length > 0) {
      if (!filters.status.includes(job.status)) return false;
    }
    
    if (filters.type && filters.type.length > 0) {
      if (!filters.type.includes(job.type)) return false;
    }
    
    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      if (!job.name.toLowerCase().includes(searchLower)) return false;
    }
    
    if (filters.dateRange) {
      const jobDate = new Date(job.created_at);
      if (jobDate < filters.dateRange[0] || jobDate > filters.dateRange[1]) return false;
    }
    
    return true;
  });

  const sortedJobs = [...filteredJobs].sort((a, b) => {
    const dateA = new Date(sortBy === 'created_at' ? a.created_at : a.updated_at || a.created_at).getTime();
    const dateB = new Date(sortBy === 'created_at' ? b.created_at : b.updated_at || b.created_at).getTime();
    
    return sortOrder === 'asc' ? dateA - dateB : dateB - dateA;
  });

  const paginatedJobs = sortedJobs.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  const activeFilterCount = Object.values(filters).filter(v => 
    v !== undefined && (Array.isArray(v) ? v.length > 0 : true)
  ).length;

  const statusOptions = [
    { label: 'Pending', value: 'pending', color: 'default' },
    { label: 'Running', value: 'running', color: 'processing' },
    { label: 'Completed', value: 'completed', color: 'success' },
    { label: 'Failed', value: 'failed', color: 'error' },
    { label: 'Cancelled', value: 'cancelled', color: 'warning' },
  ];

  const typeOptions = [
    { label: 'Synchronization', value: 'sync' },
    { label: 'Scene Analysis', value: 'analysis' },
    { label: 'Batch Analysis', value: 'batch_analysis' },
  ];

  if (loading && jobs.length === 0) {
    return <LoadingSpinner />;
  }

  return (
    <div className={styles.jobList}>
      {showFilters && (
        <div className={styles.toolbar}>
          <Space wrap>
            <Input
              prefix={<SearchOutlined />}
              placeholder="Search jobs..."
              value={filters.search}
              onChange={(e) => handleFilterChange('search', e.target.value)}
              style={{ width: 200 }}
              allowClear
            />
            
            <Select
              mode="multiple"
              placeholder="Filter by status"
              value={filters.status}
              onChange={(value) => handleFilterChange('status', value)}
              style={{ minWidth: 150 }}
            >
              {statusOptions.map(option => (
                <Select.Option key={option.value} value={option.value}>
                  <Tag color={option.color}>{option.label}</Tag>
                </Select.Option>
              ))}
            </Select>
            
            <Select
              mode="multiple"
              placeholder="Filter by type"
              value={filters.type}
              onChange={(value) => handleFilterChange('type', value)}
              style={{ minWidth: 150 }}
            >
              {typeOptions.map(option => (
                <Select.Option key={option.value} value={option.value}>
                  {option.label}
                </Select.Option>
              ))}
            </Select>
            
            <RangePicker
              value={filters.dateRange as any}
              onChange={(dates) => handleFilterChange('dateRange', dates as [Date, Date])}
              style={{ width: 240 }}
            />
            
            {activeFilterCount > 0 && (
              <Button onClick={clearFilters}>
                Clear Filters ({activeFilterCount})
              </Button>
            )}
          </Space>
          
          <Space>
            <Select
              value={sortBy}
              onChange={setSortBy}
              style={{ width: 120 }}
            >
              <Select.Option value="created_at">Created</Select.Option>
              <Select.Option value="updated_at">Updated</Select.Option>
            </Select>
            
            <Button
              icon={sortOrder === 'asc' ? <SortAscendingOutlined /> : <SortDescendingOutlined />}
              onClick={toggleSortOrder}
            >
              {sortOrder === 'asc' ? 'Oldest First' : 'Newest First'}
            </Button>
            
            {onRefresh && (
              <Button
                icon={<ReloadOutlined />}
                onClick={onRefresh}
                loading={loading}
              >
                Refresh
              </Button>
            )}
          </Space>
        </div>
      )}

      {paginatedJobs.length === 0 ? (
        <Empty
          description={filters.search || activeFilterCount > 0 ? "No jobs match your filters" : "No jobs found"}
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      ) : (
        <>
          <List
            className={styles.list}
            loading={loading}
            dataSource={paginatedJobs}
            renderItem={(job) => (
              <JobCard
                key={job.id}
                job={job}
                onCancel={onCancel ? () => onCancel(job.id) : undefined}
                onRetry={onRetry ? () => onRetry(job.id) : undefined}
                onDelete={onDelete ? () => onDelete(job.id) : undefined}
              />
            )}
          />
          
          {filteredJobs.length > pageSize && (
            <Pagination
              current={currentPage}
              total={filteredJobs.length}
              pageSize={pageSize}
              onChange={setCurrentPage}
              showSizeChanger={false}
              showTotal={(total, range) => `${range[0]}-${range[1]} of ${total} jobs`}
              className={styles.pagination}
            />
          )}
        </>
      )}
    </div>
  );
};