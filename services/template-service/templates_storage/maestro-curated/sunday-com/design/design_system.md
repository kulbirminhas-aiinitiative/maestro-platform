# Sunday.com Design System

## Overview
The Sunday.com Design System is a comprehensive collection of reusable components, design tokens, and guidelines that ensure consistent user experiences across all platforms. Built on Tailwind CSS with custom extensions, it provides a scalable foundation for modern work management interfaces.

---

## Design Principles

### 1. Clarity & Simplicity
- **Clear Information Hierarchy**: Use typography, spacing, and color to guide user attention
- **Minimal Cognitive Load**: Reduce visual clutter and present information progressively
- **Intuitive Interactions**: Familiar patterns and predictable behaviors

### 2. Accessibility First
- **WCAG 2.1 AA Compliance**: Meet or exceed accessibility standards
- **Inclusive Design**: Support diverse users, abilities, and technologies
- **Universal Usability**: Ensure functionality across devices and input methods

### 3. Performance & Efficiency
- **Fast Loading**: Optimize assets and minimize bundle size
- **Smooth Interactions**: 60fps animations and responsive feedback
- **Efficient Workflows**: Reduce steps to complete common tasks

### 4. Consistency & Cohesion
- **Systematic Approach**: Reusable components and predictable patterns
- **Brand Alignment**: Consistent visual identity and tone
- **Cross-Platform Harmony**: Unified experience across web and mobile

---

## Color System

### Core Palette

#### Primary Colors
```css
/* Blue - Primary brand color */
--primary-50: #eff6ff
--primary-100: #dbeafe
--primary-200: #bfdbfe
--primary-300: #93c5fd
--primary-400: #60a5fa
--primary-500: #3b82f6  /* Primary */
--primary-600: #2563eb
--primary-700: #1d4ed8
--primary-800: #1e40af
--primary-900: #1e3a8a
```

#### Semantic Colors
```css
/* Success - Green */
--success-50: #f0fdf4
--success-100: #dcfce7
--success-200: #bbf7d0
--success-300: #86efac
--success-400: #4ade80
--success-500: #22c55e  /* Success base */
--success-600: #16a34a
--success-700: #15803d
--success-800: #166534
--success-900: #14532d

/* Warning - Amber */
--warning-50: #fffbeb
--warning-100: #fef3c7
--warning-200: #fde68a
--warning-300: #fcd34d
--warning-400: #fbbf24
--warning-500: #f59e0b  /* Warning base */
--warning-600: #d97706
--warning-700: #b45309
--warning-800: #92400e
--warning-900: #78350f

/* Danger - Red */
--danger-50: #fef2f2
--danger-100: #fee2e2
--danger-200: #fecaca
--danger-300: #fca5a5
--danger-400: #f87171
--danger-500: #ef4444  /* Danger base */
--danger-600: #dc2626
--danger-700: #b91c1c
--danger-800: #991b1b
--danger-900: #7f1d1d
```

#### Neutral Colors
```css
/* Grayscale - Base for text and backgrounds */
--gray-50: #f9fafb
--gray-100: #f3f4f6
--gray-200: #e5e7eb
--gray-300: #d1d5db
--gray-400: #9ca3af
--gray-500: #6b7280
--gray-600: #4b5563
--gray-700: #374151
--gray-800: #1f2937
--gray-900: #111827
```

### Color Usage Guidelines

#### Text Colors
- **Primary Text**: `--gray-900` (light) / `--gray-100` (dark)
- **Secondary Text**: `--gray-600` (light) / `--gray-400` (dark)
- **Muted Text**: `--gray-500` (light) / `--gray-500` (dark)
- **Link Text**: `--primary-600` with hover states

#### Background Colors
- **Page Background**: `--gray-50` (light) / `--gray-900` (dark)
- **Card Background**: `white` (light) / `--gray-800` (dark)
- **Input Background**: `white` (light) / `--gray-700` (dark)

#### Interactive Colors
- **Hover States**: Reduce opacity by 10% or shift shade by 100
- **Active States**: Reduce opacity by 20% or shift shade by 200
- **Focus States**: Use `--primary-500` with 2px ring

---

## Typography

### Font Stack
```css
/* Primary font - Inter */
font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;

/* Monospace font - JetBrains Mono */
font-family: 'JetBrains Mono', 'Fira Code', Consolas, 'Courier New', monospace;
```

