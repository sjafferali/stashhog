import React, { useState } from 'react'
import { 
  Button, 
  Dropdown, 
  Menu, 
  Space, 
  Modal, 
  InputNumber, 
  Select,
  Tooltip,
  Badge
} from 'antd'
import { 
  CheckCircleOutlined,
  CloseCircleOutlined,
  ThunderboltOutlined,
  FilterOutlined,
  TagsOutlined,
  UserOutlined,
  HomeOutlined,
  FileTextOutlined,
  CalendarOutlined
} from '@ant-design/icons'

export interface BulkActionsProps {
  totalChanges: number
  acceptedChanges: number
  rejectedChanges: number
  pendingChanges: number
  onAcceptAll: () => void
  onRejectAll: () => void
  onAcceptByConfidence: (threshold: number) => void
  onAcceptByField: (field: string) => void
  onRejectByField: (field: string) => void
  fieldCounts: {
    title: number
    performers: number
    tags: number
    studio: number
    details: number
    date: number
  }
}

const BulkActions: React.FC<BulkActionsProps> = ({
  totalChanges,
  acceptedChanges,
  rejectedChanges,
  pendingChanges,
  onAcceptAll,
  onRejectAll,
  onAcceptByConfidence,
  onAcceptByField,
  onRejectByField,
  fieldCounts
}) => {
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.8)

  const fieldIcons = {
    title: <FileTextOutlined />,
    performers: <UserOutlined />,
    tags: <TagsOutlined />,
    studio: <HomeOutlined />,
    details: <FileTextOutlined />,
    date: <CalendarOutlined />
  }

  const fieldLabels = {
    title: 'Title',
    performers: 'Performers',
    tags: 'Tags',
    studio: 'Studio',
    details: 'Details',
    date: 'Date'
  }

  const handleAcceptByConfidence = () => {
    Modal.confirm({
      title: 'Accept High Confidence Changes',
      content: (
        <div>
          <p>Set minimum confidence threshold:</p>
          <InputNumber
            min={0}
            max={1}
            step={0.1}
            value={confidenceThreshold}
            onChange={val => setConfidenceThreshold(val || 0.8)}
            formatter={value => `${(value as number * 100).toFixed(0)}%`}
            parser={value => parseInt(value!.replace('%', '')) / 100}
            style={{ width: '100%' }}
          />
          <p style={{ marginTop: 8, color: '#666' }}>
            This will accept all pending changes with confidence ≥ {(confidenceThreshold * 100).toFixed(0)}%
          </p>
        </div>
      ),
      onOk: () => onAcceptByConfidence(confidenceThreshold)
    })
  }

  const acceptByFieldMenu = (
    <Menu>
      {Object.entries(fieldCounts).map(([field, count]) => (
        <Menu.Item 
          key={field}
          icon={fieldIcons[field as keyof typeof fieldIcons]}
          onClick={() => onAcceptByField(field)}
          disabled={count === 0}
        >
          {fieldLabels[field as keyof typeof fieldLabels]}
          <Badge 
            count={count} 
            style={{ marginLeft: 8 }}
            showZero
          />
        </Menu.Item>
      ))}
    </Menu>
  )

  const rejectByFieldMenu = (
    <Menu>
      {Object.entries(fieldCounts).map(([field, count]) => (
        <Menu.Item 
          key={field}
          icon={fieldIcons[field as keyof typeof fieldIcons]}
          onClick={() => onRejectByField(field)}
          disabled={count === 0}
        >
          {fieldLabels[field as keyof typeof fieldLabels]}
          <Badge 
            count={count} 
            style={{ marginLeft: 8 }}
            showZero
          />
        </Menu.Item>
      ))}
    </Menu>
  )

  const mainMenu = (
    <Menu>
      <Menu.ItemGroup title="Accept Actions">
        <Menu.Item 
          key="accept-all"
          icon={<CheckCircleOutlined />}
          onClick={onAcceptAll}
          disabled={pendingChanges === 0}
        >
          Accept All Pending ({pendingChanges})
        </Menu.Item>
        <Menu.Item 
          key="accept-confidence"
          icon={<ThunderboltOutlined />}
          onClick={handleAcceptByConfidence}
          disabled={pendingChanges === 0}
        >
          Accept by Confidence
        </Menu.Item>
        <Menu.SubMenu 
          key="accept-field" 
          title="Accept by Field" 
          icon={<FilterOutlined />}
          disabled={pendingChanges === 0}
        >
          {Object.entries(fieldCounts).map(([field, count]) => (
            <Menu.Item 
              key={field}
              icon={fieldIcons[field as keyof typeof fieldIcons]}
              onClick={() => onAcceptByField(field)}
              disabled={count === 0}
            >
              {fieldLabels[field as keyof typeof fieldLabels]}
              <Badge 
                count={count} 
                style={{ marginLeft: 8 }}
                showZero
              />
            </Menu.Item>
          ))}
        </Menu.SubMenu>
      </Menu.ItemGroup>
      
      <Menu.Divider />
      
      <Menu.ItemGroup title="Reject Actions">
        <Menu.Item 
          key="reject-all"
          icon={<CloseCircleOutlined />}
          onClick={onRejectAll}
          disabled={pendingChanges === 0}
        >
          Reject All Pending ({pendingChanges})
        </Menu.Item>
        <Menu.SubMenu 
          key="reject-field" 
          title="Reject by Field" 
          icon={<FilterOutlined />}
          disabled={pendingChanges === 0}
        >
          {Object.entries(fieldCounts).map(([field, count]) => (
            <Menu.Item 
              key={field}
              icon={fieldIcons[field as keyof typeof fieldIcons]}
              onClick={() => onRejectByField(field)}
              disabled={count === 0}
            >
              {fieldLabels[field as keyof typeof fieldLabels]}
              <Badge 
                count={count} 
                style={{ marginLeft: 8 }}
                showZero
              />
            </Menu.Item>
          ))}
        </Menu.SubMenu>
      </Menu.ItemGroup>
    </Menu>
  )

  return (
    <Space>
      <Dropdown overlay={mainMenu} placement="bottomRight">
        <Button type="primary">
          Bulk Actions
          <Badge 
            count={pendingChanges} 
            style={{ marginLeft: 8 }}
          />
        </Button>
      </Dropdown>
      
      <Tooltip title="Quick accept all pending changes">
        <Button 
          icon={<CheckCircleOutlined />}
          onClick={onAcceptAll}
          disabled={pendingChanges === 0}
        >
          Accept All
        </Button>
      </Tooltip>
      
      <Tooltip title="Quick reject all pending changes">
        <Button 
          icon={<CloseCircleOutlined />}
          onClick={onRejectAll}
          disabled={pendingChanges === 0}
          danger
        >
          Reject All
        </Button>
      </Tooltip>
    </Space>
  )
}

export default BulkActions