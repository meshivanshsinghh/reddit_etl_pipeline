'use client';

import { useState } from 'react';
import { format } from 'date-fns';
import { Alert } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { SeverityBadge } from './SeverityBadge';
import { ExternalLink, CheckCircle } from 'lucide-react';
import { REDDIT_BASE_URL } from '@/lib/constants';
import { cn } from '@/lib/utils';

interface AlertCardProps {
  alert: Alert;
  onResolve?: (id: number) => void;
}

export function AlertCard({ alert, onResolve }: AlertCardProps) {
  const [isResolving, setIsResolving] = useState(false);

  const handleResolve = async () => {
    if (!onResolve) return;
    
    setIsResolving(true);
    try {
      await onResolve(alert.id);
    } finally {
      setIsResolving(false);
    }
  };

  const permalinks = alert.metadata?.permalinks || [];

  return (
    <Card className={cn(
      'transition-all hover:shadow-md',
      alert.resolved && 'opacity-60'
    )}>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <SeverityBadge severity={alert.severity} />
              <span className="text-xs text-muted-foreground">
                {alert.alert_type.replace(/_/g, ' ')}
              </span>
            </div>
            <CardTitle className="text-lg">
              r/{alert.subreddit}
            </CardTitle>
          </div>
          {!alert.resolved && onResolve && (
            <Button
              size="sm"
              variant="outline"
              onClick={handleResolve}
              disabled={isResolving}
            >
              <CheckCircle className="w-4 h-4 mr-1" />
              {isResolving ? 'Resolving...' : 'Resolve'}
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-foreground">
          {alert.message}
        </p>
        
        {alert.metric_value !== undefined && (
          <div className="text-xs text-muted-foreground">
            Metric Value: <span className="font-semibold">{alert.metric_value.toFixed(3)}</span>
          </div>
        )}

        {permalinks.length > 0 && (
          <div className="space-y-1">
            <p className="text-xs font-medium text-muted-foreground">Source Posts:</p>
            <div className="flex flex-wrap gap-2">
              {permalinks.slice(0, 3).map((permalink, idx) => (
                <a
                  key={idx}
                  href={`${REDDIT_BASE_URL}${permalink}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                >
                  <ExternalLink className="w-3 h-3" />
                  Post {idx + 1}
                </a>
              ))}
              {permalinks.length > 3 && (
                <span className="text-xs text-muted-foreground">
                  +{permalinks.length - 3} more
                </span>
              )}
            </div>
          </div>
        )}

        <div className="text-xs text-muted-foreground border-t pt-2">
          Detected: {format(new Date(alert.detected_at), 'MMM dd, yyyy HH:mm')}
        </div>
      </CardContent>
    </Card>
  );
}

