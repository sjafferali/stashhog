import React from 'react';
import { Card, Statistic, Row, Col, Divider, Typography } from 'antd';
import {
  UserOutlined,
  TagsOutlined,
  HomeOutlined,
  FileTextOutlined,
  EditOutlined,
  FileSearchOutlined,
} from '@ant-design/icons';

const { Text } = Typography;

export interface AnalysisJobResultData {
  plan_id: string;
  total_changes: number;
  scenes_analyzed: number;
  summary: {
    performers_to_add?: number;
    tags_to_add?: number;
    studios_to_set?: number;
    titles_to_update?: number;
    details_to_update?: number;
    scenes_with_detail_changes?: number;
  };
}

interface Props {
  result: AnalysisJobResultData;
}

export const AnalysisJobResult: React.FC<Props> = ({ result }) => {
  const { summary } = result;

  return (
    <div>
      <Row gutter={[16, 16]}>
        <Col span={8}>
          <Statistic
            title="Scenes Analyzed"
            value={result.scenes_analyzed}
            prefix={<FileSearchOutlined />}
          />
        </Col>
        <Col span={8}>
          <Statistic
            title="Total Changes"
            value={result.total_changes}
            prefix={<EditOutlined />}
          />
        </Col>
        <Col span={8}>
          <Statistic
            title="Plan ID"
            value={result.plan_id}
            valueStyle={{ fontSize: 14 }}
          />
        </Col>
      </Row>

      {summary && (
        <>
          <Divider>Changes Summary</Divider>
          <Row gutter={[16, 16]}>
            {summary.performers_to_add !== undefined &&
              summary.performers_to_add > 0 && (
                <Col span={8}>
                  <Card size="small" bordered={false}>
                    <Statistic
                      title="Performers to Add"
                      value={summary.performers_to_add}
                      prefix={<UserOutlined />}
                      valueStyle={{ color: '#3f8600' }}
                    />
                  </Card>
                </Col>
              )}

            {summary.tags_to_add !== undefined && summary.tags_to_add > 0 && (
              <Col span={8}>
                <Card size="small" bordered={false}>
                  <Statistic
                    title="Tags to Add"
                    value={summary.tags_to_add}
                    prefix={<TagsOutlined />}
                    valueStyle={{ color: '#3f8600' }}
                  />
                </Card>
              </Col>
            )}

            {summary.studios_to_set !== undefined &&
              summary.studios_to_set > 0 && (
                <Col span={8}>
                  <Card size="small" bordered={false}>
                    <Statistic
                      title="Studios to Set"
                      value={summary.studios_to_set}
                      prefix={<HomeOutlined />}
                      valueStyle={{ color: '#3f8600' }}
                    />
                  </Card>
                </Col>
              )}

            {summary.titles_to_update !== undefined &&
              summary.titles_to_update > 0 && (
                <Col span={8}>
                  <Card size="small" bordered={false}>
                    <Statistic
                      title="Titles to Update"
                      value={summary.titles_to_update}
                      prefix={<FileTextOutlined />}
                      valueStyle={{ color: '#1890ff' }}
                    />
                  </Card>
                </Col>
              )}

            {summary.scenes_with_detail_changes !== undefined &&
              summary.scenes_with_detail_changes > 0 && (
                <Col span={8}>
                  <Card size="small" bordered={false}>
                    <Statistic
                      title="Scenes with Detail Changes"
                      value={summary.scenes_with_detail_changes}
                      prefix={<FileTextOutlined />}
                      valueStyle={{ color: '#1890ff' }}
                    />
                    {summary.details_to_update !== undefined &&
                      summary.details_to_update >
                        summary.scenes_with_detail_changes && (
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          ({summary.details_to_update} total detail changes)
                        </Text>
                      )}
                  </Card>
                </Col>
              )}
          </Row>
        </>
      )}
    </div>
  );
};
