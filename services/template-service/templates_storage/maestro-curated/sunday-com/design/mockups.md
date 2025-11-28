# Sunday.com - High-Fidelity Mockups

## Overview
This document presents high-fidelity visual mockups for key interfaces in Sunday.com. These mockups demonstrate the complete visual design, including colors, typography, spacing, and interactive states, based on our design system.

---

## Mockup 1: Dashboard Landing Page

### Visual Design Specifications

#### Layout Grid
- **Container**: Max-width 1280px, centered with 32px side margins
- **Grid System**: 12-column grid with 24px gutters
- **Vertical Rhythm**: 32px base spacing between major sections

#### Color Palette Applied
```css
Background: #f9fafb (--gray-50)
Cards: #ffffff with shadow-sm
Primary Actions: #3b82f6 (--primary-500)
Text Primary: #111827 (--gray-900)
Text Secondary: #6b7280 (--gray-500)
Success Indicators: #22c55e (--success-500)
Warning Indicators: #f59e0b (--warning-500)
Danger Indicators: #ef4444 (--danger-500)
```

### Detailed Mockup Description

#### Header Section (Height: 64px)
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ [LOGO] Sunday.com            [Search: "Type to search..."]  [🔔3] [👤Sarah] │
│ #3b82f6 brand blue           #f3f4f6 bg, border-gray-300   #6b7280  #111827  │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Typography:**
- Logo: Inter 24px, font-weight-700, color-primary-600
- Search: Inter 14px, font-weight-400, placeholder-gray-500
- User name: Inter 14px, font-weight-500, color-gray-900

**Interactive States:**
- Search focus: border-primary-500, ring-2 ring-primary-500/20
- Notification hover: bg-gray-100, scale-105 transform
- User avatar hover: ring-2 ring-primary-500

#### Navigation Bar (Height: 48px)
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 📊 Dashboard  📋 My Work  👥 Teams  📈 Reports  ⚙️ Settings                  │
│ [Active: bg-primary-50, text-primary-700, border-b-2 border-primary-500]    │
│ [Inactive: text-gray-600, hover:text-gray-900, hover:bg-gray-50]            │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Welcome Section
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Good morning, Sarah! 👋                                   Today: Dec 15, 2024│
│ Inter 24px, font-weight-600, color-gray-900              Inter 16px, gray-500│
│                                                                             │
│ Ready to tackle your goals? You have 3 high-priority tasks due today.      │
│ Inter 16px, font-weight-400, color-gray-600, line-height-6                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Stats Cards Section
```
┌─────────────────────────────────┐  ┌───────────────────────────────────┐
│ 📊 Quick Stats                  │  │ 🎯 Today's Priorities             │
│ bg-white, rounded-lg, p-6       │  │ bg-white, rounded-lg, p-6         │
│ shadow-sm, border border-gray-200│  │ shadow-sm, border border-gray-200 │
│                                 │  │                                   │
│ Projects: 12 active             │  │ ☐ Review Q4 Marketing Plan       │
│ Inter 32px, font-weight-700     │  │   checkbox-primary               │
│ color-gray-900                  │  │   Inter 16px, font-weight-500     │
│                                 │  │   Due: 2:00 PM (text-red-600)    │
│ Tasks: 47 in progress           │  │                                   │
│ Inter 16px, color-gray-600      │  │ ☐ Client Feedback Review          │
│                                 │  │   Inter 16px, font-weight-500     │
│ Team: 23 members                │  │   Due: 4:30 PM (text-amber-600)  │
│ Inter 16px, color-gray-600      │  │                                   │
│                                 │  │ ☐ Sprint Planning Meeting         │
│ Overdue: 3 items ⚠️             │  │   Inter 16px, font-weight-500     │
│ Inter 16px, color-red-600       │  │   Due: Tomorrow 10:00 AM          │
│ bg-red-50, px-2, py-1, rounded  │  │   (text-gray-600)                │
└─────────────────────────────────┘  └───────────────────────────────────┘
```