### Type Scale

#### Headings
```css
/* Heading 1 - Page titles */
.text-h1 {
  font-size: 2.25rem;    /* 36px */
  line-height: 2.5rem;   /* 40px */
  font-weight: 700;      /* Bold */
  letter-spacing: -0.025em;
}

/* Heading 2 - Section titles */
.text-h2 {
  font-size: 1.875rem;   /* 30px */
  line-height: 2.25rem;  /* 36px */
  font-weight: 600;      /* Semi-bold */
  letter-spacing: -0.025em;
}

/* Heading 3 - Subsection titles */
.text-h3 {
  font-size: 1.5rem;     /* 24px */
  line-height: 2rem;     /* 32px */
  font-weight: 600;      /* Semi-bold */
}

/* Heading 4 - Component titles */
.text-h4 {
  font-size: 1.25rem;    /* 20px */
  line-height: 1.75rem;  /* 28px */
  font-weight: 600;      /* Semi-bold */
}

/* Heading 5 - Card titles */
.text-h5 {
  font-size: 1.125rem;   /* 18px */
  line-height: 1.75rem;  /* 28px */
  font-weight: 600;      /* Semi-bold */
}

/* Heading 6 - Small titles */
.text-h6 {
  font-size: 1rem;       /* 16px */
  line-height: 1.5rem;   /* 24px */
  font-weight: 600;      /* Semi-bold */
}
```

#### Body Text
```css
/* Large body text */
.text-lg {
  font-size: 1.125rem;   /* 18px */
  line-height: 1.75rem;  /* 28px */
  font-weight: 400;      /* Regular */
}

/* Regular body text */
.text-base {
  font-size: 1rem;       /* 16px */
  line-height: 1.5rem;   /* 24px */
  font-weight: 400;      /* Regular */
}

/* Small body text */
.text-sm {
  font-size: 0.875rem;   /* 14px */
  line-height: 1.25rem;  /* 20px */
  font-weight: 400;      /* Regular */
}

/* Extra small text */
.text-xs {
  font-size: 0.75rem;    /* 12px */
  line-height: 1rem;     /* 16px */
  font-weight: 400;      /* Regular */
}
```

#### Specialized Text
```css
/* Code text */
.text-code {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.875rem;   /* 14px */
  line-height: 1.25rem;  /* 20px */
  font-weight: 400;      /* Regular */
}

/* Caption text */
.text-caption {
  font-size: 0.75rem;    /* 12px */
  line-height: 1rem;     /* 16px */
  font-weight: 500;      /* Medium */
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
```

---

## Spacing System

### Spacing Scale
Based on 4px base unit for consistent rhythm:

```css
/* Spacing values */
--space-0: 0px
--space-1: 4px      /* 0.25rem */
--space-2: 8px      /* 0.5rem */
--space-3: 12px     /* 0.75rem */
--space-4: 16px     /* 1rem */
--space-5: 20px     /* 1.25rem */
--space-6: 24px     /* 1.5rem */
--space-8: 32px     /* 2rem */
--space-10: 40px    /* 2.5rem */
--space-12: 48px    /* 3rem */
--space-16: 64px    /* 4rem */
--space-20: 80px    /* 5rem */
--space-24: 96px    /* 6rem */
--space-32: 128px   /* 8rem */
```

### Usage Guidelines

#### Component Spacing
- **Button Padding**: `px-4 py-2` (16px horizontal, 8px vertical)
- **Card Padding**: `p-6` (24px all sides)
- **Form Spacing**: `space-y-4` (16px vertical gap)
- **Section Spacing**: `space-y-8` (32px vertical gap)

#### Layout Spacing
- **Page Margins**: `mx-4` on mobile, `mx-8` on desktop
- **Container Max Width**: `max-w-7xl` (1280px)
- **Grid Gaps**: `gap-4` (16px) for cards, `gap-6` (24px) for sections

---

## Elevation & Shadows

### Shadow Scale
```css
/* Elevation levels */
.shadow-xs {
  box-shadow: 0 1px 2px 0 rgb(0 0 0 / 0.05);
}

.shadow-sm {
  box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1);
}

.shadow-md {
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
}

.shadow-lg {
  box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
}

.shadow-xl {
  box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1);
}

.shadow-2xl {
  box-shadow: 0 25px 50px -12px rgb(0 0 0 / 0.25);
}
```

