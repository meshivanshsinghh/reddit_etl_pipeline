'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  LayoutDashboard, 
  AlertTriangle, 
  Package, 
  TrendingUp, 
  MessageSquare 
} from 'lucide-react';
import { cn } from '@/lib/utils';

const navItems = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Alerts', href: '/alerts', icon: AlertTriangle },
  { name: 'Products', href: '/products', icon: Package },
  { name: 'Insights', href: '/insights', icon: TrendingUp },
  { name: 'Subreddits', href: '/subreddits', icon: MessageSquare },
];

export function Navigation() {
  const pathname = usePathname();

  return (
    <nav className="w-64 min-h-screen bg-card border-r border-border p-6 flex flex-col">
      {/* Logo/Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-foreground">
          Tesla Energy
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Sentiment Dashboard
        </p>
      </div>

      {/* Navigation Links */}
      <div className="flex-1 space-y-2">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex items-center gap-3 px-4 py-3 rounded-lg transition-colors',
                'hover:bg-accent hover:text-accent-foreground',
                isActive && 'bg-primary text-primary-foreground hover:bg-primary/90'
              )}
            >
              <Icon className="w-5 h-5" />
              <span className="font-medium">{item.name}</span>
            </Link>
          );
        })}
      </div>

      {/* Footer */}
      <div className="mt-auto pt-6 border-t border-border">
        <p className="text-xs text-muted-foreground">
          Interview Project 2024
        </p>
        <p className="text-xs text-muted-foreground mt-1">
          Real-time Reddit Sentiment Analysis
        </p>
      </div>
    </nav>
  );
}