#### Activity Feed
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 📈 Recent Activity                                            View all →     │
│ Inter 18px, font-weight-600, color-gray-900                  text-primary-600│
│                                                                             │
│ 🟢 Marcus completed "API Integration Tests"                  2 minutes ago   │
│ w-3 h-3 bg-green-500 rounded-full                           text-gray-500   │
│ Inter 14px, color-gray-900                                   Inter 12px      │
│                                                                             │
│ 🔵 Emily updated design in "Login Component"                5 minutes ago   │
│ w-3 h-3 bg-blue-500 rounded-full                           text-gray-500   │
│                                                                             │
│ 🟠 New comment on "Database Optimization"                   12 minutes ago  │
│ w-3 h-3 bg-orange-500 rounded-full                         text-gray-500   │
│                                                                             │
│ 🔴 Project Alpha status changed to "At Risk"                1 hour ago      │
│ w-3 h-3 bg-red-500 rounded-full                            text-gray-500   │
│ bg-red-50 border-l-4 border-red-400 px-4 py-2 rounded      Inter 14px      │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Project Overview Section
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 📋 Active Projects                                          View All (12) → │
│ Inter 18px, font-weight-600, color-gray-900                text-primary-600 │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ Project Alpha        ██████████░░ 80%   ⚠️ At Risk    [View Details]   │ │
│ │ Inter 16px, font-600  progress-bar      bg-red-100     btn-primary-sm   │ │
│ │ color-gray-900       bg-red-500         text-red-700   px-3 py-1        │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ Mobile App Redesign  ████████████ 95%   🟢 On Track   [View Details]   │ │
│ │ progress-bar bg-green-500               bg-green-100   btn-primary-sm   │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ Q4 Marketing         ████████░░░░ 60%   🟡 Needs Attn [View Details]   │ │
│ │ progress-bar bg-amber-500               bg-amber-100   btn-primary-sm   │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Mockup 2: Kanban Board View

### Visual Design Specifications

