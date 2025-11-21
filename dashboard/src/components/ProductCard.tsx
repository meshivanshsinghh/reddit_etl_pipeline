import { Product } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SentimentBadge } from "./SentimentBadge";
import { Package } from "lucide-react";
import { formatNumber } from "@/lib/constants";

interface ProductCardProps {
  product: Product;
}

export function ProductCard({ product }: ProductCardProps) {
  return (
    <Card className="transition-all hover:shadow-md hover:border-primary/50">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="text-lg flex items-center gap-2">
              <Package className="w-5 h-5" />
              {product.primary_product}
            </CardTitle>
          </div>
          <SentimentBadge sentiment={product.avg_sentiment} />
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-sm text-muted-foreground">Posts</span>
            <span className="text-2xl font-bold">
              {formatNumber(product.post_count)}
            </span>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-sm text-muted-foreground">Avg Sentiment</span>
            <span className="text-lg font-semibold">
              {product.avg_sentiment
                ? Number(product.avg_sentiment).toFixed(3)
                : "N/A"}
            </span>
          </div>

          {/* Sentiment Bar */}
          <div className="w-full h-2 bg-secondary rounded-full overflow-hidden">
            <div
              className="h-full transition-all"
              style={{
                width: `${Math.abs((product.avg_sentiment || 0) * 50)}%`,
                backgroundColor:
                  (product.avg_sentiment || 0) > 0.2
                    ? "#22c55e"
                    : (product.avg_sentiment || 0) < 0
                    ? "#ef4444"
                    : "#eab308",
              }}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
