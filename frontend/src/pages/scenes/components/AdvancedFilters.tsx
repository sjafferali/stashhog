import React, { useState, ChangeEvent } from 'react';
import {
  Card,
  Collapse,
  Select,
  DatePicker,
  // Switch,
  Input,
  Space,
  Button,
  Tag,
  Spin,
  Row,
  Col,
} from 'antd';
import {
  UserOutlined,
  TagsOutlined,
  HomeOutlined,
  CalendarOutlined,
  FolderOutlined,
  ClearOutlined,
  CheckCircleOutlined,
  // FileTextOutlined,
} from '@ant-design/icons';
import { useQuery } from 'react-query';
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
    'performers',
    'tags',
  ]);

  // Fetch filter options
  const { data: performers, isLoading: loadingPerformers } = useQuery<
    Performer[]
  >('performers', async () => {
    const response = await api.get('/performers', { params: { size: 1000 } });
    return response.data.items;
  });

  const { data: tags, isLoading: loadingTags } = useQuery<TagType[]>(
    'tags',
    async () => {
      const response = await api.get('/tags', { params: { size: 1000 } });
      return response.data.items;
    }
  );

  const { data: studios, isLoading: loadingStudios } = useQuery<Studio[]>(
    'studios',
    async () => {
      const response = await api.get('/studios', { params: { size: 1000 } });
      return response.data.items;
    }
  );

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
          {/* Performers Filter */}
          <Panel
            header={
              <Space>
                <UserOutlined />
                Performers
                {renderFilterCount(
                  Array.isArray(filters.performers)
                    ? filters.performers.length
                    : 0
                )}
              </Space>
            }
            key="performers"
          >
            <Spin spinning={loadingPerformers}>
              <Select
                mode="multiple"
                placeholder="Select performers..."
                value={
                  Array.isArray(filters.performers) ? filters.performers : []
                }
                onChange={(value: string[]) =>
                  updateFilter('performers', value)
                }
                style={{ width: '100%' }}
                filterOption={(
                  input: string,
                  option?: { label?: React.ReactNode; value?: string }
                ) =>
                  (typeof option?.label === 'string' &&
                    option.label.toLowerCase().includes(input.toLowerCase())) ||
                  false
                }
                options={performers?.map((p) => ({
                  label: p.name,
                  value: p.id.toString(),
                }))}
                maxTagCount="responsive"
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
                  Array.isArray(filters.tags) ? filters.tags.length : 0
                )}
              </Space>
            }
            key="tags"
          >
            <Spin spinning={loadingTags}>
              <Select
                mode="multiple"
                placeholder="Select tags..."
                value={Array.isArray(filters.tags) ? filters.tags : []}
                onChange={(value: string[]) => updateFilter('tags', value)}
                style={{ width: '100%' }}
                filterOption={(
                  input: string,
                  option?: { label?: React.ReactNode; value?: string }
                ) =>
                  (typeof option?.label === 'string' &&
                    option.label.toLowerCase().includes(input.toLowerCase())) ||
                  false
                }
                options={tags?.map((t) => ({
                  label: t.name,
                  value: t.id.toString(),
                }))}
                maxTagCount="responsive"
              />
            </Spin>
          </Panel>

          {/* Studios Filter */}
          <Panel
            header={
              <Space>
                <HomeOutlined />
                Studios
                {renderFilterCount(
                  Array.isArray(filters.studios) ? filters.studios.length : 0
                )}
              </Space>
            }
            key="studios"
          >
            <Spin spinning={loadingStudios}>
              <Select
                mode="multiple"
                placeholder="Select studios..."
                value={Array.isArray(filters.studios) ? filters.studios : []}
                onChange={(value: string[]) => updateFilter('studios', value)}
                style={{ width: '100%' }}
                filterOption={(
                  input: string,
                  option?: { label?: React.ReactNode; value?: string }
                ) =>
                  (typeof option?.label === 'string' &&
                    option.label.toLowerCase().includes(input.toLowerCase())) ||
                  false
                }
                options={studios?.map((s) => ({
                  label: s.name,
                  value: s.id.toString(),
                }))}
                maxTagCount="responsive"
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
                  filters.has_details !== undefined) &&
                  renderFilterCount(
                    (filters.organized !== undefined ? 1 : 0) +
                      (filters.has_details !== undefined ? 1 : 0)
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
                  <span>Has Details:</span>
                  <Select
                    value={
                      typeof filters.has_details === 'boolean'
                        ? filters.has_details
                        : undefined
                    }
                    onChange={(value: boolean | undefined) =>
                      updateFilter('has_details', value)
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

          {/* Path Filter */}
          <Panel
            header={
              <Space>
                <FolderOutlined />
                Path Contains
                {filters.path_contains && renderFilterCount(1)}
              </Space>
            }
            key="path"
          >
            <Input
              placeholder="Filter by path..."
              value={
                typeof filters.path_contains === 'string'
                  ? filters.path_contains
                  : ''
              }
              onChange={(e: ChangeEvent<HTMLInputElement>) =>
                updateFilter('path_contains', e.target.value)
              }
              allowClear
            />
          </Panel>
        </Collapse>
      </Space>
    </Card>
  );
};
