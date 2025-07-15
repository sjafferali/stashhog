import type {
  InputProps,
  TextAreaProps,
  SelectProps,
  AutoCompleteProps,
  DatePickerProps,
  RangePickerProps,
  CheckboxProps,
  CheckboxChangeEvent,
  ButtonProps,
  TagProps,
  TableProps,
  CollapseProps,
  ListProps,
  SpaceCompactProps,
} from './antd-proper';

/* eslint-disable @typescript-eslint/no-explicit-any */
declare module 'antd' {
  // Re-export properly typed components from antd-proper.d.ts
  export const Input: React.FC<InputProps> & {
    TextArea: React.FC<TextAreaProps>;
    Search: React.FC<
      InputProps & {
        onSearch?: (value: string) => void;
        enterButton?: boolean | React.ReactNode;
      }
    >;
    Password: React.FC<InputProps>;
  };

  export const Select: (<T = any>(
    props: SelectProps<T>
  ) => React.ReactElement) & {
    Option: React.FC<{ value: any; children: React.ReactNode }>;
  };

  export const AutoComplete: React.FC<AutoCompleteProps>;

  export const DatePicker: React.FC<DatePickerProps> & {
    RangePicker: React.FC<RangePickerProps>;
  };

  export const Checkbox: React.FC<CheckboxProps>;
  export type { CheckboxChangeEvent };

  export const Button: React.FC<ButtonProps>;
  export const Tag: React.FC<TagProps>;
  export const Table: <T = any>(props: TableProps<T>) => React.ReactElement;
  export const Collapse: React.FC<CollapseProps> & {
    Panel: React.FC<{
      header: React.ReactNode;
      key: string;
      children: React.ReactNode;
    }>;
  };
  export const List: (<T = any>(props: ListProps<T>) => React.ReactElement) & {
    Item: React.FC<{
      className?: string;
      children: React.ReactNode;
      actions?: React.ReactNode[];
      extra?: React.ReactNode;
    }> & {
      Meta: React.FC<{
        avatar?: React.ReactNode;
        title?: React.ReactNode;
        description?: React.ReactNode;
        className?: string;
      }>;
    };
  };

  export const Space: React.FC<{
    direction?: 'horizontal' | 'vertical';
    size?: 'small' | 'middle' | 'large' | number;
    wrap?: boolean;
    style?: React.CSSProperties;
    children?: React.ReactNode;
    align?: 'start' | 'end' | 'center' | 'baseline';
    className?: string;
  }> & {
    Compact: React.FC<SpaceCompactProps>;
  };

  // Components that still need proper typing
  export const message: any;
  export const notification: any;
  export const Modal: any;
  export const Form: any;
  export const Card: any;
  export const Typography: any;
  export const Tooltip: any;
  export const Progress: any;
  export const Spin: any;
  export const Alert: any;
  export const Row: any;
  export const Col: any;
  export const Layout: any;
  export const Menu: any;
  export const Dropdown: any;
  export const Avatar: any;
  export const Badge: any;
  export const Breadcrumb: any;
  export const TimePicker: any;
  export const Radio: any;
  export const Switch: any;
  export const Upload: any;
  export const Rate: any;
  export const Slider: any;
  export const Tree: any;
  export const TreeSelect: any;
  export const Transfer: any;
  export const Tabs: any;
  export const Carousel: any;
  export const Calendar: any;
  export const Timeline: any;
  export const Steps: any;
  export const Statistic: any;
  export const Descriptions: any;
  export const Empty: any;
  export const Popover: any;
  export const Popconfirm: any;
  export const Divider: any;
  export const Drawer: any;
  export const Skeleton: any;
  export const Result: any;
  export const Segmented: any;
  export const Affix: any;
  export const BackTop: any;
  export const ConfigProvider: any;
  export const FloatButton: any;
  export const Watermark: any;
  export const Tour: any;
  export const App: any;
  export const theme: any;
  export const version: string;
  export const InputNumber: any;
  export const Pagination: any;
  export const Image: any;
  export interface MenuProps {
    [key: string]: any;
  }
}

declare module 'antd/es/table' {
  import type {
    TableProps as TablePropsType,
    TableColumnType,
    TablePaginationConfig,
  } from '../types/antd-proper';

  const Table: <T = any>(props: TablePropsType<T>) => React.ReactElement;
  export default Table;
  export type ColumnsType<T = any> = TableColumnType<T>[];
  export type { TablePaginationConfig, TablePropsType as TableProps };
}

declare module 'antd/es/table/interface' {
  export type {
    TableColumnType as ColumnsType,
    TablePaginationConfig,
    TableProps,
  } from '../types/antd-proper';
}
