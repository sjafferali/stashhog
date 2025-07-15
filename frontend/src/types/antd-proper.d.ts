import type {
  ChangeEvent,
  ReactNode,
  CSSProperties,
  MouseEvent,
  KeyboardEvent,
} from 'react';
import type { Moment } from 'moment';
import type { Dayjs } from 'dayjs';

// Re-export types for table sorting/filtering
export type { FilterValue, SorterResult } from 'antd/es/table/interface';

// Common types
export type SizeType = 'small' | 'middle' | 'large';

// Input types
export interface InputProps {
  value?: string;
  onChange?: (e: ChangeEvent<HTMLInputElement>) => void;
  onPressEnter?: (e: KeyboardEvent<HTMLInputElement>) => void;
  onKeyDown?: (e: KeyboardEvent<HTMLInputElement>) => void;
  onBlur?: (e: ChangeEvent<HTMLInputElement>) => void;
  placeholder?: string;
  prefix?: ReactNode;
  suffix?: ReactNode;
  size?: SizeType;
  style?: CSSProperties;
  className?: string;
  disabled?: boolean;
  status?: 'error' | 'warning';
  type?: string;
  ref?: React.Ref<HTMLInputElement>;
  allowClear?: boolean;
}

export interface TextAreaProps {
  value?: string | number | readonly string[];
  onChange?: (e: ChangeEvent<HTMLTextAreaElement>) => void;
  onKeyDown?: (e: KeyboardEvent<HTMLTextAreaElement>) => void;
  placeholder?: string;
  autoSize?: boolean | { minRows?: number; maxRows?: number };
  status?: 'error' | 'warning';
  ref?: React.Ref<HTMLTextAreaElement>;
  rows?: number;
}

// Select types
export interface SelectOption<T = string | number> {
  label: ReactNode;
  value: T;
  disabled?: boolean;
  children?: ReactNode;
}

export interface SelectProps<T = string | number> {
  value?: T | T[];
  onChange?: (value: T, option: SelectOption<T> | SelectOption<T>[]) => void;
  onSelect?: (value: T, option: SelectOption<T>) => void;
  options?: SelectOption<T>[];
  placeholder?: string;
  mode?: 'multiple' | 'tags';
  filterOption?:
    | boolean
    | ((input: string, option?: SelectOption<T>) => boolean);
  style?: CSSProperties;
  className?: string;
  allowClear?: boolean;
  maxTagCount?: number | 'responsive';
  disabled?: boolean;
  size?: SizeType;
  onKeyDown?: (e: KeyboardEvent) => void;
  showSearch?: boolean;
  suffixIcon?: ReactNode;
}

// AutoComplete types
export interface AutoCompleteProps {
  value?: string;
  onChange?: (value: string) => void;
  onSelect?: (value: string, option: { value: string }) => void;
  onBlur?: () => void;
  options?: Array<{ value: string; label?: string }>;
  placeholder?: string;
  style?: CSSProperties;
  size?: SizeType;
  disabled?: boolean;
  ref?: React.Ref<HTMLInputElement>;
}

// DatePicker types
export interface DatePickerProps {
  value?: Moment | Dayjs | null;
  onChange?: (date: Dayjs | null, dateString: string) => void;
  format?: string;
  placeholder?: string;
  style?: CSSProperties;
  ref?: React.Ref<HTMLElement>;
}

export interface RangePickerProps {
  value?: [Dayjs | null, Dayjs | null] | null;
  onChange?: (
    dates: [Dayjs | null, Dayjs | null] | null,
    dateStrings: [string, string]
  ) => void;
  format?: string;
  style?: CSSProperties;
}

// Checkbox types
export interface CheckboxChangeEvent {
  target: {
    checked: boolean;
  };
  stopPropagation: () => void;
  preventDefault: () => void;
  nativeEvent: MouseEvent;
}

export interface CheckboxProps {
  checked?: boolean;
  onChange?: (e: CheckboxChangeEvent) => void;
  onClick?: (e: MouseEvent) => void;
  indeterminate?: boolean;
  disabled?: boolean;
  children?: ReactNode;
  className?: string;
}