#### Board Header
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 📋 Project Alpha / Frontend Development                                     │
│ Inter 24px, font-weight-700, color-gray-900                                │
│                                                                             │
│ [👥 Share] [⚙️ Settings] [📤 Export] [🔍 Filter]                            │
│ btn-secondary btn-secondary  btn-outline  btn-outline                      │
│ px-4 py-2     px-4 py-2     px-3 py-2    px-3 py-2                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### View Switcher
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ [📊 Table] [📋 Kanban] [📅 Timeline] [📈 Chart]                             │
│ btn-ghost   btn-primary  btn-ghost    btn-ghost                            │
│ Active: bg-primary-500, text-white, shadow-sm                              │
│ Inactive: text-gray-600, hover:text-gray-900, hover:bg-gray-100            │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Kanban Columns
```
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ 📝 Backlog  │ │ 🚧 In Prog  │ │ 👀 Review   │ │ ✅ Done     │
│   (12)      │ │    (8)      │ │    (5)      │ │    (23)     │
│ bg-gray-50  │ │ bg-blue-50  │ │ bg-amber-50 │ │ bg-green-50 │
│ rounded-lg  │ │ rounded-lg  │ │ rounded-lg  │ │ rounded-lg  │
│ p-4         │ │ p-4         │ │ p-4         │ │ p-4         │
│ min-h-96    │ │ min-h-96    │ │ min-h-96    │ │ min-h-96    │
├─────────────┤ ├─────────────┤ ├─────────────┤ ├─────────────┤
│ Task Cards  │ │ Task Cards  │ │ Task Cards  │ │ Task Cards  │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

#### Task Card Design
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 🎨 Login Design System Component                                           │
│ Inter 14px, font-weight-600, color-gray-900, line-height-5                 │
│                                                                             │
│ Create a comprehensive design system component for login interfaces...     │
│ Inter 12px, font-weight-400, color-gray-600, line-height-4, truncate-2     │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ 👤 Emily Watson        🔴 High Priority        📅 Due: Dec 17            │ │
│ │ avatar-sm              badge-red               text-xs text-gray-500     │ │
│ │ w-6 h-6 rounded-full   px-2 py-1 rounded       font-medium              │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ⏱️ 5.5h / 8h estimated    💬 3 comments    📎 2 attachments                │
│ text-xs text-gray-500     text-xs gray-500  text-xs text-gray-500          │
│                                                                             │
│ [Labels: 🎨 Design] [🔧 Frontend]                                          │
│ badge-blue px-2 py-1  badge-purple px-2 py-1                               │
│ rounded-full text-xs  rounded-full text-xs                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Card Interaction States:**
- **Hover**: shadow-md, scale-102 transform, cursor-pointer
- **Dragging**: shadow-lg, rotate-1 transform, opacity-90
- **Focus**: ring-2 ring-primary-500, ring-offset-2

---

## Mockup 3: Task Detail Modal

### Modal Design Specifications

#### Modal Overlay
```css
Background: rgba(0, 0, 0, 0.75) backdrop-blur-sm
z-index: 50
transition: opacity 200ms ease-out
```

#### Modal Container
```css
Background: #ffffff
Border radius: 12px (rounded-xl)
Shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25) (shadow-2xl)
Max width: 768px
Max height: 90vh
Overflow: auto
```

### Modal Content Layout

#### Header Section
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 🎨 Login Design System Component                            [✕ Close]       │
│ Inter 20px, font-weight-700, color-gray-900                 btn-ghost        │
│ px-6 py-4, border-b border-gray-200                         hover:bg-gray-100│
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Content Sections
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 📝 Description                                                              │
│ Inter 16px, font-weight-600, color-gray-900, mb-3                          │
│                                                                             │
│ Create a modern, accessible login design system component that includes:   │
│ Inter 14px, font-weight-400, color-gray-700, line-height-6                 │
│                                                                             │
│ • Form layouts and responsive breakpoints                                  │
│ • Input validation states and error messaging                              │
│ • Dark/light theme support with smooth transitions                         │
│ • WCAG 2.1 AA compliance for accessibility                                 │
│                                                                             │
│ [Edit Description]                                                          │
│ btn-outline-sm px-3 py-1 text-sm                                           │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ 📊 Task Details                                                             │
│                                                                             │
│ Status: 🚧 In Progress      Priority: 🔴 High         Assignee: 👤 Emily   │
│ badge-blue px-3 py-1       badge-red px-3 py-1       avatar + name         │
│                                                                             │
│ Due Date: 📅 Dec 17, 2024  Created: 📅 Dec 13, 2024  Project: Frontend    │
│ text-sm text-gray-600     text-sm text-gray-500      link-primary          │
│                                                                             │
│ Time: ⏱️ 5.5h / 8h est     Labels: 🎨 Design 🔧 Frontend                   │
│ progress-bar w-full       badge-collection                                  │
│ bg-gray-200 h-2          space-x-2                                          │
│ progress: bg-blue-500                                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Comments Section
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 💬 Comments (7)                                              [Latest ↓]    │
│ Inter 16px, font-weight-600, color-gray-900                 btn-ghost-sm    │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ 👤 Marcus Rodriguez • 2 hours ago                                       │ │
│ │ avatar-sm + name-link  text-xs text-gray-500                           │ │
│ │                                                                         │ │
│ │ Looks great! Just make sure the error states meet WCAG guidelines.      │ │
│ │ Inter 14px, color-gray-700, line-height-5                              │ │
│ │                                                                         │ │
│ │ @emily can you also include focus states for keyboard navigation?       │ │
│ │ mention: bg-blue-50, color-blue-700, px-1 rounded                      │ │
│ │                                                                         │ │
│ │ [👍 2] [💭 Reply]                                                        │ │
│ │ btn-ghost-xs  btn-ghost-xs                                              │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ 💭 Add a comment...                                      [📎] [Send]    │ │
│ │ textarea resize-none border border-gray-300 rounded-md   btn-primary    │ │
│ │ focus:border-primary-500 focus:ring-primary-500         px-3 py-2       │ │
│ │ placeholder-gray-400                                                    │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Mockup 4: Mobile Interface

### Mobile Design Specifications (375px width)

#### Header (Fixed)
```
┌─────────────────────────────┐
│ ☰ Sunday.com    🔍  🔔(2)   │
│ bg-white shadow-sm          │
│ px-4 py-3 fixed top-0       │
│ h-14 w-full z-40            │
└─────────────────────────────┘
```

#### Content Area
```
┌─────────────────────────────┐
│ 👋 Good morning, Emily!     │
│ Inter 20px, font-weight-600 │
│ px-4 pt-6 pb-2              │
│                             │
│ 🎯 Today's Tasks (3)        │
│ Inter 16px, font-weight-600 │
│ px-4 pb-3                   │
│                             │
│ ┌─────────────────────────┐ │
│ │ 🎨 Login Design         │ │
│ │ bg-white rounded-lg     │ │
│ │ p-4 shadow-sm           │ │
│ │ border border-gray-200  │ │
│ │                         │ │
│ │ Due: 2:00 PM           │ │
│ │ text-red-600 text-sm   │ │
│ │ font-medium            │ │
│ │                         │ │
│ │ 🔴 High Priority        │ │
│ │ badge-red inline-flex  │ │
│ │ px-2 py-1 rounded-full │ │
│ │                         │ │
│ │ [Start Timer] [Update] │ │
│ │ btn-primary-sm w-full  │ │
│ │ space-y-2              │ │
│ └─────────────────────────┘ │
│                             │
│ ┌─────────────────────────┐ │
│ │ 📊 Dashboard Analytics  │ │
│ │ Similar styling...      │ │
│ └─────────────────────────┘ │
└─────────────────────────────┘
```

#### Bottom Navigation (Fixed)
```
┌─────────────────────────────┐
│ ═══════════════════════════ │
│ 📊      📋      👥      ⚙️  │
│ Home   Tasks   Team   More  │
│ text-xs text-center        │
│ bg-white border-t           │
│ border-gray-200 fixed       │
│ bottom-0 w-full h-16        │
│ safe-bottom                 │
└─────────────────────────────┘
```

### Touch Interactions
- **Minimum touch target**: 44px x 44px (iOS guidelines)
- **Swipe gestures**: Left swipe to archive, right swipe for quick actions
- **Pull to refresh**: Refresh content with native feel
- **Haptic feedback**: Light feedback on button presses

---

## Mockup 5: Dark Mode Variations

### Dark Mode Color Palette
```css
Background: #111827 (--gray-900)
Cards: #1f2937 (--gray-800)
Text Primary: #f9fafb (--gray-50)
Text Secondary: #9ca3af (--gray-400)
Borders: #374151 (--gray-700)
Primary: #60a5fa (--primary-400) /* Lighter for better contrast */
```

### Dashboard in Dark Mode
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ [LOGO] Sunday.com              [Search]              [🔔3] [👤Sarah]       │
│ color-primary-400              bg-gray-800           text-gray-300          │
│ bg-gray-900                    border-gray-600                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ Good morning, Sarah! 👋                                Today: Dec 15, 2024  │
│ text-gray-50 font-weight-600                           text-gray-400        │
│                                                                             │
│ ┌─────────────────────────────────┐  ┌───────────────────────────────────┐ │
│ │ 📊 Quick Stats                  │  │ 🎯 Today's Priorities             │ │
│ │ bg-gray-800 border-gray-700     │  │ bg-gray-800 border-gray-700       │ │
│ │                                 │  │                                   │ │
│ │ Projects: 12 active             │  │ ☐ Review Q4 Marketing Plan       │ │
│ │ text-gray-50 font-weight-700    │  │   text-gray-200                   │ │
│ │                                 │  │   Due: 2:00 PM (text-red-400)    │ │
│ │ Tasks: 47 in progress           │  │                                   │ │
│ │ text-gray-400                   │  │ ☐ Client Feedback Review          │ │
│ │                                 │  │   text-gray-200                   │ │
│ │ Overdue: 3 items ⚠️             │  │   Due: 4:30 PM (text-amber-400)  │ │
│ │ text-red-400 bg-red-900/20      │  │                                   │ │
│ └─────────────────────────────────┘  └───────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Dark Mode Considerations
- **Contrast ratios**: Maintain WCAG AA compliance (4.5:1 for normal text)
- **Eye strain reduction**: Use pure black (#000000) sparingly, prefer dark grays
- **Color adjustments**: Semantic colors are lighter for better contrast
- **Image handling**: Apply subtle overlay or filter to maintain readability

---

## Interactive States & Micro-animations

### Button States
```css
/* Primary Button */
.btn-primary {
  background: #3b82f6;
  transition: all 150ms ease-out;
}

