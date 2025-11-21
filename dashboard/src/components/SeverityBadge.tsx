import { Badge } from '@/components/ui/badge';
import { AlertSeverity } from '@/types';
import { cn } from '@/lib/utils';

interface SeverityBadgeProps {
  severity: AlertSeverity;
  className?: string;
}

const severityConfig: Record<AlertSeverity, { variant: 'default' | 'secondary' | 'destructive' | 'outline', label: string }> = {
  CRITICAL: { variant: 'destructive', label: '🔴 Critical' },
  HIGH: { variant: 'destructive', label: '🟠 High' },
  MEDIUM: { variant: 'secondary', label: '🟡 Medium' },
  LOW: { variant: 'outline', label: '🔵 Low' },
};

export function SeverityBadge({ severity, className }: SeverityBadgeProps) {
  const config = severityConfig[severity];
  
  return (
    <Badge variant={config.variant} className={cn('font-semibold', className)}>
      {config.label}
    </Badge>
  );
}