// Button types
export interface ButtonProps {
  onClick?: (e: MouseEvent<HTMLElement>) => void;
  type?: 'primary' | 'default' | 'dashed' | 'link' | 'text';
  size?: SizeType;
  icon?: ReactNode;
  danger?: boolean;
  disabled?: boolean;
  loading?: boolean;
  children?: ReactNode;
  style?: CSSProperties;
  className?: string;
}

// Tag types
export interface TagProps {
  closable?: boolean;
  onClose?: (e: MouseEvent<HTMLElement>) => void | Promise<void>;
  color?: string;
  children?: ReactNode;
  style?: CSSProperties;
  className?: string;
  onClick?: (e: MouseEvent<HTMLElement>) => void;
}

// Table types
export interface TableColumnType<T = Record<string, unknown>> {
  title?: ReactNode | (() => ReactNode);
  dataIndex?: string;
  key?: string;
  render?: (value: unknown, record: T, index: number) => ReactNode;
  sorter?: boolean | ((a: T, b: T) => number);
  sortOrder?: 'ascend' | 'descend' | null;
  width?: number | string;
  fixed?: 'left' | 'right' | boolean;
  align?: 'left' | 'right' | 'center';
  ellipsis?: boolean;
  filters?: Array<{ text: ReactNode; value: string | number | boolean }>;
  onFilter?: (value: string | number | boolean, record: T) => boolean;
}

export interface TableProps<T = Record<string, unknown>> {
  columns?: TableColumnType<T>[];
  dataSource?: T[];
  rowKey?: string | ((record: T) => string);
  pagination?: false | TablePaginationConfig;
  onChange?: (
    pagination: TablePaginationConfig,
    filters: Record<string, FilterValue | null>,
    sorter: SorterResult<T> | SorterResult<T>[]
  ) => void;
  onRow?: (
    record: T,
    index?: number
  ) => {
    onClick?: (event: MouseEvent) => void;
    onDoubleClick?: (event: MouseEvent) => void;
    onContextMenu?: (event: MouseEvent) => void;
    onMouseEnter?: (event: MouseEvent) => void;
    onMouseLeave?: (event: MouseEvent) => void;
    style?: CSSProperties;
    className?: string;
  };
  rowClassName?: (record: T, index: number) => string;
  scroll?: { x?: number | string; y?: number | string };
  loading?: boolean;
  size?: SizeType;
  className?: string;
}

export interface TablePaginationConfig {
  current?: number;
  pageSize?: number;
  total?: number;
  showSizeChanger?: boolean;
  showTotal?: (total: number, range: [number, number]) => ReactNode;
  onChange?: (page: number, pageSize: number) => void;
  onShowSizeChange?: (current: number, size: number) => void;
}

// Table filter and sorter types
export type FilterValue =
  | string
  | number
  | boolean
  | (string | number | boolean)[];
export interface SorterResult<T> {
  column?: TableColumnType<T>;
  order?: 'ascend' | 'descend' | null;
  field?: string | string[];
  columnKey?: string;
}

// Collapse types
export interface CollapseProps {
  activeKey?: string | string[];
  defaultActiveKey?: string | string[];
  onChange?: (key: string | string[]) => void;
  ghost?: boolean;
  children?: ReactNode;
}

// List types
export interface ListRenderItem<T> {
  (item: T, index: number): ReactNode;
}

export interface ListProps<T = Record<string, unknown>> {
  dataSource?: T[];
  renderItem?: ListRenderItem<T>;
  pagination?: false | TablePaginationConfig;
  loading?: boolean;
  locale?: {
    emptyText?: ReactNode;
  };
  grid?: {
    gutter?: number;
    xs?: number;
    sm?: number;
    md?: number;
    lg?: number;
    xl?: number;
    xxl?: number;
  };
  size?: SizeType;
}

export interface ListItemProps {
  className?: string;
  children?: ReactNode;
  actions?: ReactNode[];
  extra?: ReactNode;
}

export interface ListItemMetaProps {
  avatar?: ReactNode;
  title?: ReactNode;
  description?: ReactNode;
  className?: string;
}

// Space types
export interface SpaceCompactProps {
  size?: SizeType;
  style?: CSSProperties;
  children?: ReactNode;
}
