import { Table } from 'antd';
import type { TableProps, ColumnsType } from 'antd/es/table';
import { EmptyState } from './EmptyState';
import styles from './DataTable.module.scss';

export interface DataTableProps<T>
  extends Omit<TableProps<T>, 'columns' | 'dataSource'> {
  columns: ColumnsType<T>;
  data: readonly T[];
  loading?: boolean;
  pagination?: TableProps<T>['pagination'];
  onRow?: TableProps<T>['onRow'];
  emptyText?: string;
  emptyDescription?: string;
}

export function DataTable<T extends object>({
  columns,
  data,
  loading = false,
  pagination = {
    pageSize: 10,
    showSizeChanger: true,
    showTotal: (total: number, range: [number, number]) =>
      `${range[0]}-${range[1]} of ${total} items`,
  },
  onRow,
  emptyText = 'No data',
  emptyDescription,
  className,
  ...restProps
}: DataTableProps<T>) {
  return (
    <Table<T>
      className={`${styles.dataTable} ${className || ''}`}
      columns={columns}
      dataSource={[...data]}
      loading={loading}
      pagination={pagination as any} // eslint-disable-line @typescript-eslint/no-explicit-any
      onRow={onRow}
      locale={{
        emptyText: (
          <EmptyState title={emptyText} description={emptyDescription} />
        ),
      }}
      {...(restProps as any)} // eslint-disable-line @typescript-eslint/no-explicit-any
    />
  );
}
