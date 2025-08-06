import React, { useState } from 'react';
import {
  Card,
  Collapse,
  Select,
  DatePicker,
  // Switch,
  Space,
  Button,
  Tag,
  Spin,
  Row,
  Col,
  Input,
} from 'antd';
import {
  UserOutlined,
  TagsOutlined,
  HomeOutlined,
  CalendarOutlined,
  ClearOutlined,
  CheckCircleOutlined,
  NumberOutlined,
  // FileTextOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import dayjs from 'dayjs';
import api from '@/services/api';
import { useSceneFilters } from '../hooks/useSceneFilters';
import { Performer, Tag as TagType, Studio } from '@/types/models';

const { Panel } = Collapse;
const { RangePicker } = DatePicker;

export const AdvancedFilters: React.FC = () => {
  const { filters, updateFilter, updateFilters, resetFilters } =
    useSceneFilters();
  const [expandedPanels, setExpandedPanels] = useState<string[]>([
    'scene_ids',
    'performers',
    'tags',
  ]);

  // Fetch filter options
  const {
    data: performers = [],
    isLoading: loadingPerformers,
    error: performersError,
  } = useQuery<Performer[]>({
    queryKey: ['performers'],
    queryFn: async () => {
      const response = await api.get('/entities/performers');
      // The backend returns a direct array, not a paginated response
      return response.data;
    },
  });

  const {
    data: tags = [],
    isLoading: loadingTags,
    error: tagsError,
  } = useQuery<TagType[]>({
    queryKey: ['tags'],
    queryFn: async () => {
      const response = await api.get('/entities/tags');
      // The backend returns a direct array, not a paginated response
      return response.data;
    },
  });

  const {
    data: studios = [],
    isLoading: loadingStudios,
    error: studiosError,
  } = useQuery<Studio[]>({
    queryKey: ['studios'],
    queryFn: async () => {
      const response = await api.get('/entities/studios');
      // The backend returns a direct array, not a paginated response
      return response.data;
    },
  });

  const handleDateRangeChange = (
    dates: [dayjs.Dayjs | null, dayjs.Dayjs | null] | null
  ) => {
    if (dates) {
      updateFilters({
        date_from: dates[0] ? dates[0].format('YYYY-MM-DD') : '',
        date_to: dates[1] ? dates[1].format('YYYY-MM-DD') : '',
      });
    } else {
      updateFilters({
        date_from: '',
        date_to: '',
      });
    }
  };

  const dateRange =
    filters.date_from || filters.date_to
      ? [
          filters.date_from && typeof filters.date_from === 'string'
            ? dayjs(filters.date_from)
            : null,
          filters.date_to && typeof filters.date_to === 'string'
            ? dayjs(filters.date_to)
            : null,
        ]
      : null;

  const renderFilterCount = (count: number) => {
    if (count === 0) return null;
    return <Tag color="blue">{count}</Tag>;
  };

  return (
    <Card size="small">
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <h4 style={{ margin: 0 }}>Advanced Filters</h4>
          <Button
            size="small"
            icon={<ClearOutlined />}
            onClick={resetFilters}
            danger
          >
            Reset All
          </Button>
        </div>

        <Collapse
          activeKey={expandedPanels}
          onChange={(key: string | string[]) =>
            setExpandedPanels(Array.isArray(key) ? key : [key])
          }
          ghost
        >
          {/* Scene IDs Filter */}
          <Panel
            header={
              <Space>
                <NumberOutlined />
                Scene IDs
                {renderFilterCount(
                  Array.isArray(filters.scene_ids)
                    ? filters.scene_ids.length
                    : 0
                )}
              </Space>
            }
            key="scene_ids"
          >
            <Input
              placeholder="Enter comma-separated scene IDs (e.g., 123,456,789)"
              value={
                Array.isArray(filters.scene_ids)
                  ? filters.scene_ids.join(',')
                  : ''
              }
              onChange={(e) => {
                const value = e.target.value;
                if (value.trim() === '') {
                  updateFilter('scene_ids', []);
                } else {
                  const ids = value
                    .split(',')
                    .map((id) => id.trim())
                    .filter(Boolean);
                  updateFilter('scene_ids', ids);
                }
              }}
            />
          </Panel>

          {/* Performers Filter */}
          <Panel
            header={
              <Space>
                <UserOutlined />
                Performers
                {renderFilterCount(
                  Array.isArray(filters.performer_ids)
                    ? filters.performer_ids.length
                    : 0
                )}
              </Space>
            }
            key="performers"
          >
            <Spin spinning={loadingPerformers}>
              {performersError ? (
                <div style={{ color: 'red', marginBottom: 8 }}>
                  Error loading performers: {(performersError as Error).message}
                </div>
              ) : null}
              <Select
                mode="multiple"
                placeholder="Select performers..."
                value={
                  Array.isArray(filters.performer_ids)
                    ? filters.performer_ids
                    : []
                }
                onChange={(value: string[]) =>
                  updateFilter('performer_ids', value)
                }
                style={{ width: '100%' }}
                showSearch
                filterOption={(input, option) => {
                  if (!option || !option.label) return false;
                  return option.label
                    .toString()
                    .toLowerCase()
                    .includes(input.toLowerCase());
                }}
                options={
                  performers.map((p) => ({
                    label: p.name,
                    value: p.id.toString(),
                  })) as any // eslint-disable-line @typescript-eslint/no-explicit-any
                }
                maxTagCount="responsive"
                notFoundContent={
                  loadingPerformers
                    ? 'Loading...'
                    : performers.length === 0
                      ? 'No performers found'
                      : 'No matching performers'
                }
              />
            </Spin>
          </Panel>

          {/* Tags Filter */}
          <Panel
            header={
              <Space>
                <TagsOutlined />
                Tags
                {renderFilterCount(
                  (Array.isArray(filters.tag_ids)
                    ? filters.tag_ids.length
                    : 0) +
                    (Array.isArray(filters.exclude_tag_ids)
                      ? filters.exclude_tag_ids.length
                      : 0)
                )}
              </Space>
            }
            key="tags"
          >
            <Spin spinning={loadingTags}>
              {tagsError ? (
                <div style={{ color: 'red', marginBottom: 8 }}>
                  Error loading tags: {(tagsError as Error).message}
                </div>
              ) : null}
              <Space
                direction="vertical"
                style={{ width: '100%' }}
                size="middle"
              >
                <div>
                  <div style={{ marginBottom: 8, fontWeight: 500 }}>
                    Include Tags:
                  </div>
                  <Select
                    mode="multiple"
                    placeholder="Select tags to include..."
                    value={
                      Array.isArray(filters.tag_ids) ? filters.tag_ids : []
                    }
                    onChange={(value: string[]) =>
                      updateFilter('tag_ids', value)
                    }
                    style={{ width: '100%' }}
                    showSearch
                    filterOption={(input, option) => {
                      if (!option || !option.label) return false;
                      return option.label
                        .toString()
                        .toLowerCase()
                        .includes(input.toLowerCase());
                    }}
                    options={
                      tags.map((t) => ({
                        label: t.name,
                        value: t.id.toString(),
                      })) as any // eslint-disable-line @typescript-eslint/no-explicit-any
                    }
                    maxTagCount="responsive"
                    notFoundContent={
                      loadingTags
                        ? 'Loading...'
                        : tags.length === 0
                          ? 'No tags found'
                          : 'No matching tags'
                    }
                  />
                </div>
                <div>
                  <div style={{ marginBottom: 8, fontWeight: 500 }}>
                    Exclude Tags:
                  </div>
                  <Select
                    mode="multiple"
                    placeholder="Select tags to exclude..."
                    value={
                      Array.isArray(filters.exclude_tag_ids)
                        ? filters.exclude_tag_ids
                        : []
                    }
                    onChange={(value: string[]) =>
                      updateFilter('exclude_tag_ids', value)
                    }
                    style={{ width: '100%' }}
                    showSearch
                    filterOption={(input, option) => {
                      if (!option || !option.label) return false;
                      return option.label
                        .toString()
                        .toLowerCase()
                        .includes(input.toLowerCase());
                    }}
                    options={
                      tags.map((t) => ({
                        label: t.name,
                        value: t.id.toString(),
                      })) as any // eslint-disable-line @typescript-eslint/no-explicit-any
                    }
                    maxTagCount="responsive"
                    notFoundContent={
                      loadingTags
                        ? 'Loading...'
                        : tags.length === 0
                          ? 'No tags found'
                          : 'No matching tags'
                    }
                  />
                </div>
              </Space>
            </Spin>
          </Panel>

          {/* Studios Filter */}
          <Panel
            header={
              <Space>
                <HomeOutlined />
                Studios
                {renderFilterCount(filters.studio_id ? 1 : 0)}
              </Space>
            }
            key="studios"
          >
            <Spin spinning={loadingStudios}>
              {studiosError ? (
                <div style={{ color: 'red', marginBottom: 8 }}>
                  Error loading studios: {(studiosError as Error).message}
                </div>
              ) : null}
              <Select
                mode="multiple"
                placeholder="Select studios..."
                value={filters.studio_id ? [filters.studio_id.toString()] : []}
                onChange={(value: string[]) =>
                  updateFilter(
                    'studio_id',
                    value.length > 0 ? value[0] : undefined
                  )
                }
                style={{ width: '100%' }}
                showSearch
                filterOption={(input, option) => {
                  if (!option || !option.label) return false;
                  return option.label
                    .toString()
                    .toLowerCase()
                    .includes(input.toLowerCase());
                }}
                options={
                  studios.map((s) => ({
                    label: s.name,
                    value: s.id.toString(),
                  })) as any // eslint-disable-line @typescript-eslint/no-explicit-any
                }
                maxTagCount="responsive"
                notFoundContent={
                  loadingStudios
                    ? 'Loading...'
                    : studios.length === 0
                      ? 'No studios found'
                      : 'No matching studios'
                }
              />
            </Spin>
          </Panel>

          {/* Date Range Filter */}
          <Panel
            header={
              <Space>
                <CalendarOutlined />
                Date Range
                {(filters.date_from || filters.date_to) && renderFilterCount(1)}
              </Space>
            }
            key="date"
          >
            <RangePicker
              value={
                dateRange as [dayjs.Dayjs | null, dayjs.Dayjs | null] | null
              }
              onChange={handleDateRangeChange}
              style={{ width: '100%' }}
              format="YYYY-MM-DD"
            />
          </Panel>

          {/* Status Filters */}
          <Panel
            header={
              <Space>
                <CheckCircleOutlined />
                Status
                {(filters.organized !== undefined ||
                  filters.analyzed !== undefined ||
                  filters.video_analyzed !== undefined ||
                  filters.has_active_jobs !== undefined) &&
                  renderFilterCount(
                    (filters.organized !== undefined ? 1 : 0) +
                      (filters.analyzed !== undefined ? 1 : 0) +
                      (filters.video_analyzed !== undefined ? 1 : 0) +
                      (filters.has_active_jobs !== undefined ? 1 : 0)
                  )}
              </Space>
            }
            key="status"
          >
            <Row gutter={16}>
              <Col span={12}>
                <Space>
                  <span>Organized:</span>
                  <Select
                    value={
                      typeof filters.organized === 'boolean'
                        ? filters.organized
                        : undefined
                    }
                    onChange={(value: boolean | undefined) =>
                      updateFilter('organized', value)
                    }
                    style={{ width: 120 }}
                    placeholder="Any"
                    allowClear
                    options={[
                      { value: true, label: 'Yes' },
                      { value: false, label: 'No' },
                    ]}
                  />
                </Space>
              </Col>
              <Col span={12}>
                <Space>
                  <span>Analyzed:</span>
                  <Select
                    value={
                      typeof filters.analyzed === 'boolean'
                        ? filters.analyzed
                        : undefined
                    }
                    onChange={(value: boolean | undefined) =>
                      updateFilter('analyzed', value)
                    }
                    style={{ width: 120 }}
                    placeholder="Any"
                    allowClear
                    options={[
                      { value: true, label: 'Yes' },
                      { value: false, label: 'No' },
                    ]}
                  />
                </Space>
              </Col>
            </Row>
            <Row gutter={16} style={{ marginTop: 16 }}>
              <Col span={12}>
                <Space>
                  <span>Video Analyzed:</span>
                  <Select
                    value={
                      typeof filters.video_analyzed === 'boolean'
                        ? filters.video_analyzed
                        : undefined
                    }
                    onChange={(value: boolean | undefined) =>
                      updateFilter('video_analyzed', value)
                    }
                    style={{ width: 120 }}
                    placeholder="Any"
                    allowClear
                    options={[
                      { value: true, label: 'Yes' },
                      { value: false, label: 'No' },
                    ]}
                  />
                </Space>
              </Col>
              <Col span={12}>
                <Space>
                  <span>Active Jobs:</span>
                  <Select
                    value={
                      typeof filters.has_active_jobs === 'boolean'
                        ? filters.has_active_jobs
                        : undefined
                    }
                    onChange={(value: boolean | undefined) =>
                      updateFilter('has_active_jobs', value)
                    }
                    style={{ width: 120 }}
                    placeholder="Any"
                    allowClear
                    options={[
                      { value: true, label: 'Yes' },
                      { value: false, label: 'No' },
                    ]}
                  />
                </Space>
              </Col>
            </Row>
          </Panel>
        </Collapse>
      </Space>
    </Card>
  );
};
