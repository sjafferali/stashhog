import React, { useState, useMemo } from 'react';
import { Card, Input, Space, Switch, Typography, Button } from 'antd';
import { 
  SearchOutlined, 
  ExpandOutlined, 
  CompressOutlined,
  CopyOutlined
} from '@ant-design/icons';
import { CopyButton } from './CopyButton';
import styles from './JsonViewer.module.scss';

const { Text } = Typography;
const { Search } = Input;

export interface JsonViewerProps {
  data: any;
  collapsed?: boolean;
  theme?: 'light' | 'dark';
  height?: number | string;
  showToolbar?: boolean;
  searchable?: boolean;
  title?: string;
}

export const JsonViewer: React.FC<JsonViewerProps> = ({
  data,
  collapsed = false,
  theme = 'light',
  height = 400,
  showToolbar = true,
  searchable = true,
  title,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(collapsed);
  const [searchTerm, setSearchTerm] = useState('');
  const [showLineNumbers, setShowLineNumbers] = useState(true);

  const jsonString = useMemo(() => {
    try {
      return JSON.stringify(data, null, 2);
    } catch (error) {
      return 'Invalid JSON data';
    }
  }, [data]);

  const highlightedJson = useMemo(() => {
    if (!searchTerm) return jsonString;

    const escapedSearchTerm = searchTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const regex = new RegExp(`(${escapedSearchTerm})`, 'gi');
    
    return jsonString.split(regex).map((part, index) => {
      if (regex.test(part)) {
        return `<mark class="${styles.highlight}">${part}</mark>`;
      }
      return part;
    });
  }, [jsonString, searchTerm]);

  const renderJson = () => {
    const lines = jsonString.split('\n');
    
    if (isCollapsed) {
      const collapsedLines = lines.slice(0, 10);
      return (
        <>
          {collapsedLines.map((line, index) => renderLine(line, index))}
          {lines.length > 10 && (
            <div className={styles.collapsedIndicator}>
              ... {lines.length - 10} more lines
            </div>
          )}
        </>
      );
    }

    if (searchTerm) {
      // When searching, render with highlights
      return (
        <div 
          dangerouslySetInnerHTML={{ 
            __html: highlightedJson.join('').split('\n').map((line, index) => 
              `<div class="${styles.line}">
                ${showLineNumbers ? `<span class="${styles.lineNumber}">${index + 1}</span>` : ''}
                <span class="${styles.content}">${line}</span>
              </div>`
            ).join('')
          }} 
        />
      );
    }

    return lines.map((line, index) => renderLine(line, index));
  };

  const renderLine = (line: string, index: number) => {
    return (
      <div key={index} className={styles.line}>
        {showLineNumbers && (
          <span className={styles.lineNumber}>{index + 1}</span>
        )}
        <span className={styles.content}>{line}</span>
      </div>
    );
  };

  const toolbar = showToolbar && (
    <div className={styles.toolbar}>
      <Space>
        {searchable && (
          <Search
            placeholder="Search..."
            allowClear
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{ width: 200 }}
            size="small"
            prefix={<SearchOutlined />}
          />
        )}
        
        <Space split="|">
          <Space size="small">
            <Text type="secondary" style={{ fontSize: 12 }}>Line Numbers</Text>
            <Switch
              size="small"
              checked={showLineNumbers}
              onChange={setShowLineNumbers}
            />
          </Space>
          
          <Button
            type="text"
            size="small"
            icon={isCollapsed ? <ExpandOutlined /> : <CompressOutlined />}
            onClick={() => setIsCollapsed(!isCollapsed)}
          >
            {isCollapsed ? 'Expand' : 'Collapse'}
          </Button>
          
          <CopyButton text={jsonString} showText />
        </Space>
      </Space>
    </div>
  );

  const content = (
    <div 
      className={`${styles.jsonContent} ${theme === 'dark' ? styles.dark : ''}`}
      style={{ height: typeof height === 'number' ? `${height}px` : height }}
    >
      {renderJson()}
    </div>
  );

  if (title) {
    return (
      <Card 
        title={title} 
        size="small"
        extra={toolbar}
        className={styles.jsonViewer}
      >
        {content}
      </Card>
    );
  }

  return (
    <div className={styles.jsonViewer}>
      {toolbar}
      {content}
    </div>
  );
};