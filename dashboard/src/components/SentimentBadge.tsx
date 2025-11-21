import { Badge } from '@/components/ui/badge';
import { getSentimentLabel, getSentimentColor } from '@/lib/constants';
import { cn } from '@/lib/utils';

interface SentimentBadgeProps {
  sentiment: number;
  showValue?: boolean;
  className?: string;
}

export function SentimentBadge({ sentiment, showValue = false, className }: SentimentBadgeProps) {
  const label = getSentimentLabel(sentiment);
  const colorClass = getSentimentColor(sentiment);
  
  let variant: 'default' | 'secondary' | 'destructive' | 'outline' = 'secondary';
  
  if (sentiment > 0.2) {
    variant = 'default';
  } else if (sentiment < 0) {
    variant = 'destructive';
  }
  
  return (
    <Badge variant={variant} className={cn('', className)}>
      {label}
      {showValue && <span className="ml-1">({sentiment.toFixed(3)})</span>}
    </Badge>
  );
}

