import React from 'react';
import { Table, TableProps } from 'antd';
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table';
import { EmptyState } from './EmptyState';
import styles from './DataTable.module.scss';

export interface DataTableProps<T> extends Omit<TableProps<T>, 'columns'> {
  columns: ColumnsType<T>;
  data: T[];
  loading?: boolean;
  pagination?: TablePaginationConfig | false;
  onRow?: (record: T) => TableProps<T>['onRow'];
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
    showTotal: (total, range) => `${range[0]}-${range[1]} of ${total} items`,
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
      dataSource={data}
      loading={loading}
      pagination={pagination}
      onRow={onRow}
      locale={{
        emptyText: (
          <EmptyState
            title={emptyText}
            description={emptyDescription}
          />
        ),
      }}
      {...restProps}
    />
  );
}