# Tailwind Admin Dashboard

Professional admin dashboard UI built with Tailwind CSS and React. Features modern application shell, responsive sidebar navigation, data tables, forms, and comprehensive CRUD interfaces.

## Features

- ✨ **Modern Design**: Clean, professional interface built with Tailwind CSS
- 📱 **Responsive**: Mobile-first design that works on all devices
- 🎨 **Dark Mode**: Built-in dark mode support
- 🔐 **Authentication**: Pre-built login, register, and password reset pages
- 📊 **Data Tables**: Sortable, filterable tables with pagination
- 📝 **Forms**: Comprehensive form components with validation
- 🎯 **TypeScript**: Full type safety and IntelliSense support
- ⚡ **Fast**: Built with Vite for lightning-fast development

## Tech Stack

- **Framework**: React 18
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Icons**: Heroicons
- **UI Components**: Headless UI
- **Routing**: React Router v6
- **Build Tool**: Vite

## Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Project Structure

```
src/
├── components/           # Reusable UI components
│   ├── layout/          # Layout components (Sidebar, Header, etc.)
│   ├── forms/           # Form components
│   ├── tables/          # Data table components
│   └── ui/              # Basic UI elements (Button, Input, etc.)
├── pages/               # Page components
│   ├── dashboard/       # Dashboard pages
│   ├── auth/            # Authentication pages
│   └── users/           # User management pages
├── hooks/               # Custom React hooks
├── utils/               # Utility functions
├── types/               # TypeScript type definitions
└── App.tsx              # Main application component
```

## Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
VITE_APP_TITLE=Admin Dashboard
VITE_API_BASE_URL=http://localhost:8000/api
VITE_ENABLE_AUTH=true
VITE_ENABLE_DARK_MODE=true
```

### Tailwind Configuration

Customize the theme in `tailwind.config.js`:

```js
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          // ... your brand colors
        },
      },
    },
  },
}
```

## Usage Examples

### Creating a CRUD Page

```tsx
import { DataTable } from '@/components/tables/DataTable'
import { Button } from '@/components/ui/Button'

export function UsersPage() {
  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Users</h1>
        <Button>Add User</Button>
      </div>
      <DataTable
        columns={columns}
        data={users}
        searchable
        pagination
      />
    </div>
  )
}
```

### Adding Authentication

```tsx
import { useAuth } from '@/hooks/useAuth'

export function ProtectedPage() {
  const { user, logout } = useAuth()

  return (
    <div>
      <p>Welcome, {user.name}!</p>
      <Button onClick={logout}>Logout</Button>
    </div>
  )
}
```

## Customization

### Adding New Pages

1. Create a new component in `src/pages/`
2. Add route in `src/App.tsx`
3. Update navigation in `src/components/layout/Sidebar.tsx`

### Styling Guidelines

- Use Tailwind utility classes for styling
- Create custom components for reusable patterns
- Follow mobile-first responsive design
- Use dark mode classes: `dark:bg-gray-800`

## Deployment

### Build for Production

```bash
npm run build
```

The build output will be in the `dist/` directory.

### Deploy to Vercel

```bash
vercel deploy
```

### Deploy to Netlify

```bash
netlify deploy --prod
```

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Support

For issues and questions:
- Check the [documentation](docs/)
- Review [examples](examples/)
- Open an issue on GitHub
