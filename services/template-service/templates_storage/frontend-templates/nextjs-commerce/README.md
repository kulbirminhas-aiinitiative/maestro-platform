# Next.js Commerce

High-performance headless e-commerce storefront built with Next.js. Features product discovery, cart management, checkout flow, and optimized for conversions.

## Features

- 🛍️ **Complete E-commerce**: Product listings, detail pages, cart, and checkout
- ⚡ **Blazing Fast**: Server-side rendering and static generation with Next.js
- 🎨 **Beautiful UI**: Tailwind CSS with mobile-first responsive design
- 🔍 **SEO Optimized**: Perfect for product discovery and search rankings
- 🖼️ **Image Optimization**: Next.js Image component for optimal loading
- 🛒 **Cart Management**: Real-time cart updates with state management
- 💳 **Payment Ready**: Integrates with Stripe, PayPal, and more
- 📱 **PWA Support**: Progressive Web App for offline functionality
- 🌐 **Multi-currency**: Support for international customers
- 🔐 **User Accounts**: Authentication and order history

## Tech Stack

- **Framework**: Next.js 14
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State Management**: Zustand
- **Data Fetching**: SWR
- **Commerce Backend**: Shopify/BigCommerce/Custom API
- **Payment**: Stripe Integration

## Quick Start

```bash
# Install dependencies
npm install

# Set up environment variables
cp .env.example .env.local
# Edit .env.local with your configuration

# Start development server
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

## Environment Variables

```env
# Store Configuration
NEXT_PUBLIC_STORE_NAME=Your Store
NEXT_PUBLIC_CURRENCY=USD

# Commerce Provider (shopify, bigcommerce, commercetools, custom)
COMMERCE_PROVIDER=shopify

# Shopify Configuration
SHOPIFY_STORE_DOMAIN=your-store.myshopify.com
SHOPIFY_STOREFRONT_API_TOKEN=your-token
SHOPIFY_ADMIN_API_TOKEN=your-admin-token

# Payment Provider
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...

# Analytics
NEXT_PUBLIC_GA_ID=G-XXXXXXXXXX
```

## Project Structure

```
src/
├── app/                     # Next.js App Router
│   ├── (shop)/             # Shop pages
│   │   ├── products/       # Product pages
│   │   ├── cart/           # Cart page
│   │   └── checkout/       # Checkout flow
│   ├── account/            # User account pages
│   └── api/                # API routes
├── components/
│   ├── product/            # Product components
│   ├── cart/               # Cart components
│   ├── checkout/           # Checkout components
│   └── ui/                 # Reusable UI components
├── lib/
│   ├── commerce/           # Commerce provider integration
│   ├── shopify/            # Shopify specific code
│   └── utils/              # Utility functions
└── types/                  # TypeScript types
```

## Key Features

### Product Listing Page (PLP)

```tsx
import { ProductGrid } from '@/components/product/ProductGrid'

export default function ProductsPage() {
  return (
    <div>
      <h1>All Products</h1>
      <ProductGrid
        products={products}
        sorting
        filtering
        pagination
      />
    </div>
  )
}
```

### Product Detail Page (PDP)

```tsx
import { ProductDetails } from '@/components/product/ProductDetails'
import { AddToCart } from '@/components/cart/AddToCart'

export default function ProductPage({ product }) {
  return (
    <div>
      <ProductDetails product={product} />
      <AddToCart product={product} />
    </div>
  )
}
```

### Shopping Cart

```tsx
import { useCart } from '@/hooks/useCart'

export function Cart() {
  const { items, updateQuantity, removeItem, total } = useCart()

  return (
    <div>
      {items.map(item => (
        <CartItem
          key={item.id}
          item={item}
          onUpdate={updateQuantity}
          onRemove={removeItem}
        />
      ))}
      <div>Total: ${total}</div>
    </div>
  )
}
```

## Commerce Provider Integration

### Shopify

This template uses Shopify's Storefront API for a headless commerce experience.

```typescript
import { getProduct } from '@/lib/shopify'

export async function getServerSideProps({ params }) {
  const product = await getProduct(params.slug)
  return { props: { product } }
}
```

### Custom Backend

To use a custom API:

1. Implement the commerce interface in `lib/commerce/`
2. Update the provider configuration
3. Ensure all required endpoints are available

## Payment Integration

### Stripe Checkout

```typescript
import { checkout } from '@/lib/stripe'

async function handleCheckout() {
  const session = await checkout({
    items: cartItems,
    successUrl: '/order/success',
    cancelUrl: '/cart',
  })

  window.location.href = session.url
}
```

## Performance Optimization

- **Image Optimization**: Uses `next/image` for automatic optimization
- **Code Splitting**: Automatic route-based code splitting
- **Static Generation**: Product pages pre-rendered at build time
- **Incremental Static Regeneration**: Pages update without full rebuild
- **Edge Caching**: Leverage CDN for faster content delivery

## SEO

```tsx
import { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Product Name | Your Store',
  description: 'Product description',
  openGraph: {
    images: ['/product-image.jpg'],
  },
}
```

## Analytics

Track e-commerce events:

```typescript
import { trackEvent } from '@/lib/analytics'

// Track product view
trackEvent('view_item', { product_id, product_name })

// Track add to cart
trackEvent('add_to_cart', { product_id, quantity })

// Track purchase
trackEvent('purchase', { transaction_id, value, items })
```

## Testing

```bash
# Run unit tests
npm test

# Run e2e tests
npm run test:e2e

# Run accessibility tests
npm run test:a11y
```

## Deployment

### Vercel (Recommended)

```bash
vercel deploy
```

### Docker

```bash
docker build -t nextjs-commerce .
docker run -p 3000:3000 nextjs-commerce
```

## License

MIT License
