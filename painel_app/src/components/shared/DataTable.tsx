import type { ReactNode } from 'react'

interface DataTableProps<T> {
  columns: string[]
  rows: T[]
  renderRow: (item: T) => ReactNode
  emptyText?: string
}

export function DataTable<T>({ columns, rows, renderRow, emptyText = 'Nenhum resultado' }: DataTableProps<T>) {
  if (rows.length === 0) {
    return <p className="empty-state">{emptyText}</p>
  }

  return (
    <table className="table">
      <thead>
        <tr>
          {columns.map((column) => (
            <th key={column}>{column}</th>
          ))}
        </tr>
      </thead>
      <tbody>{rows.map((row) => renderRow(row))}</tbody>
    </table>
  )
}
