import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface KPICardProps {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  trend?: {
    value: string;
    positive: boolean;
  };
  status?: 'success' | 'warning' | 'danger' | 'default';
}

export function KPICard({ icon, label, value, trend, status = 'default' }: KPICardProps) {
  const statusColors = {
    success: 'text-success',
    warning: 'text-warning',
    danger: 'text-destructive',
    default: 'text-accent',
  };

  return (
    <Card className="p-6 hover:shadow-md transition-shadow duration-200">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm text-muted-foreground mb-2">{label}</p>
          <p className={cn('text-3xl font-semibold tabular-nums', statusColors[status])}>
            {value}
          </p>
          {trend && (
            <div className="mt-2 flex items-center gap-1 text-xs">
              <span className={trend.positive ? 'text-success' : 'text-destructive'}>
                {trend.positive ? '↑' : '↓'} {trend.value}
              </span>
              <span className="text-muted-foreground">vs. ontem</span>
            </div>
          )}
        </div>
        <div className={cn('p-3 rounded-lg bg-opacity-10', statusColors[status])}>
          {icon}
        </div>
      </div>
    </Card>
  );
}
