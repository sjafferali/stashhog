import React, { useState, MouseEvent } from 'react';
import {
  List,
  Card,
  Tag,
  Space,
  Button,
  Typography,
  Switch,
  Popconfirm,
  Row,
  Col,
  Tooltip,
  Badge,
} from 'antd';
import {
  PlayCircleOutlined,
  EditOutlined,
  DeleteOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { Schedule } from '../types';
import { useSchedules } from '../hooks/useSchedules';
import ScheduleDetail from './ScheduleDetail';
import cronstrue from 'cronstrue';

const { Text, Paragraph } = Typography;

interface ScheduleListProps {
  schedules: Schedule[];
  onScheduleClick?: (schedule: Schedule) => void;
  onRefresh?: () => void;
}

const ScheduleList: React.FC<ScheduleListProps> = ({
  schedules,
  onScheduleClick,
  onRefresh,
}) => {
  const [selectedSchedule, setSelectedSchedule] = useState<Schedule | null>(
    null
  );
  const [detailVisible, setDetailVisible] = useState(false);
  const { toggleSchedule, deleteSchedule, runScheduleNow } = useSchedules();

  const handleToggle = async (schedule: Schedule) => {
    await toggleSchedule(schedule.id, !schedule.enabled);
    onRefresh?.();
  };

  const handleDelete = async (id: number) => {
    await deleteSchedule(id);
    onRefresh?.();
  };

  const handleRunNow = async (id: number) => {
    await runScheduleNow(id);
  };

  const handleDetailClick = (schedule: Schedule) => {
    setSelectedSchedule(schedule);
    setDetailVisible(true);
  };

  const getTaskTypeColor = (type: string) => {
    switch (type) {
      case 'sync':
        return 'blue';
      case 'analysis':
        return 'green';
      case 'cleanup':
        return 'orange';
      default:
        return 'default';
    }
  };

  const getStatusIcon = (schedule: Schedule) => {
    if (!schedule.enabled) {
      return <ExclamationCircleOutlined style={{ color: '#bfbfbf' }} />;
    }
    if (schedule.last_run) {
      // Check if last run was successful (this would come from the run history)
      return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
    }
    return <ClockCircleOutlined style={{ color: '#1890ff' }} />;
  };

  const getCronDescription = (expression: string) => {
    try {
      return cronstrue.toString(expression);
    } catch {
      return expression;
    }
  };

  return (
    <>
      <List
        grid={{ gutter: 16, xs: 1, sm: 1, md: 2, lg: 2, xl: 3, xxl: 3 }}
        dataSource={schedules}
        renderItem={(schedule) => (
          <List.Item>
            <Badge.Ribbon
              text={schedule.enabled ? 'Active' : 'Inactive'}
              color={schedule.enabled ? 'green' : 'gray'}
            >
              <Card
                hoverable
                onClick={() => onScheduleClick?.(schedule)}
                actions={[
                  <Tooltip key="run" title="Run now">
                    <Button
                      type="text"
                      icon={<PlayCircleOutlined />}
                      onClick={(e: MouseEvent<HTMLElement>) => {
                        e.stopPropagation();
                        void handleRunNow(schedule.id);
                      }}
                      disabled={!schedule.enabled}
                    />
                  </Tooltip>,
                  <Tooltip key="edit" title="View details">
                    <Button
                      type="text"
                      icon={<EditOutlined />}
                      onClick={(e: MouseEvent<HTMLElement>) => {
                        e.stopPropagation();
                        handleDetailClick(schedule);
                      }}
                    />
                  </Tooltip>,
                  <Popconfirm
                    key="delete"
                    title="Delete Schedule"
                    description="Are you sure you want to delete this schedule?"
                    onConfirm={(e?: MouseEvent<HTMLElement>) => {
                      e?.stopPropagation();
                      void handleDelete(schedule.id);
                    }}
                    okText="Yes"
                    cancelText="No"
                  >
                    <Tooltip title="Delete">
                      <Button
                        type="text"
                        danger
                        icon={<DeleteOutlined />}
                        onClick={(e: React.MouseEvent) => e.stopPropagation()}
                      />
                    </Tooltip>
                  </Popconfirm>,
                ]}
              >
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Row justify="space-between" align="top">
                    <Col flex="1">
                      <Space align="start">
                        {getStatusIcon(schedule)}
                        <div>
                          <Text strong style={{ fontSize: 16 }}>
                            {schedule.name}
                          </Text>
                          {schedule.description && (
                            <Paragraph
                              ellipsis={{ rows: 2 }}
                              type="secondary"
                              style={{ marginBottom: 0, marginTop: 4 }}
                            >
                              {schedule.description}
                            </Paragraph>
                          )}
                        </div>
                      </Space>
                    </Col>
                    <Col>
                      <Switch
                        checked={schedule.enabled}
                        onChange={() => void handleToggle(schedule)}
                        onClick={(
                          _: boolean,
                          e?: MouseEvent<HTMLButtonElement>
                        ) => e?.stopPropagation?.()}
                      />
                    </Col>
                  </Row>

                  <Space>
                    <Tag color={getTaskTypeColor(schedule.task_type)}>
                      {schedule.task_type.toUpperCase()}
                    </Tag>
                  </Space>

                  <div>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      <ClockCircleOutlined />{' '}
                      {getCronDescription(schedule.schedule)}
                    </Text>
                  </div>

                  {schedule.next_run && (
                    <div>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        Next run: {new Date(schedule.next_run).toLocaleString()}
                      </Text>
                    </div>
                  )}

                  {schedule.last_run && (
                    <div>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        Last run: {new Date(schedule.last_run).toLocaleString()}
                      </Text>
                    </div>
                  )}
                </Space>
              </Card>
            </Badge.Ribbon>
          </List.Item>
        )}
      />

      {selectedSchedule && (
        <ScheduleDetail
          schedule={selectedSchedule}
          visible={detailVisible}
          onClose={() => {
            setDetailVisible(false);
            setSelectedSchedule(null);
          }}
          onUpdate={() => {
            onRefresh?.();
            setDetailVisible(false);
          }}
        />
      )}
    </>
  );
};

export default ScheduleList;