### Usage Guidelines
- **Cards**: `shadow-sm` for standard cards, `shadow-md` for hover
- **Modals**: `shadow-xl` for modal overlays
- **Dropdowns**: `shadow-lg` for dropdown menus
- **Tooltips**: `shadow-md` for tooltip containers

---

## Border Radius

### Radius Scale
```css
/* Border radius values */
--radius-none: 0px
--radius-sm: 2px      /* 0.125rem */
--radius-base: 4px    /* 0.25rem */
--radius-md: 6px      /* 0.375rem */
--radius-lg: 8px      /* 0.5rem */
--radius-xl: 12px     /* 0.75rem */
--radius-2xl: 16px    /* 1rem */
--radius-3xl: 24px    /* 1.5rem */
--radius-full: 9999px /* Full circle */
```

### Usage Guidelines
- **Buttons**: `rounded-md` (6px)
- **Cards**: `rounded-lg` (8px)
- **Inputs**: `rounded-md` (6px)
- **Modals**: `rounded-xl` (12px)
- **Avatars**: `rounded-full` (circle)

---

## Component Library

### Buttons

#### Primary Button
```jsx
<Button variant="default" size="default">
  Primary Action
</Button>
```

#### Secondary Button
```jsx
<Button variant="secondary" size="default">
  Secondary Action
</Button>
```

#### Destructive Button
```jsx
<Button variant="destructive" size="default">
  Delete Item
</Button>
```

#### Icon Button
```jsx
<Button variant="ghost" size="icon">
  <PlusIcon className="h-4 w-4" />
</Button>
```

### Form Controls

#### Input Field
```jsx
<Input
  type="text"
  placeholder="Enter project name..."
  className="w-full"
/>
```

#### Select Dropdown
```jsx
<Select>
  <SelectTrigger>
    <SelectValue placeholder="Choose priority..." />
  </SelectTrigger>
  <SelectContent>
    <SelectItem value="high">High Priority</SelectItem>
    <SelectItem value="medium">Medium Priority</SelectItem>
    <SelectItem value="low">Low Priority</SelectItem>
  </SelectContent>
</Select>
```

#### Checkbox
```jsx
<div className="flex items-center space-x-2">
  <Checkbox id="task-complete" />
  <label htmlFor="task-complete">Mark as complete</label>
</div>
```

### Layout Components

#### Card
```jsx
<Card>
  <CardHeader>
    <CardTitle>Project Overview</CardTitle>
    <CardDescription>Track your project progress</CardDescription>
  </CardHeader>
  <CardContent>
    {/* Card content */}
  </CardContent>
</Card>
```

#### Badge
```jsx
<Badge variant="success">Completed</Badge>
<Badge variant="warning">In Progress</Badge>
<Badge variant="destructive">Overdue</Badge>
```

#### Avatar
```jsx
<Avatar>
  <AvatarImage src="/user-avatar.jpg" alt="User Name" />
  <AvatarFallback>UN</AvatarFallback>
</Avatar>
```

---

## Icons

### Icon System
Using Lucide React for consistent, scalable icons:

#### Standard Sizes
```jsx
// Small icons (16px)
<Icon className="h-4 w-4" />

// Medium icons (20px)
<Icon className="h-5 w-5" />

// Large icons (24px)
<Icon className="h-6 w-6" />

// Extra large icons (32px)
<Icon className="h-8 w-8" />
```

#### Common Icons
- **Navigation**: `Home`, `Search`, `Settings`, `Menu`
- **Actions**: `Plus`, `Edit`, `Trash2`, `Download`, `Share`
- **Status**: `Check`, `X`, `AlertTriangle`, `Info`, `Clock`
- **Media**: `Play`, `Pause`, `Stop`, `Upload`, `Image`
- **Communication**: `MessageSquare`, `Mail`, `Phone`, `Video`

---

## Animation & Motion

### Motion Principles
1. **Purposeful**: Every animation serves a functional purpose
2. **Performant**: 60fps animations using CSS transforms
3. **Natural**: Easing curves that feel organic and responsive
4. **Respectful**: Honor `prefers-reduced-motion` settings

