import React, { useState, useRef, useEffect } from 'react'
import { Input, Select, DatePicker, Tag, Space, Button } from 'antd'
import { CheckOutlined, CloseOutlined, PlusOutlined } from '@ant-design/icons'
import moment from 'moment'
import './InlineEditor.scss'

const { TextArea } = Input

export interface InlineEditorProps {
  value: any
  type: 'text' | 'textarea' | 'array' | 'date' | 'number' | 'object'
  onSave: (value: any) => void
  onCancel: () => void
  placeholder?: string
  options?: Array<{ label: string; value: any }>
  validator?: (value: any) => boolean | string
}

const InlineEditor: React.FC<InlineEditorProps> = ({
  value,
  type,
  onSave,
  onCancel,
  placeholder,
  options,
  validator
}) => {
  const [editValue, setEditValue] = useState<any>(value)
  const [arrayInput, setArrayInput] = useState('')
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<any>(null)

  useEffect(() => {
    // Focus input on mount
    setTimeout(() => {
      inputRef.current?.focus()
    }, 100)
  }, [])

  const handleSave = () => {
    // Validate if validator provided
    if (validator) {
      const validationResult = validator(editValue)
      if (validationResult !== true) {
        setError(typeof validationResult === 'string' ? validationResult : 'Invalid value')
        return
      }
    }

    onSave(editValue)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey && type !== 'textarea') {
      e.preventDefault()
      handleSave()
    } else if (e.key === 'Escape') {
      onCancel()
    }
  }

  // Render array editor
  if (type === 'array') {
    const items = Array.isArray(editValue) ? editValue : []

    return (
      <div className="inline-editor array-editor">
        <Space direction="vertical" style={{ width: '100%' }}>
          <div className="array-items">
            {items.map((item, index) => (
              <Tag
                key={index}
                closable
                onClose={() => {
                  const newItems = [...items]
                  newItems.splice(index, 1)
                  setEditValue(newItems)
                }}
              >
                {item}
              </Tag>
            ))}
          </div>
          
          <Space.Compact style={{ width: '100%' }}>
            <Input
              ref={inputRef}
              value={arrayInput}
              onChange={e => setArrayInput(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && arrayInput.trim()) {
                  e.preventDefault()
                  setEditValue([...items, arrayInput.trim()])
                  setArrayInput('')
                } else if (e.key === 'Escape') {
                  onCancel()
                }
              }}
              placeholder="Add item..."
            />
            <Button
              icon={<PlusOutlined />}
              onClick={() => {
                if (arrayInput.trim()) {
                  setEditValue([...items, arrayInput.trim()])
                  setArrayInput('')
                }
              }}
            />
          </Space.Compact>
          
          <Space>
            <Button
              type="primary"
              size="small"
              icon={<CheckOutlined />}
              onClick={handleSave}
            >
              Save
            </Button>
            <Button
              size="small"
              icon={<CloseOutlined />}
              onClick={onCancel}
            >
              Cancel
            </Button>
          </Space>
        </Space>
      </div>
    )
  }

  // Render date editor
  if (type === 'date') {
    return (
      <div className="inline-editor date-editor">
        <Space>
          <DatePicker
            ref={inputRef}
            value={editValue ? moment(editValue) : null}
            onChange={date => setEditValue(date?.toISOString())}
            format="YYYY-MM-DD"
          />
          <Button
            type="primary"
            size="small"
            icon={<CheckOutlined />}
            onClick={handleSave}
          />
          <Button
            size="small"
            icon={<CloseOutlined />}
            onClick={onCancel}
          />
        </Space>
      </div>
    )
  }

  // Render select editor (for options)
  if (options && options.length > 0) {
    return (
      <div className="inline-editor select-editor">
        <Space.Compact style={{ width: '100%' }}>
          <Select
            ref={inputRef}
            value={editValue}
            onChange={setEditValue}
            style={{ width: '100%' }}
            placeholder={placeholder}
            onKeyDown={handleKeyDown}
          >
            {options.map(opt => (
              <Select.Option key={opt.value} value={opt.value}>
                {opt.label}
              </Select.Option>
            ))}
          </Select>
          <Button
            type="primary"
            icon={<CheckOutlined />}
            onClick={handleSave}
          />
          <Button
            icon={<CloseOutlined />}
            onClick={onCancel}
          />
        </Space.Compact>
      </div>
    )
  }

  // Render textarea editor
  if (type === 'textarea') {
    return (
      <div className="inline-editor textarea-editor">
        <TextArea
          ref={inputRef}
          value={editValue}
          onChange={e => setEditValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          autoSize={{ minRows: 2, maxRows: 6 }}
          status={error ? 'error' : undefined}
        />
        {error && <div className="error-message">{error}</div>}
        <Space style={{ marginTop: 8 }}>
          <Button
            type="primary"
            size="small"
            icon={<CheckOutlined />}
            onClick={handleSave}
          >
            Save
          </Button>
          <Button
            size="small"
            icon={<CloseOutlined />}
            onClick={onCancel}
          >
            Cancel
          </Button>
        </Space>
      </div>
    )
  }

  // Render number editor
  if (type === 'number') {
    return (
      <div className="inline-editor number-editor">
        <Space.Compact>
          <Input
            ref={inputRef}
            type="number"
            value={editValue}
            onChange={e => setEditValue(parseFloat(e.target.value) || 0)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            status={error ? 'error' : undefined}
          />
          <Button
            type="primary"
            icon={<CheckOutlined />}
            onClick={handleSave}
          />
          <Button
            icon={<CloseOutlined />}
            onClick={onCancel}
          />
        </Space.Compact>
        {error && <div className="error-message">{error}</div>}
      </div>
    )
  }

  // Default text editor
  return (
    <div className="inline-editor text-editor">
      <Space.Compact style={{ width: '100%' }}>
        <Input
          ref={inputRef}
          value={editValue}
          onChange={e => setEditValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          status={error ? 'error' : undefined}
        />
        <Button
          type="primary"
          icon={<CheckOutlined />}
          onClick={handleSave}
        />
        <Button
          icon={<CloseOutlined />}
          onClick={onCancel}
        />
      </Space.Compact>
      {error && <div className="error-message">{error}</div>}
    </div>
  )
}

export default InlineEditor