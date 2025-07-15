import React, { useMemo, useCallback } from 'react';
import { Typography, Tag, Space, Button, message } from 'antd';
import { CopyOutlined } from '@ant-design/icons';
import { diffLines, diffWords, diffJson } from 'diff';
import styles from './DiffViewer.module.scss';

const { Text } = Typography;

export interface DiffViewerProps {
  current:
    | string
    | number
    | boolean
    | string[]
    | Record<string, unknown>
    | null;
  proposed:
    | string
    | number
    | boolean
    | string[]
    | Record<string, unknown>
    | null;
  type: 'text' | 'array' | 'object' | 'json';
  showLineNumbers?: boolean;
  collapsed?: boolean;
}

export const DiffViewer: React.FC<DiffViewerProps> = ({
  current,
  proposed,
  type,
  showLineNumbers = true,
  collapsed = false,
}) => {
  const handleCopy = (text: string) => {
    void navigator.clipboard.writeText(text);
    void message.success('Copied to clipboard');
  };

  const formatValue = useCallback(
    (
      value:
        | string
        | number
        | boolean
        | string[]
        | Record<string, unknown>
        | null
    ): string => {
      if (value === null || value === undefined) return '';

      if (type === 'array') {
        return Array.isArray(value) ? value.join('\n') : String(value);
      }

      if (type === 'object' || type === 'json') {
        return JSON.stringify(value, null, 2);
      }

      return String(value);
    },
    [type]
  );

  const diff = useMemo(() => {
    const currentStr = formatValue(current);
    const proposedStr = formatValue(proposed);

    if (type === 'object' || type === 'json') {
      try {
        return diffJson(
          typeof current === 'string'
            ? current
            : JSON.stringify(current, null, 2),
          typeof proposed === 'string'
            ? proposed
            : JSON.stringify(proposed, null, 2)
        );
      } catch {
        return diffLines(currentStr, proposedStr);
      }
    }

    if (
      (type === 'text' && currentStr.includes('\n')) ||
      proposedStr.includes('\n')
    ) {
      return diffLines(currentStr, proposedStr);
    }

    return diffWords(currentStr, proposedStr);
  }, [current, proposed, type, formatValue]);

  const renderDiff = () => {
    let lineNumber = 1;

    return diff.map((part, index) => {
      const lines = part.value.split('\n');
      const isLastPart = index === diff.length - 1;
      const linesToRender = isLastPart ? lines : lines.slice(0, -1);

      return linesToRender
        .map((line, lineIndex) => {
          const currentLineNumber = lineNumber++;
          const isEmptyLine =
            line === '' && lineIndex === linesToRender.length - 1;

          if (isEmptyLine && !part.added && !part.removed) {
            return null;
          }

          return (
            <div
              key={`${index}-${lineIndex}`}
              className={`${styles.line} ${
                part.added ? styles.added : part.removed ? styles.removed : ''
              }`}
            >
              {showLineNumbers && (
                <span className={styles.lineNumber}>
                  {part.removed ? '-' : currentLineNumber}
                </span>
              )}
              <span className={styles.content}>
                {part.added && <span className={styles.marker}>+</span>}
                {part.removed && <span className={styles.marker}>-</span>}
                {!part.added && !part.removed && (
                  <span className={styles.marker}> </span>
                )}
                {line || '\u00A0'}
              </span>
            </div>
          );
        })
        .filter(Boolean);
    });
  };

  const renderCompact = () => {
    const currentStr = formatValue(current);
    const proposedStr = formatValue(proposed);

    return (
      <div className={styles.compact}>
        <div className={styles.compactSection}>
          <Text type="secondary">Current:</Text>
          <div className={styles.compactValue}>
            <Text delete>{currentStr || 'None'}</Text>
            <Button
              type="text"
              size="small"
              icon={<CopyOutlined />}
              onClick={() => handleCopy(currentStr)}
            />
          </div>
        </div>
        <div className={styles.compactSection}>
          <Text type="secondary">Proposed:</Text>
          <div className={styles.compactValue}>
            <Text mark>{proposedStr || 'None'}</Text>
            <Button
              type="text"
              size="small"
              icon={<CopyOutlined />}
              onClick={() => handleCopy(proposedStr)}
            />
          </div>
        </div>
      </div>
    );
  };

  const stats = useMemo(() => {
    let additions = 0;
    let deletions = 0;

    diff.forEach((part) => {
      const lines = part.value.split('\n').length - 1;
      if (part.added) additions += lines || 1;
      if (part.removed) deletions += lines || 1;
    });

    return { additions, deletions };
  }, [diff]);

  if (collapsed) {
    return renderCompact();
  }

  return (
    <div className={styles.diffViewer}>
      <div className={styles.header}>
        <Space>
          <Tag color="green">+{stats.additions}</Tag>
          <Tag color="red">-{stats.deletions}</Tag>
        </Space>
        <Space>
          <Button
            type="text"
            size="small"
            icon={<CopyOutlined />}
            onClick={() => handleCopy(formatValue(current))}
          >
            Copy Current
          </Button>
          <Button
            type="text"
            size="small"
            icon={<CopyOutlined />}
            onClick={() => handleCopy(formatValue(proposed))}
          >
            Copy Proposed
          </Button>
        </Space>
      </div>
      <div className={styles.diffContent}>{renderDiff()}</div>
    </div>
  );
};
