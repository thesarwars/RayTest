import { ProductGrid } from "@/components/ProductGrid";

export default function HomePage() {
  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Flash Sale</h1>
        <p className="mt-2 text-gray-500">
          Limited stock, first come first served. Reserve now — you have 5 minutes to checkout.
        </p>
      </div>
      <ProductGrid />
    </div>
  );
}
