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

  // Get post links from metadata (they're stored as full URLs, permalinks, or just post_id)
  let permalinks: string[] = [];
  
  if (alert.metadata?.post_links) {
    // Case 1: Has full post_links array
    permalinks = alert.metadata.post_links.map((link: string) => {
      if (link.startsWith('http')) {
        return link.replace(/^https?:\/\/(www\.)?reddit\.com/, '');
      }
      return link;
    });
  } else if (alert.metadata?.permalinks) {
    // Case 2: Has permalinks array
    permalinks = alert.metadata.permalinks;
  } else if (alert.metadata?.post_id) {
    // Case 3: Has single post_id (EXTREME_POST alerts)
    permalinks = [`/r/${alert.subreddit}/comments/${alert.metadata.post_id}/`];
  } else if (alert.metadata?.post_ids && Array.isArray(alert.metadata.post_ids)) {
    // Case 4: Has post_ids array
    permalinks = alert.metadata.post_ids.map((id: string) => 
      `/r/${alert.subreddit}/comments/${id}/`
    );
  }

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
          <div className="text-xs text-muted-foreground bg-muted/50 rounded px-3 py-2">
            Metric Value: <span className="font-semibold text-foreground">{Number(alert.metric_value).toFixed(3)}</span>
          </div>
        )}

        {permalinks.length > 0 && (
          <div className="space-y-2 bg-blue-500/10 border-2 border-blue-500/30 rounded-lg p-4">
            <p className="text-sm font-semibold text-foreground flex items-center gap-2">
              <ExternalLink className="w-4 h-4 text-blue-500" />
              View Original Reddit Posts
            </p>
            <div className="flex flex-wrap gap-2">
              {permalinks.slice(0, 5).map((permalink, idx) => (
                <a
                  key={idx}
                  href={`${REDDIT_BASE_URL}${permalink}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors shadow-sm"
                >
                  <ExternalLink className="w-4 h-4" />
                  Reddit Post {idx + 1}
                </a>
              ))}
              {permalinks.length > 5 && (
                <span className="inline-flex items-center px-4 py-2 text-sm font-medium text-muted-foreground bg-muted rounded-md">
                  +{permalinks.length - 5} more posts
                </span>
              )}
            </div>
            {((alert.metadata?.post_titles && alert.metadata.post_titles.length > 0) || alert.metadata?.title) && (
              <div className="mt-2 pt-2 border-t border-border">
                <p className="text-xs text-muted-foreground font-medium mb-1">Post Title{alert.metadata?.post_titles?.length > 1 ? 's' : ''}:</p>
                <ul className="space-y-1">
                  {alert.metadata?.title && (
                    <li className="text-xs text-foreground">
                      • {alert.metadata.title}
                    </li>
                  )}
                  {alert.metadata?.post_titles && alert.metadata.post_titles.slice(0, 3).map((title: string, idx: number) => (
                    <li key={idx} className="text-xs text-foreground">
                      • {title}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        <div className="text-xs text-muted-foreground border-t pt-2">
          Detected: {format(new Date(alert.detected_at), 'MMM dd, yyyy HH:mm')}
        </div>
      </CardContent>
    </Card>
  );
}

