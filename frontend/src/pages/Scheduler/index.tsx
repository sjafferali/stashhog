import React, { useState } from 'react';
import {
  Card,
  Tabs,
  Button,
  Space,
  Typography,
  Row,
  Col,
  Statistic,
  Spin,
  Empty,
} from 'antd';
import {
  PlusOutlined,
  CalendarOutlined,
  HistoryOutlined,
  ClockCircleOutlined,
  PlayCircleOutlined,
} from '@ant-design/icons';
import ScheduleList from './components/ScheduleList';
import CreateScheduleModal from './components/CreateScheduleModal';
import CalendarView from './components/CalendarView';
import RunHistory from './components/RunHistory';
import { useSchedules, useScheduleHistory } from './hooks/useSchedules';
import { Schedule } from './types';
import { useNavigate } from 'react-router-dom';

const { Title } = Typography;
const { TabPane } = Tabs;

const Scheduler: React.FC = () => {
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [selectedSchedule, setSelectedSchedule] = useState<Schedule | null>(
    null
  );
  const [activeTab, setActiveTab] = useState('schedules');

  const navigate = useNavigate();
  const { schedules, loading, refetch } = useSchedules();
  const { runs, stats } = useScheduleHistory();

  const activeSchedules = schedules.filter((s) => s.enabled);
  const upcomingRuns = schedules
    .filter((s) => s.enabled && s.next_run)
    .sort(
      (a, b) =>
        new Date(a.next_run!).getTime() - new Date(b.next_run!).getTime()
    )
    .slice(0, 5);

  const handleCreateSuccess = () => {
    setCreateModalVisible(false);
    void refetch();
  };

  const handleScheduleSelect = (schedule: Schedule) => {
    setSelectedSchedule(schedule);
    setActiveTab('history');
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div style={{ padding: '24px' }}>
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={2}>Task Scheduler</Title>
        </Col>
        <Col>
          <Space>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setCreateModalVisible(true)}
              size="large"
            >
              Create Schedule
            </Button>
            <Button
              icon={<PlayCircleOutlined />}
              onClick={() => void navigate('/jobs/run')}
              size="large"
            >
              Run Job Now
            </Button>
          </Space>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Total Schedules"
              value={schedules.length}
              prefix={<CalendarOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Active Schedules"
              value={activeSchedules.length}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Total Runs Today"
              value={
                runs.filter((r) => {
                  const runDate = new Date(r.started_at);
                  const today = new Date();
                  return runDate.toDateString() === today.toDateString();
                }).length
              }
              prefix={<HistoryOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Success Rate"
              value={
                stats
                  ? Math.round((stats.successful_runs / stats.total_runs) * 100)
                  : 0
              }
              suffix="%"
              valueStyle={{
                color:
                  stats && stats.successful_runs / stats.total_runs > 0.9
                    ? '#52c41a'
                    : '#faad14',
              }}
            />
          </Card>
        </Col>
      </Row>

      <Card>
        <Tabs activeKey={activeTab} onChange={setActiveTab} size="large">
          <TabPane tab="Schedules" key="schedules">
            {schedules.length === 0 ? (
              <Empty
                description="No schedules created yet"
                style={{ padding: '40px 0' }}
              >
                <Button
                  type="primary"
                  onClick={() => setCreateModalVisible(true)}
                >
                  Create Your First Schedule
                </Button>
              </Empty>
            ) : (
              <ScheduleList
                schedules={schedules}
                onScheduleClick={handleScheduleSelect}
                onRefresh={() => void refetch()}
              />
            )}
          </TabPane>

          <TabPane tab="Calendar" key="calendar">
            <CalendarView
              schedules={schedules}
              runs={runs}
              onScheduleClick={handleScheduleSelect}
            />
          </TabPane>

          <TabPane tab="History" key="history">
            <RunHistory
              scheduleId={selectedSchedule?.id}
              onScheduleSelect={setSelectedSchedule}
              schedules={schedules}
            />
          </TabPane>

          <TabPane tab="Upcoming" key="upcoming">
            <Card title="Next Scheduled Runs" bordered={false}>
              {upcomingRuns.length === 0 ? (
                <Empty description="No upcoming runs" />
              ) : (
                <Space direction="vertical" style={{ width: '100%' }}>
                  {upcomingRuns.map((schedule) => (
                    <Card
                      key={schedule.id}
                      size="small"
                      hoverable
                      onClick={() => handleScheduleSelect(schedule)}
                    >
                      <Row justify="space-between" align="middle">
                        <Col>
                          <Space direction="vertical" size={0}>
                            <Typography.Text strong>
                              {schedule.name}
                            </Typography.Text>
                            <Typography.Text type="secondary">
                              {schedule.task_type}
                            </Typography.Text>
                          </Space>
                        </Col>
                        <Col>
                          <Typography.Text>
                            {new Date(schedule.next_run!).toLocaleString()}
                          </Typography.Text>
                        </Col>
                      </Row>
                    </Card>
                  ))}
                </Space>
              )}
            </Card>
          </TabPane>
        </Tabs>
      </Card>

      <CreateScheduleModal
        visible={createModalVisible}
        onClose={() => setCreateModalVisible(false)}
        onSuccess={handleCreateSuccess}
      />
    </div>
  );
};

export default Scheduler;
