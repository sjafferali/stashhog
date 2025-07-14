import React, { useState, useRef, useEffect } from 'react';
import { Tag, Input, Space, Tooltip, AutoComplete, message } from 'antd';
import { PlusOutlined, CloseOutlined } from '@ant-design/icons';
import { Tag as TagModel } from '@/types/models';
import styles from './TagList.module.scss';

export interface TagListProps {
  tags: string[] | TagModel[];
  editable?: boolean;
  onAdd?: (tag: string) => void | Promise<void>;
  onRemove?: (tag: string) => void | Promise<void>;
  color?: string;
  maxTags?: number;
  maxTagLength?: number;
  suggestions?: string[];
  placeholder?: string;
  allowDuplicates?: boolean;
  size?: 'small' | 'default' | 'large';
}

export const TagList: React.FC<TagListProps> = ({
  tags,
  editable = false,
  onAdd,
  onRemove,
  color,
  maxTags,
  maxTagLength = 50,
  suggestions = [],
  placeholder = 'Add tag...',
  allowDuplicates = false,
  size = 'default',
}) => {
  const [inputVisible, setInputVisible] = useState(false);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<any>(null);

  useEffect(() => {
    if (inputVisible) {
      inputRef.current?.focus();
    }
  }, [inputVisible]);

  const normalizedTags = tags.map(tag => 
    typeof tag === 'string' ? tag : tag.name
  );

  const handleClose = async (removedTag: string) => {
    if (!onRemove) return;
    
    setLoading(true);
    try {
      await onRemove(removedTag);
    } catch (error) {
      console.error('Failed to remove tag:', error);
      message.error('Failed to remove tag');
    } finally {
      setLoading(false);
    }
  };

  const handleInputConfirm = async () => {
    if (!onAdd || !inputValue.trim()) {
      setInputVisible(false);
      setInputValue('');
      return;
    }

    const trimmedValue = inputValue.trim();

    // Validation
    if (!allowDuplicates && normalizedTags.includes(trimmedValue)) {
      message.warning('Tag already exists');
      setInputValue('');
      return;
    }

    if (trimmedValue.length > maxTagLength) {
      message.warning(`Tag must be less than ${maxTagLength} characters`);
      return;
    }

    if (maxTags && normalizedTags.length >= maxTags) {
      message.warning(`Maximum ${maxTags} tags allowed`);
      setInputVisible(false);
      setInputValue('');
      return;
    }

    setLoading(true);
    try {
      await onAdd(trimmedValue);
      setInputValue('');
      setInputVisible(false);
    } catch (error) {
      console.error('Failed to add tag:', error);
      message.error('Failed to add tag');
    } finally {
      setLoading(false);
    }
  };

  const showInput = () => {
    if (maxTags && normalizedTags.length >= maxTags) {
      message.warning(`Maximum ${maxTags} tags allowed`);
      return;
    }
    setInputVisible(true);
  };

  const getTagColor = (tag: string, index: number) => {
    if (color) return color;
    
    // Generate consistent colors based on tag content
    const colors = ['magenta', 'red', 'volcano', 'orange', 'gold', 'lime', 'green', 'cyan', 'blue', 'geekblue', 'purple'];
    const hash = tag.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
    return colors[hash % colors.length];
  };

  const filteredSuggestions = suggestions.filter(suggestion => 
    suggestion.toLowerCase().includes(inputValue.toLowerCase()) &&
    !normalizedTags.includes(suggestion)
  );

  const renderTag = (tag: string | TagModel, index: number) => {
    const tagName = typeof tag === 'string' ? tag : tag.name;
    const tagKey = typeof tag === 'string' ? tag : tag.id;
    
    const isLongTag = tagName.length > 20;
    const tagElem = (
      <Tag
        key={tagKey}
        color={getTagColor(tagName, index)}
        closable={editable && !!onRemove}
        onClose={() => handleClose(tagName)}
        className={styles.tag}
        style={{ 
          fontSize: size === 'small' ? 12 : size === 'large' ? 16 : 14,
        }}
      >
        <span>
          {isLongTag ? `${tagName.slice(0, 20)}...` : tagName}
        </span>
      </Tag>
    );

    return isLongTag ? (
      <Tooltip key={tagKey} title={tagName}>
        {tagElem}
      </Tooltip>
    ) : (
      tagElem
    );
  };

  return (
    <Space size={4} wrap className={styles.tagList}>
      {tags.map((tag, index) => renderTag(tag, index))}
      
      {editable && onAdd && inputVisible ? (
        suggestions.length > 0 ? (
          <AutoComplete
            ref={inputRef}
            value={inputValue}
            onChange={setInputValue}
            onSelect={handleInputConfirm}
            onBlur={handleInputConfirm}
            onPressEnter={handleInputConfirm}
            options={filteredSuggestions.map(value => ({ value }))}
            style={{ width: 120 }}
            size={size}
            placeholder={placeholder}
            disabled={loading}
          />
        ) : (
          <Input
            ref={inputRef}
            type="text"
            size={size}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onBlur={handleInputConfirm}
            onPressEnter={handleInputConfirm}
            style={{ width: 100 }}
            placeholder={placeholder}
            disabled={loading}
          />
        )
      ) : (
        editable && onAdd && (!maxTags || normalizedTags.length < maxTags) && (
          <Tag
            onClick={showInput}
            className={styles.addTag}
            style={{ 
              fontSize: size === 'small' ? 12 : size === 'large' ? 16 : 14,
            }}
          >
            <PlusOutlined /> Add Tag
          </Tag>
        )
      )}
    </Space>
  );
};