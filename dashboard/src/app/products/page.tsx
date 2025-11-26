"use client";

import { useEffect, useState } from "react";
import { Product } from "@/types";
import { ProductCard } from "@/components/ProductCard";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Package } from "lucide-react";

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<"posts" | "sentiment">("posts");

  useEffect(() => {
    async function fetchProducts() {
      try {
        setLoading(true);
        const response = await fetch("/api/products");

        if (!response.ok) throw new Error("Failed to fetch products");

        const data = await response.json();
        setProducts(data.data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    }

    fetchProducts();
    // Auto-refresh disabled for better UX
  }, []);

  if (loading) {
    return (
      <div className="p-8">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="bg-destructive/10 border border-destructive text-destructive px-4 py-3 rounded">
          Error: {error}
        </div>
      </div>
    );
  }

  // Sort products
  const sortedProducts = [...products].sort((a, b) => {
    if (sortBy === "posts") {
      return b.post_count - a.post_count;
    } else {
      return (b.avg_sentiment || 0) - (a.avg_sentiment || 0);
    }
  });

  // Category breakdown
  const vehicleProducts = sortedProducts.filter((p) =>
    ["Model Y", "Model 3", "Model S", "Model X", "Cybertruck"].includes(
      p.primary_product
    )
  );
  const energyProducts = sortedProducts.filter((p) =>
    ["Powerwall", "Solar Panels", "Solar Roof", "Megapack"].includes(
      p.primary_product
    )
  );
  const otherProducts = sortedProducts.filter(
    (p) => !vehicleProducts.includes(p) && !energyProducts.includes(p)
  );

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-4xl font-bold">Products</h1>
        <p className="text-muted-foreground mt-2">
          Sentiment analysis by Tesla product category
        </p>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Products
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{products.length}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Identified from posts
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Top Product
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {sortedProducts[0]?.primary_product || "N/A"}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {sortedProducts[0]?.post_count || 0} posts
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Most Positive
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {[...products].sort(
                (a, b) => (b.avg_sentiment || 0) - (a.avg_sentiment || 0)
              )[0]?.primary_product || "N/A"}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {Number(
                [...products].sort(
                  (a, b) =>
                    (Number(b.avg_sentiment) || 0) -
                    (Number(a.avg_sentiment) || 0)
                )[0]?.avg_sentiment || 0
              ).toFixed(3)}{" "}
              sentiment{" "}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Sort Controls */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Product Breakdown</CardTitle>
            <div className="flex gap-2">
              <button
                onClick={() => setSortBy("posts")}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  sortBy === "posts"
                    ? "bg-primary text-primary-foreground"
                    : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
                }`}
              >
                Sort by Posts
              </button>
              <button
                onClick={() => setSortBy("sentiment")}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  sortBy === "sentiment"
                    ? "bg-primary text-primary-foreground"
                    : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
                }`}
              >
                Sort by Sentiment
              </button>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Vehicles Section */}
      {vehicleProducts.length > 0 && (
        <div>
          <h2 className="text-2xl font-bold mb-4">🚗 Vehicles</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {vehicleProducts.map((product) => (
              <ProductCard key={product.primary_product} product={product} />
            ))}
          </div>
        </div>
      )}

      {/* Energy Products Section */}
      {energyProducts.length > 0 && (
        <div>
          <h2 className="text-2xl font-bold mb-4">🔋 Energy Products</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {energyProducts.map((product) => (
              <ProductCard key={product.primary_product} product={product} />
            ))}
          </div>
        </div>
      )}

      {/* Other Products Section */}
      {otherProducts.length > 0 && (
        <div>
          <h2 className="text-2xl font-bold mb-4">📦 Other Products</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {otherProducts.map((product) => (
              <ProductCard key={product.primary_product} product={product} />
            ))}
          </div>
        </div>
      )}

      {products.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center">
            <Package className="w-16 h-16 mx-auto text-muted-foreground mb-4" />
            <p className="text-lg font-medium">No products found</p>
            <p className="text-sm text-muted-foreground">
              Products will appear here once entity extraction completes
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
