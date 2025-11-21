'use client';

import { useEffect, useState } from 'react';
import { Alert, AlertSeverity } from '@/types';
import { AlertCard } from '@/components/AlertCard';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Select } from '@/components/ui/select';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { AlertTriangle, CheckCircle } from 'lucide-react';

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [severityFilter, setSeverityFilter] = useState<string>('');
  const [showResolved, setShowResolved] = useState(false);

  const fetchAlerts = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (severityFilter) params.append('severity', severityFilter);
      params.append('resolved', showResolved.toString());

      const response = await fetch(`/api/alerts?${params}`);
      if (!response.ok) throw new Error('Failed to fetch alerts');

      const data = await response.json();
      setAlerts(data.data.alerts);
      setCounts(data.data.counts);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
    
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchAlerts, 30000);
    return () => clearInterval(interval);
  }, [severityFilter, showResolved]);

  const handleResolve = async (id: number) => {
    try {
      const response = await fetch(`/api/alerts/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resolved: true }),
      });

      if (!response.ok) throw new Error('Failed to resolve alert');

      // Refresh alerts
      fetchAlerts();
    } catch (err) {
      console.error('Error resolving alert:', err);
    }
  };

  if (loading && alerts.length === 0) {
    return (
      <div className="p-8">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  const totalActive = Object.values(counts).reduce((a, b) => a + b, 0);

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-4xl font-bold">Alerts</h1>
        <p className="text-muted-foreground mt-2">
          Real-time anomaly detection and critical alerts
        </p>
      </div>

      {/* Alert Counts */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Active
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{totalActive}</div>
          </CardContent>
        </Card>
        
        <Card className="border-red-500/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-red-500">
              🔴 Critical
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{counts.CRITICAL || 0}</div>
          </CardContent>
        </Card>

        <Card className="border-orange-500/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-orange-500">
              🟠 High
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{counts.HIGH || 0}</div>
          </CardContent>
        </Card>

        <Card className="border-yellow-500/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-yellow-500">
              🟡 Medium
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{counts.MEDIUM || 0}</div>
          </CardContent>
        </Card>

        <Card className="border-blue-500/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-blue-500">
              🔵 Low
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{counts.LOW || 0}</div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Alert Feed</CardTitle>
            <div className="flex gap-4 items-center">
              <Tabs value={showResolved ? 'resolved' : 'active'} onValueChange={(v) => setShowResolved(v === 'resolved')}>
                <TabsList>
                  <TabsTrigger value="active">
                    <AlertTriangle className="w-4 h-4 mr-2" />
                    Active
                  </TabsTrigger>
                  <TabsTrigger value="resolved">
                    <CheckCircle className="w-4 h-4 mr-2" />
                    Resolved
                  </TabsTrigger>
                </TabsList>
              </Tabs>
              
              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
                className="px-3 py-2 rounded-md border border-border bg-background text-sm"
              >
                <option value="">All Severities</option>
                <option value="CRITICAL">Critical</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
              </select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {error && (
            <div className="bg-destructive/10 border border-destructive text-destructive px-4 py-3 rounded mb-4">
              Error: {error}
            </div>
          )}

          {alerts.length === 0 ? (
            <div className="text-center py-12">
              <CheckCircle className="w-16 h-16 mx-auto text-muted-foreground mb-4" />
              <p className="text-lg font-medium">No alerts found</p>
              <p className="text-sm text-muted-foreground">
                {showResolved ? 'No resolved alerts' : 'All systems operating normally'}
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {alerts.map((alert) => (
                <AlertCard
                  key={alert.id}
                  alert={alert}
                  onResolve={!showResolved ? handleResolve : undefined}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Footer */}
      <div className="text-center text-sm text-muted-foreground">
        Alerts update automatically every 30 seconds
      </div>
    </div>
  );
}