### Timing Functions
```css
/* Standard easing curves */
--ease-in: cubic-bezier(0.4, 0, 1, 1)
--ease-out: cubic-bezier(0, 0, 0.2, 1)
--ease-in-out: cubic-bezier(0.4, 0, 0.2, 1)

/* Custom curves */
--ease-spring: cubic-bezier(0.175, 0.885, 0.32, 1.275)
--ease-bounce: cubic-bezier(0.68, -0.55, 0.265, 1.55)
```

### Duration Scale
```css
/* Animation durations */
--duration-fast: 150ms     /* Quick transitions */
--duration-normal: 250ms   /* Standard transitions */
--duration-slow: 350ms     /* Complex animations */
--duration-slower: 500ms   /* Page transitions */
```

### Common Animations

#### Hover Effects
```css
.hover-lift {
  transition: transform 150ms ease-out;
}

.hover-lift:hover {
  transform: translateY(-2px);
}
```

#### Loading States
```css
.loading-pulse {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
```

#### Entrance Animations
```css
.fade-in {
  animation: fadeIn 250ms ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
```

---

## Responsive Design

### Breakpoint System
```css
/* Mobile first approach */
@media (min-width: 640px) { /* sm */ }
@media (min-width: 768px) { /* md */ }
@media (min-width: 1024px) { /* lg */ }
@media (min-width: 1280px) { /* xl */ }
@media (min-width: 1536px) { /* 2xl */ }
```

### Responsive Patterns

#### Grid Systems
```jsx
// Responsive grid
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
  {/* Grid items */}
</div>

// Auto-fit grid
<div className="grid grid-cols-auto-fit gap-4" style={{gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))'}}>
  {/* Auto-sizing items */}
</div>
```

#### Typography Scaling
```jsx
// Responsive text sizes
<h1 className="text-2xl md:text-3xl lg:text-4xl font-bold">
  Responsive Heading
</h1>

// Responsive line height
<p className="text-sm md:text-base leading-relaxed md:leading-loose">
  Responsive paragraph text
</p>
```

#### Spacing Adjustments
```jsx
// Responsive spacing
<div className="p-4 md:p-6 lg:p-8">
  <div className="space-y-4 md:space-y-6 lg:space-y-8">
    {/* Content with responsive spacing */}
  </div>
</div>
```

---

## Dark Mode

### Implementation
Sunday.com supports automatic dark mode based on system preference or manual toggle:

```jsx
// Dark mode toggle
const [darkMode, setDarkMode] = useState(false)

useEffect(() => {
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
  setDarkMode(mediaQuery.matches)

  const handler = (e) => setDarkMode(e.matches)
  mediaQuery.addEventListener('change', handler)

  return () => mediaQuery.removeEventListener('change', handler)
}, [])
```

### Color Adaptations
All components automatically adapt to dark mode using CSS custom properties:

```css
/* Light mode */
:root {
  --background: 255 255 255;
  --foreground: 15 23 42;
}

/* Dark mode */
.dark {
  --background: 15 23 42;
  --foreground: 248 250 252;
}
```

---

## Accessibility

### WCAG 2.1 AA Compliance

#### Color Contrast
- **Normal text**: 4.5:1 minimum contrast ratio
- **Large text**: 3:1 minimum contrast ratio
- **Interactive elements**: 3:1 minimum contrast ratio

#### Keyboard Navigation
- **Focus indicators**: Visible 2px outline on all interactive elements
- **Tab order**: Logical tab sequence through interface
- **Shortcuts**: Common keyboard shortcuts (Cmd/Ctrl+S for save, etc.)

#### Screen Reader Support
- **Semantic HTML**: Proper heading hierarchy, landmarks, and roles
- **ARIA labels**: Descriptive labels for complex interactions
- **Live regions**: Announce dynamic content changes

### Accessibility Features

#### High Contrast Mode
```css
@media (prefers-contrast: high) {
  :root {
    --border: 0 0% 0%;
    --ring: 0 0% 0%;
  }
}
```

#### Reduced Motion
```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

#### Focus Management
```jsx
// Focus trap for modals
import { useFocusTrap } from '@/hooks/useFocusTrap'

