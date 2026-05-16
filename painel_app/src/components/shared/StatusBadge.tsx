interface StatusBadgeProps {
  label: string
  tone?: 'blue' | 'green' | 'yellow' | 'red' | 'purple' | 'gray'
}

export function StatusBadge({ label, tone = 'gray' }: StatusBadgeProps) {
  return <span className={`status-badge ${tone}`}>{label}</span>
}
