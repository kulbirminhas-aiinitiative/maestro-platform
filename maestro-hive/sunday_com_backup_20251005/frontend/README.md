# Sunday.com Frontend

A modern React frontend for the Sunday.com work management platform built with TypeScript, Vite, and Tailwind CSS.

## 🚀 Features

- **Modern React 18** with TypeScript for type safety
- **Vite** for fast development and optimized builds
- **Tailwind CSS** with custom design system
- **Framer Motion** for smooth animations
- **React Query** for efficient server state management
- **Zustand** for client-side state management
- **React Hook Form** with Zod validation
- **React Router** for client-side routing
- **Jest & React Testing Library** for comprehensive testing
- **ESLint & Prettier** for code quality
- **Responsive design** with mobile-first approach

## 📁 Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── ui/             # Base UI components (Button, Input, etc.)
│   └── layout/         # Layout components (Header, Sidebar, etc.)
├── pages/              # Page components
│   ├── auth/          # Authentication pages
│   └── ...            # Other page directories
├── hooks/              # Custom React hooks
├── lib/                # Utility libraries
│   ├── api.ts         # API client
│   ├── utils.ts       # General utilities
│   └── constants.ts   # App constants
├── store/              # Zustand stores
├── styles/             # Global styles
├── types/              # TypeScript type definitions
└── test/               # Test utilities and setup
```

## 🛠️ Tech Stack

### Core Framework
- **React 18.2** - UI library with concurrent features
- **TypeScript 5.3** - Type safety and developer experience
- **Vite 5.0** - Build tool and dev server

### UI & Styling
- **Tailwind CSS 3.3** - Utility-first CSS framework
- **Radix UI** - Unstyled, accessible UI primitives
- **Lucide React** - Beautiful SVG icons
- **Framer Motion** - Animation library

### State Management
- **Zustand** - Lightweight state management
- **React Query** - Server state management
- **React Hook Form** - Form state management

### Development Tools
- **ESLint** - Code linting
- **Prettier** - Code formatting
- **Jest** - Testing framework
- **React Testing Library** - Component testing utilities

## 🚦 Getting Started

### Prerequisites

- Node.js 18+
- npm 8+

### Installation

1. **Install dependencies**
   ```bash
   npm install
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env.local
   ```

   Update the environment variables:
   ```env
   VITE_API_URL=http://localhost:3000
   VITE_APP_URL=http://localhost:3001
   ```

3. **Start the development server**
   ```bash
   npm run dev
   ```

4. **Open in browser**

   Navigate to [http://localhost:3001](http://localhost:3001)

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run test` - Run tests
- `npm run test:watch` - Run tests in watch mode
- `npm run test:coverage` - Run tests with coverage
- `npm run lint` - Lint code
- `npm run lint:fix` - Fix linting issues
- `npm run type-check` - Check TypeScript types

## 🎨 Design System

### Colors

The app uses a semantic color system:

- **Primary**: Blue tones for primary actions
- **Success**: Green tones for positive states
- **Warning**: Yellow/orange tones for warnings
- **Danger**: Red tones for errors/destructive actions
- **Muted**: Gray tones for secondary content

### Typography

- **Font Family**: Inter (primary), JetBrains Mono (monospace)
- **Font Sizes**: Responsive scale from xs to 4xl
- **Font Weights**: 300, 400, 500, 600, 700

### Components

All UI components follow consistent patterns:

- **Variants**: Different visual styles (default, outline, ghost, etc.)
- **Sizes**: Multiple size options (sm, md, lg, xl)
- **States**: Loading, disabled, error states
- **Accessibility**: ARIA labels, keyboard navigation, screen reader support

## 🔧 Configuration

### Path Aliases

The project uses TypeScript path mapping for cleaner imports:

```typescript
// Instead of: import { Button } from '../../../components/ui/Button'
import { Button } from '@/components/ui/Button'
```

Available aliases:
- `@/*` → `src/*`
- `@/components/*` → `src/components/*`
- `@/hooks/*` → `src/hooks/*`
- `@/lib/*` → `src/lib/*`
- `@/types/*` → `src/types/*`

### API Integration

The frontend communicates with the backend via:

- **REST API** for standard CRUD operations
- **WebSocket** for real-time updates
- **GraphQL** for complex queries (planned)

## 🧪 Testing

### Test Structure

```
src/
├── components/
│   └── ui/
│       └── __tests__/
│           └── Button.test.tsx
└── test/
    └── setup.ts
```

### Writing Tests

```typescript
import { render, screen, fireEvent } from '@testing-library/react'
import { Button } from '../Button'

describe('Button', () => {
  it('renders correctly', () => {
    render(<Button>Click me</Button>)
    expect(screen.getByRole('button', { name: 'Click me' })).toBeInTheDocument()
  })
})
```

### Test Coverage

The project aims for:
- **80%+ code coverage** overall
- **90%+ coverage** for utility functions
- **70%+ coverage** for components

## 🔒 Authentication

The frontend implements JWT-based authentication:

1. **Login/Register** - User credentials are sent to backend
2. **Token Storage** - JWT tokens stored securely in localStorage
3. **Auto-refresh** - Tokens are automatically refreshed
4. **Route Protection** - Private routes require authentication

## 📱 Responsive Design

The app is designed mobile-first with breakpoints:

- **Mobile**: < 768px
- **Tablet**: 768px - 1024px
- **Desktop**: > 1024px

Key responsive features:
- Collapsible sidebar on mobile
- Touch-friendly interactions
- Optimized layouts for different screen sizes

## 🎯 Performance

### Optimization Strategies

- **Code Splitting** - Route-based and component-based splitting
- **Lazy Loading** - Components and images loaded on demand
- **Memoization** - React.memo and useMemo for expensive operations
- **Bundle Analysis** - Vite bundle analyzer for optimization insights

### Performance Targets

- **First Contentful Paint**: < 1.5s
- **Largest Contentful Paint**: < 2.5s
- **Cumulative Layout Shift**: < 0.1
- **First Input Delay**: < 100ms

## 🚀 Deployment

### Build Process

```bash
# Type check
npm run type-check

# Run tests
npm run test

# Build for production
npm run build

# Preview build
npm run preview
```

### Environment Variables

Production environment variables:

```env
VITE_API_URL=https://api.sunday.com
VITE_APP_URL=https://app.sunday.com
```

## 🤝 Contributing

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make changes and test**: `npm run test`
4. **Commit changes**: `git commit -m 'Add amazing feature'`
5. **Push to branch**: `git push origin feature/amazing-feature`
6. **Open a Pull Request**

### Code Style

- Use TypeScript for all new code
- Follow ESLint and Prettier configurations
- Write tests for new components and utilities
- Use semantic commit messages

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For questions and support:

- **Documentation**: Check this README and inline code comments
- **Issues**: Create a GitHub issue for bugs or feature requests
- **Discussions**: Use GitHub Discussions for questions

---

Built with ❤️ by the Sunday.com Team