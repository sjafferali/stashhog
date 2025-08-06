import React, {
  useState,
  useRef,
  useEffect,
  ChangeEvent,
  KeyboardEvent,
  MouseEvent,
} from 'react';
import { Input, Select, DatePicker, Tag, Space, Button } from 'antd';
import { CheckOutlined, CloseOutlined, PlusOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import apiClient from '@/services/apiClient';
import { Tag as TagType, PaginatedResponse } from '@/types/models';
import moment from 'moment';
import './InlineEditor.scss';

const { TextArea } = Input;

export interface InlineEditorProps {
  value: string | number | boolean | string[] | Date | null;
  type: 'text' | 'textarea' | 'array' | 'date' | 'number' | 'object';
  onSave: (value: string | number | boolean | string[] | Date | null) => void;
  onCancel: () => void;
  placeholder?: string;
  options?: Array<{ label: string; value: string | number }>;
  fieldName?: string;
  validator?: (
    value: string | number | boolean | string[] | Date | null
  ) => boolean | string;
}

const InlineEditor: React.FC<InlineEditorProps> = ({
  value,
  type,
  onSave,
  onCancel,
  placeholder,
  options,
  fieldName,
  validator,
}) => {
  // Fetch all tags to map IDs to names if needed
  const { data: tagsData } = useQuery<PaginatedResponse<TagType>>({
    queryKey: ['all-tags'],
    queryFn: () => apiClient.getTags({ per_page: 1000 }),
    enabled: fieldName === 'tags' && type === 'array',
  });

  // Create a map of tag IDs to names
  const tagIdToName = React.useMemo(() => {
    const map = new Map<string, string>();
    if (tagsData?.items) {
      tagsData.items.forEach((tag: TagType) => {
        map.set(tag.id.toString(), tag.name);
      });
    }
    return map;
  }, [tagsData]);
  const [editValue, setEditValue] = useState<
    string | number | boolean | string[] | Date | null
  >(value);
  const [arrayInput, setArrayInput] = useState('');
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const textAreaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    // Focus input on mount
    setTimeout(() => {
      inputRef.current?.focus();
    }, 100);
  }, []);

  const handleSave = () => {
    // Validate if validator provided
    if (validator) {
      const validationResult = validator(editValue);
      if (validationResult !== true) {
        setError(
          typeof validationResult === 'string'
            ? validationResult
            : 'Invalid value'
        );
        return;
      }
    }

    onSave(editValue);
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey && type !== 'textarea') {
      e.preventDefault();
      handleSave();
    } else if (e.key === 'Escape') {
      onCancel();
    }
  };

  // Render array editor
  if (type === 'array') {
    const items = Array.isArray(editValue) ? editValue : [];

    return (
      <div className="inline-editor array-editor">
        <Space direction="vertical" style={{ width: '100%' }}>
          <div className="array-items">
            {items.map((item, index) => {
              // If this is a tags field and we have the mapping, use tag names
              let displayValue = item;
              if (fieldName === 'tags' && tagIdToName.size > 0) {
                displayValue = tagIdToName.get(item.toString()) || item;
              }
              return (
                <Tag
                  key={index}
                  closable
                  onClose={(_e?: MouseEvent<HTMLElement>) => {
                    const newItems = [...items];
                    newItems.splice(index, 1);
                    setEditValue(newItems);
                  }}
                >
                  {displayValue}
                </Tag>
              );
            })}
          </div>

          <Space.Compact style={{ width: '100%' }}>
            <Input
              ref={inputRef}
              value={arrayInput}
              onChange={(e: ChangeEvent<HTMLInputElement>) =>
                setArrayInput(e.target.value)
              }
              onKeyDown={(e: KeyboardEvent<HTMLInputElement>) => {
                if (e.key === 'Enter' && arrayInput.trim()) {
                  e.preventDefault();
                  setEditValue([...items, arrayInput.trim()]);
                  setArrayInput('');
                } else if (e.key === 'Escape') {
                  onCancel();
                }
              }}
              placeholder="Add item..."
            />
            <Button
              icon={<PlusOutlined />}
              onClick={() => {
                if (arrayInput.trim()) {
                  setEditValue([...items, arrayInput.trim()]);
                  setArrayInput('');
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
            <Button size="small" icon={<CloseOutlined />} onClick={onCancel}>
              Cancel
            </Button>
          </Space>
        </Space>
      </div>
    );
  }

  // Render date editor
  if (type === 'date') {
    return (
      <div className="inline-editor date-editor">
        <Space>
          <DatePicker
            ref={inputRef}
            value={
              editValue &&
              typeof editValue !== 'boolean' &&
              !Array.isArray(editValue)
                ? moment(editValue)
                : null
            }
            onChange={(date) => setEditValue(date?.toISOString() || null)}
            format="YYYY-MM-DD"
          />
          <Button
            type="primary"
            size="small"
            icon={<CheckOutlined />}
            onClick={handleSave}
          />
          <Button size="small" icon={<CloseOutlined />} onClick={onCancel} />
        </Space>
      </div>
    );
  }

  // Render select editor (for options)
  if (options && options.length > 0) {
    return (
      <div className="inline-editor select-editor">
        <Space.Compact style={{ width: '100%' }}>
          <Select
            value={editValue}
            onChange={(
              value: string | number | boolean | string[] | Date | null
            ) => setEditValue(value)}
            style={{ width: '100%' }}
            placeholder={placeholder}
            onKeyDown={handleKeyDown}
            options={options.map((opt) => ({
              value: opt.value,
              label: opt.label,
            }))}
          />
          <Button
            type="primary"
            icon={<CheckOutlined />}
            onClick={handleSave}
          />
          <Button icon={<CloseOutlined />} onClick={onCancel} />
        </Space.Compact>
      </div>
    );
  }

  // Render textarea editor
  if (type === 'textarea') {
    return (
      <div className="inline-editor textarea-editor">
        <TextArea
          ref={textAreaRef}
          value={editValue !== null ? String(editValue) : ''}
          onChange={(e: ChangeEvent<HTMLTextAreaElement>) =>
            setEditValue(e.target.value)
          }
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
          <Button size="small" icon={<CloseOutlined />} onClick={onCancel}>
            Cancel
          </Button>
        </Space>
      </div>
    );
  }

  // Render number editor
  if (type === 'number') {
    return (
      <div className="inline-editor number-editor">
        <Space.Compact>
          <Input
            ref={inputRef}
            type="number"
            value={editValue !== null ? String(editValue) : ''}
            onChange={(e: ChangeEvent<HTMLInputElement>) =>
              setEditValue(parseFloat(e.target.value) || 0)
            }
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            status={error ? 'error' : undefined}
          />
          <Button
            type="primary"
            icon={<CheckOutlined />}
            onClick={handleSave}
          />
          <Button icon={<CloseOutlined />} onClick={onCancel} />
        </Space.Compact>
        {error && <div className="error-message">{error}</div>}
      </div>
    );
  }

  // Default text editor
  return (
    <div className="inline-editor text-editor">
      <Space.Compact style={{ width: '100%' }}>
        <Input
          ref={inputRef}
          value={editValue !== null ? String(editValue) : ''}
          onChange={(e: ChangeEvent<HTMLInputElement>) =>
            setEditValue(e.target.value)
          }
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          status={error ? 'error' : undefined}
        />
        <Button type="primary" icon={<CheckOutlined />} onClick={handleSave} />
        <Button icon={<CloseOutlined />} onClick={onCancel} />
      </Space.Compact>
      {error && <div className="error-message">{error}</div>}
    </div>
  );
};

export default InlineEditor;