.btn-primary:hover {
  background: #2563eb;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
}

.btn-primary:active {
  transform: translateY(0);
  background: #1d4ed8;
}

.btn-primary:focus {
  outline: none;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.5);
}
```

### Card Hover Effects
```css
.card {
  transition: all 200ms ease-out;
  cursor: pointer;
}

.card:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
}
```

### Loading States
```css
.loading-skeleton {
  background: linear-gradient(90deg, #f3f4f6 25%, #e5e7eb 50%, #f3f4f6 75%);
  background-size: 200% 100%;
  animation: loading 1.5s infinite;
}

@keyframes loading {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

---

## Responsive Breakpoints

### Mobile First Approach
```css
/* Mobile (default) */
.container { padding: 16px; }
.grid { grid-template-columns: 1fr; }

/* Tablet (768px+) */
@media (min-width: 768px) {
  .container { padding: 24px; }
  .grid { grid-template-columns: repeat(2, 1fr); }
}

/* Desktop (1024px+) */
@media (min-width: 1024px) {
  .container { padding: 32px; }
  .grid { grid-template-columns: repeat(3, 1fr); }
}

/* Large Desktop (1280px+) */
@media (min-width: 1280px) {
  .container { max-width: 1280px; margin: 0 auto; }
  .grid { grid-template-columns: repeat(4, 1fr); }
}
```

### Component Adaptations
- **Navigation**: Hamburger menu on mobile, full nav on desktop
- **Cards**: Single column on mobile, grid on larger screens
- **Modals**: Full-screen on mobile, centered overlay on desktop
- **Tables**: Horizontal scroll on mobile, full table on desktop

---

## Accessibility Mockups

### High Contrast Mode
```css
@media (prefers-contrast: high) {
  :root {
    --gray-50: #ffffff;
    --gray-900: #000000;
    --primary-500: #0000ff;
    --border: #000000;
  }

  .card {
    border: 2px solid #000000;
  }

  button {
    border: 2px solid currentColor;
  }
}
```

### Reduced Motion
```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

### Focus Indicators
```css
.focus-visible {
  outline: 3px solid #3b82f6;
  outline-offset: 2px;
}

/* Skip link */
.skip-link {
  position: absolute;
  top: -40px;
  left: 6px;
  background: #3b82f6;
  color: white;
  padding: 8px;
  border-radius: 4px;
  text-decoration: none;
  transition: top 0.3s;
}

.skip-link:focus {
  top: 6px;
}
```

---

## Print Styles

### Print-Optimized Layouts
```css
@media print {
  body {
    font-size: 12pt;
    line-height: 1.5;
    color: #000000;
    background: #ffffff;
  }

  .no-print {
    display: none !important;
  }

  .print-break-before {
    page-break-before: always;
  }

  a[href]:after {
    content: " (" attr(href) ")";
  }

  .card {
    border: 1px solid #000000;
    box-shadow: none;
    margin-bottom: 1rem;
  }
}
```

---

## Implementation Notes

### CSS Custom Properties Usage
```css
:root {
  /* Spacing system */
  --space-unit: 4px;
  --space-xs: calc(var(--space-unit) * 1); /* 4px */
  --space-sm: calc(var(--space-unit) * 2); /* 8px */
  --space-md: calc(var(--space-unit) * 4); /* 16px */
  --space-lg: calc(var(--space-unit) * 6); /* 24px */
  --space-xl: calc(var(--space-unit) * 8); /* 32px */

  /* Typography scale */
  --font-size-xs: 0.75rem;
  --font-size-sm: 0.875rem;
  --font-size-base: 1rem;
  --font-size-lg: 1.125rem;
  --font-size-xl: 1.25rem;
  --font-size-2xl: 1.5rem;
  --font-size-3xl: 1.875rem;
  --font-size-4xl: 2.25rem;

  /* Border radius */
  --radius-sm: 0.125rem;
  --radius-base: 0.25rem;
  --radius-md: 0.375rem;
  --radius-lg: 0.5rem;
  --radius-xl: 0.75rem;
}
```

### Component API Examples
```jsx
// Button component usage
<Button
  variant="primary"
  size="lg"
  leftIcon={<PlusIcon />}
  loading={isSubmitting}
  onClick={handleSubmit}
>
  Create Project
</Button>

// Card component with different states
<Card className="hover:shadow-md transition-shadow">
  <CardHeader>
    <CardTitle>Project Status</CardTitle>
  </CardHeader>
  <CardContent>
    <ProgressBar value={75} max={100} />
  </CardContent>
</Card>
```

---

*Document Version: 1.0*
*Created: December 2024*
*Next Review: Q1 2025*