const Modal = ({ isOpen, children }) => {
  const focusTrapRef = useFocusTrap(isOpen)

  return (
    <div ref={focusTrapRef} role="dialog" aria-modal="true">
      {children}
    </div>
  )
}
```

---

## Performance Guidelines

### Asset Optimization
1. **Images**: Use WebP format with fallbacks, implement lazy loading
2. **Icons**: Use SVG icons, optimize with SVGO
3. **Fonts**: Preload critical fonts, use font-display: swap

### Component Performance
1. **React.memo**: Memoize expensive components
2. **useMemo/useCallback**: Optimize expensive calculations
3. **Code splitting**: Lazy load routes and components

### CSS Optimization
1. **Purge unused styles**: Tailwind CSS purging in production
2. **Critical CSS**: Inline critical styles for above-the-fold content
3. **CSS-in-JS**: Use for dynamic styles only

---

## Design Tokens

### Implementation
Design tokens are implemented as CSS custom properties and exported as JavaScript objects:

```javascript
// tokens/colors.js
export const colors = {
  primary: {
    50: '#eff6ff',
    100: '#dbeafe',
    500: '#3b82f6',
    900: '#1e3a8a'
  },
  semantic: {
    success: '#22c55e',
    warning: '#f59e0b',
    danger: '#ef4444'
  }
}

// tokens/spacing.js
export const spacing = {
  0: '0px',
  1: '4px',
  2: '8px',
  4: '16px',
  6: '24px',
  8: '32px'
}
```

### Usage in Components
```jsx
import { colors, spacing } from '@/design-tokens'

const StyledComponent = {
  backgroundColor: colors.primary[500],
  padding: spacing[4],
  margin: spacing[2]
}
```

---

## Component Development Guidelines

### File Structure
```
components/
├── ui/                    # Base UI components
│   ├── Button.tsx
│   ├── Input.tsx
│   └── Card.tsx
├── layout/                # Layout components
│   ├── Header.tsx
│   ├── Sidebar.tsx
│   └── Footer.tsx
├── feature/               # Feature-specific components
│   ├── TaskCard.tsx
│   ├── ProjectBoard.tsx
│   └── UserProfile.tsx
└── __tests__/             # Component tests
    ├── Button.test.tsx
    └── Card.test.tsx
```

### Component API Design
```tsx
interface ComponentProps {
  // Required props first
  title: string

  // Optional props with defaults
  variant?: 'primary' | 'secondary'
  size?: 'sm' | 'md' | 'lg'
  disabled?: boolean

  // Event handlers
  onClick?: (event: MouseEvent) => void

  // Composition
  children?: ReactNode

  // Styling flexibility
  className?: string
}
```

### Testing Guidelines
1. **Unit tests**: Test component logic and behavior
2. **Integration tests**: Test component interactions
3. **Visual regression**: Storybook visual testing
4. **Accessibility tests**: Automated a11y testing

---

## Documentation Standards

### Storybook Stories
Each component should have comprehensive Storybook stories:

```jsx
// Button.stories.tsx
export default {
  title: 'UI/Button',
  component: Button,
  parameters: {
    docs: {
      description: {
        component: 'A versatile button component with multiple variants and sizes.'
      }
    }
  }
}

export const Primary = {
  args: {
    variant: 'primary',
    children: 'Primary Button'
  }
}

export const AllVariants = () => (
  <div className="space-x-4">
    <Button variant="primary">Primary</Button>
    <Button variant="secondary">Secondary</Button>
    <Button variant="destructive">Destructive</Button>
  </div>
)
```

### Code Comments
```tsx
/**
 * Button component with multiple variants and sizes
 *
 * @param variant - Visual style variant
 * @param size - Button size
 * @param disabled - Disabled state
 * @param loading - Loading state with spinner
 * @param children - Button content
 */
export const Button = ({ variant, size, disabled, loading, children }: ButtonProps) => {
  // Implementation
}
```

---

## Version Control & Updates

### Semantic Versioning
- **Major**: Breaking changes to component APIs
- **Minor**: New components or non-breaking features
- **Patch**: Bug fixes and minor improvements

### Change Management
1. **RFC Process**: Propose significant changes through RFC documents
2. **Migration Guides**: Provide clear upgrade paths for breaking changes
3. **Deprecation Warnings**: Give teams time to migrate from deprecated components

### Release Process
1. **Development**: Feature branches with component updates
2. **Testing**: Comprehensive testing including visual regression
3. **Documentation**: Update Storybook and documentation
4. **Release**: Automated releases with changelog generation

---

*Document Version: 1.0*
*Created: December 2024*
*Next Review: Q1 2025*