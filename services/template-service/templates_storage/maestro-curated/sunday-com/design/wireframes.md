# Sunday.com - Wireframes

## Overview
This document presents wireframes for key user flows in Sunday.com, focusing on user experience and information architecture. Wireframes are organized by user flow and include annotations for functionality and behavior.

---

## Wireframe 1: Dashboard Landing Page

### Layout Structure
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ SUNDAY.COM                                    🔍 Search    🔔 (3)   👤 Sarah │
├─────────────────────────────────────────────────────────────────────────────┤
│ 📊 Dashboard  📋 My Work  👥 Teams  📈 Reports  ⚙️ Settings                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ Good morning, Sarah! 👋                     Today: Dec 15, 2024             │
│                                                                             │
│ ┌─────────────────────────────────┐  ┌───────────────────────────────────┐ │
│ │ 📊 Quick Stats                  │  │ 🎯 Today's Priorities             │ │
│ │                                 │  │                                   │ │
│ │ Projects: 12 active             │  │ ☐ Review Q4 Marketing Plan       │ │
│ │ Tasks: 47 in progress           │  │   Due: 2:00 PM                    │ │
│ │ Team: 23 members                │  │                                   │ │
│ │ Overdue: 3 items ⚠️             │  │ ☐ Client Feedback Review          │ │
│ │                                 │  │   Due: 4:30 PM                    │ │
│ └─────────────────────────────────┘  │                                   │ │
│                                      │ ☐ Sprint Planning Meeting         │ │
│ ┌─────────────────────────────────┐  │   Due: Tomorrow 10:00 AM          │ │
│ │ 📈 Recent Activity              │  │                                   │ │
│ │                                 │  │ + Add Priority                    │ │
│ │ 🟢 Marcus completed "API Tests" │  └───────────────────────────────────┘ │
│ │ 🔵 Emily updated "Login Design" │                                        │ │
│ │ 🟠 New comment on "Database"    │  ┌───────────────────────────────────┐ │
│ │ 🔴 Project Alpha is at risk     │  │ 🚀 Quick Actions                  │ │
│ │                                 │  │                                   │ │
│ │ View all activity →             │  │ [+ New Project]  [+ New Task]     │ │
│ └─────────────────────────────────┘  │ [📅 Schedule]    [👥 Invite]      │ │
│                                      └───────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ 📋 Active Projects                                                      │ │
│ │                                                                         │ │
│ │ Project Alpha        ██████████░░ 80%  ⚠️ At Risk    View Details →     │ │
│ │ Mobile App Redesign  ████████████ 95%  🟢 On Track   View Details →     │ │
│ │ Q4 Marketing         ████████░░░░ 60%  🟡 Needs Attn View Details →     │ │
│ │ Website Refresh      ██░░░░░░░░░░ 15%  🟢 On Track   View Details →     │ │
│ │                                                                         │ │
│ │ View All Projects (12) →                                                │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────┐  ┌───────────────────────────────────┐ │
│ │ 🤖 AI Insights                  │  │ 📊 Team Performance               │ │
│ │                                 │  │                                   │ │
│ │ "Based on current velocity,     │  │ Velocity: ↗️ +15% this week        │ │
│ │ Project Alpha may miss deadline │  │ Happiness: 😊 4.2/5               │ │
│ │ by 3 days. Consider reallocating│  │ Utilization: 📊 85%               │ │
│ │ 2 developers from Website."     │  │                                   │ │
│ │                                 │  │ Top Performers:                   │ │
│ │ [Take Action] [Dismiss]         │  │ 1. Marcus (12 tasks completed)    │ │
│ └─────────────────────────────────┘  │ 2. Emily (8 tasks completed)      │ │
│                                      │ 3. James (7 tasks completed)      │ │
│                                      └───────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Annotations
1. **Header Navigation**: Global search, notifications with count, user profile
2. **Main Navigation**: Primary sections with clear icons and labels
3. **Personalized Greeting**: Time-aware greeting with user name
4. **Quick Stats**: Overview of key metrics with attention-grabbing alerts
5. **Today's Priorities**: AI-curated daily tasks with time-based urgency
6. **Recent Activity**: Real-time updates with color-coded status indicators
7. **Quick Actions**: Most common tasks easily accessible
8. **Active Projects**: Visual progress bars with status indicators and quick access
9. **AI Insights**: Proactive recommendations with actionable suggestions
10. **Team Performance**: Key metrics with trend indicators

---

## Wireframe 2: Project Board View (Kanban)

### Layout Structure
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 📋 Project Alpha / Frontend Development                    👥 Share  ⚙️ Config│
├─────────────────────────────────────────────────────────────────────────────┤
│ 📊 Table  📋 Kanban  📅 Timeline  📈 Chart    |  🔍 Filter  📤 Export       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ [+ Add Col] │
│ │ 📝 Backlog  │ │ 🚧 In Prog  │ │ 👀 Review   │ │ ✅ Done     │             │
│ │    (12)     │ │    (8)      │ │    (5)      │ │    (23)     │             │
│ ├─────────────┤ ├─────────────┤ ├─────────────┤ ├─────────────┤             │
│ │ ┌─────────┐ │ │ ┌─────────┐ │ │ ┌─────────┐ │ │ ┌─────────┐ │             │
│ │ │ 🎨 Login│ │ │ │ ⚡ API   │ │ │ │ 🔍 Search│ │ │ │ 📱 Nav  │ │             │
│ │ │ Design  │ │ │ │ Integration│ │ │ │ Feature │ │ │ │ Component│ │             │
│ │ │         │ │ │ │         │ │ │ │         │ │ │ │         │ │             │
│ │ │ 👤 Emily│ │ │ │ 👤 Marcus│ │ │ │ 👤 Sarah│ │ │ │ 👤 James│ │             │
│ │ │ 🔴 High │ │ │ │ 🟡 Med  │ │ │ │ 🟢 Low  │ │ │ │ ✅ Done │ │             │
│ │ │ Due: 2d │ │ │ │ Due: 5d │ │ │ │ Due: 1w │ │ │ │ Comp: 3d│ │             │
│ │ └─────────┘ │ │ └─────────┘ │ │ └─────────┘ │ │ └─────────┘ │             │
│ │             │ │             │ │             │ │             │             │
│ │ ┌─────────┐ │ │ ┌─────────┐ │ │ ┌─────────┐ │ │ ┌─────────┐ │             │
│ │ │ 🔐 Auth │ │ │ │ 📊 Dash │ │ │ │ 🎨 Theme│ │ │ │ 📝 Forms│ │             │
│ │ │ System  │ │ │ │ Analytics│ │ │ │ System  │ │ │ │ Validation│ │             │
│ │ │         │ │ │ │         │ │ │ │         │ │ │ │         │ │             │
│ │ │ 👤 Alex │ │ │ │ 👤 Emily│ │ │ │ 👤 Emily│ │ │ │ 👤 Marcus│ │             │
│ │ │ 🟡 Med  │ │ │ │ 🔴 High │ │ │ │ 🟢 Low  │ │ │ │ ✅ Done │ │             │
│ │ │ Due: 1w │ │ │ │ Due: 3d │ │ │ │ Due: 2w │ │ │ │ Comp: 1w│ │             │
│ │ └─────────┘ │ │ └─────────┘ │ │ └─────────┘ │ │ └─────────┘ │             │
│ │             │ │             │ │             │ │             │             │
│ │ [+ Add Task]│ │ [+ Add Task]│ │ [+ Add Task]│ │ [+ Add Task]│             │
│ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘             │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ 📊 Board Analytics                                                      │ │
│ │                                                                         │ │
│ │ Cycle Time: 4.2 days  │  Throughput: 12 tasks/week  │  WIP: 8 tasks     │ │
│ │ Blocked Tasks: 2      │  Overdue: 1                 │  Team Load: 85%   │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Annotations
1. **Project Header**: Clear project name with quick access to sharing and configuration
2. **View Switcher**: Easy toggling between different board views
3. **Column Headers**: Status columns with task counts for quick overview
4. **Task Cards**: Compact cards showing essential information (title, assignee, priority, due date)
5. **Visual Indicators**: Color-coded priorities and status with icons
6. **Drag & Drop**: Cards can be moved between columns (indicated by design)
7. **Add Task**: Quick task creation in each column
8. **Board Analytics**: Key metrics displayed below the board for performance tracking
9. **Filter/Export**: Advanced options for data manipulation and export

---

## Wireframe 3: Task Detail Modal

### Layout Structure
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 🎨 Login Design System                                           ✕ Close    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ ┌─────────────────────────────────┐  ┌───────────────────────────────────┐ │
│ │ 📝 Description                  │  │ 📊 Task Details                   │ │
│ │                                 │  │                                   │ │
│ │ Create a modern, accessible     │  │ Status: 🚧 In Progress            │ │
│ │ login design system component   │  │ Priority: 🔴 High                 │ │
│ │ that includes:                  │  │ Assignee: 👤 Emily Watson         │ │
│ │                                 │  │ Due Date: Dec 17, 2024            │ │
│ │ • Form layouts                  │  │ Created: Dec 13, 2024             │ │
│ │ • Input validation states       │  │ Estimated: 8 hours               │ │
│ │ • Error messaging               │  │ Logged: 5.5 hours                │ │
│ │ • Responsive breakpoints        │  │                                   │ │
│ │ • Dark/light theme support      │  │ Labels: 🎨 Design 🔧 Frontend    │ │
│ │                                 │  │                                   │ │
│ │ [Edit Description]              │  │ [Edit Details]                    │ │
│ └─────────────────────────────────┘  └───────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ 📎 Attachments (3)                                                      │ │
│ │                                                                         │ │
│ │ 📄 login-wireframe.fig    📅 Dec 13  👤 Emily   [View] [Download]       │ │
│ │ 🖼️ inspiration-gallery.png 📅 Dec 14  👤 Sarah   [View] [Download]       │ │
│ │ 📋 requirements.md         📅 Dec 13  👤 Marcus  [View] [Download]       │ │
│ │                                                                         │ │
│ │ [+ Add Attachment] [📸 Take Photo] [🔗 Add Link]                        │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ 💬 Comments (7)                                              [Latest ↓] │ │
│ │                                                                         │ │
│ │ 👤 Marcus Rodriguez • 2 hours ago                                       │ │
│ │ Looks great! Just make sure the error states meet WCAG guidelines.      │ │
│ │ @emily can you also include focus states for keyboard navigation?       │ │
│ │                                                               👍 2  💭 Reply │ │
│ │                                                                         │ │
│ │ 👤 Emily Watson • 1 hour ago                                            │ │
│ │ @marcus Absolutely! I'll include all accessibility states in v2.        │ │
│ │ Updated the Figma file with focus indicators.                           │ │
│ │                                                               👍 1  💭 Reply │ │
│ │                                                                         │ │
│ │ 👤 Sarah Chen • 30 minutes ago                                          │ │
│ │ This is looking fantastic! Client feedback has been very positive.      │ │
│ │ Let's make this our standard component template.                        │ │
│ │                                                               👍 3  💭 Reply │ │
│ │                                                                         │ │
│ │ ┌─────────────────────────────────────────────────────────────────────┐ │ │
│ │ │ 💭 Add a comment...                                     [📎] [Send] │ │ │
│ │ │                                                                     │ │ │
│ │ │ @mention team members, #link tasks, or /commands                    │ │ │
│ │ └─────────────────────────────────────────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────┐  ┌───────────────────────────────────┐ │
│ │ 🔗 Dependencies                 │  │ ⏱️ Time Tracking                  │ │
│ │                                 │  │                                   │ │
│ │ Blocked by:                     │  │ ⏯️ Currently tracking time        │ │
│ │ ☐ Design System Setup (Alex)    │  │                                   │ │
│ │                                 │  │ Today: 2h 30m                    │ │
│ │ Blocking:                       │  │ This week: 5h 30m                │ │
│ │ ☐ Login Page Implementation     │  │ Total: 5h 30m / 8h estimated     │ │
│ │ ☐ Registration Flow             │  │                                   │ │
│ │                                 │  │ [⏸️ Pause] [+ Log Time]           │ │
│ │ [+ Add Dependency]              │  └───────────────────────────────────┘ │
│ └─────────────────────────────────┘                                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Annotations
1. **Modal Header**: Clear task title with close button
2. **Description Panel**: Rich text description with edit capability
3. **Task Details**: Key metadata in organized, scannable format
4. **Attachments**: File management with preview and download options
5. **Comments Thread**: Chronological conversation with @mentions and reactions
6. **Comment Input**: Rich comment editor with mention suggestions and commands
7. **Dependencies**: Visual representation of task relationships
8. **Time Tracking**: Real-time tracking with progress visualization
9. **Smart Features**: @mentions, #linking, /commands for power users

---

## Wireframe 4: Team Analytics Dashboard

### Layout Structure
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 📊 Team Analytics • Frontend Development                    📅 Last 30 Days  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ 📈 Key Metrics                                                          │ │
│ │                                                                         │ │
│ │ Velocity        Cycle Time       Happiness        Utilization            │ │
│ │ 47 tasks/week   3.2 days        😊 4.2/5         📊 85%                │ │
│ │ ↗️ +12%          ↘️ -0.3d         ↗️ +0.2          ↗️ +5%                 │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────┐  ┌───────────────────────────────────┐ │
│ │ 📊 Velocity Trend               │  │ 👥 Team Performance               │ │
│ │                                 │  │                                   │ │
│ │     45 ██                       │  │ Emily Watson        ████████░░ 82% │ │
│ │     40 ██ ██                    │  │ 12 completed │ 3 in progress      │ │
│ │     35 ██ ██ ██                 │  │ Avg cycle: 2.8d │ Happiness: 😊   │ │
│ │     30 ██ ██ ██ ██              │  │                                   │ │
│ │     25 ██ ██ ██ ██ ██           │  │ Marcus Rodriguez   ████████████ 95% │ │
│ │     20 ██ ██ ██ ██ ██ ██        │  │ 15 completed │ 2 in progress      │ │
│ │       W1 W2 W3 W4 W5 W6         │  │ Avg cycle: 2.1d │ Happiness: 😊   │ │
│ │                                 │  │                                   │ │
│ │ Target: 40 tasks/week           │  │ James Liu          ██████░░░░ 64%   │ │
│ └─────────────────────────────────┘  │ 8 completed │ 5 in progress       │ │
│                                      │ Avg cycle: 4.2d │ Happiness: 😐   │ │
│ ┌─────────────────────────────────┐  │                                   │ │
│ │ 🚦 Blockers & Risks             │  │ Alex Thompson     ██████████░ 78%  │ │
│ │                                 │  │ 10 completed │ 2 in progress      │ │
│ │ 🔴 Critical (2)                 │  │ Avg cycle: 3.5d │ Happiness: 😊   │ │
│ │ • API Integration timeout       │  └───────────────────────────────────┘ │
│ │ • Database performance issue    │                                        │ │
│ │                                 │  ┌───────────────────────────────────┐ │
│ │ 🟡 Medium (5)                   │  │ 📋 Task Distribution              │ │
│ │ • Design review delays          │  │                                   │ │
│ │ • Testing environment setup     │  │     Frontend    Backend    Design │ │
│ │ • Client feedback pending       │  │        45%        35%       20%   │ │
│ │ • Code review backlog           │  │     ███████    ██████     ████     │ │
│ │ • Deploy pipeline issues        │  │                                   │ │
│ │                                 │  │     High Pri   Medium Pri  Low Pri│ │
│ │ [View All Blockers]             │  │        30%        50%       20%   │ │
│ └─────────────────────────────────┘  │     ██████    ████████    ████     │ │
│                                      └───────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ 🎯 Sprint Progress                                                      │ │
│ │                                                                         │ │
│ │ Sprint 23: Mobile Optimization                    🗓️ 3 days remaining    │ │
│ │                                                                         │ │
│ │ ████████████████████████████████████████░░░░░░░░ 85% Complete (34/40)   │ │
│ │                                                                         │ │
│ │ Completed: 34 tasks  │  In Progress: 4 tasks  │  Remaining: 2 tasks     │ │
│ │ Story Points: 67/80  │  Confidence: 🟢 High   │  Burndown: On Track     │ │
│ │                                                                         │ │
│ │ [View Sprint Details] [Generate Report] [Plan Next Sprint]              │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────┐  ┌───────────────────────────────────┐ │
│ │ 🤖 AI Insights                  │  │ 📈 Recommendations                │ │
│ │                                 │  │                                   │ │
│ │ "James has 40% higher cycle     │  │ • Assign design tasks to Emily    │ │
│ │ time than team average. Consider│  │   (she has 18% lower workload)    │ │
│ │ pairing him with Marcus for     │  │                                   │ │
│ │ knowledge transfer."            │  │ • Schedule code review session    │ │
│ │                                 │  │   (4 PRs waiting > 2 days)        │ │
│ │ "Sprint velocity trending up    │  │                                   │ │
│ │ 15%. Team can handle 10% more   │  │ • Create API timeout monitoring   │ │
│ │ story points next sprint."      │  │   (critical blocker pattern)      │ │
│ │                                 │  │                                   │ │
│ │ [View All Insights]             │  │ [Apply Suggestions]               │ │
│ └─────────────────────────────────┘  └───────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Annotations
1. **Dashboard Header**: Clear context and time period selector
2. **Key Metrics**: High-level KPIs with trend indicators
3. **Velocity Chart**: Visual trend analysis with target benchmarks
4. **Team Performance**: Individual metrics with visual progress bars
5. **Blockers & Risks**: Prioritized issue tracking with severity levels
6. **Task Distribution**: Workload breakdown by type and priority
7. **Sprint Progress**: Real-time sprint tracking with confidence indicators
8. **AI Insights**: Machine learning-powered observations and recommendations
9. **Actionable Items**: Clear next steps and automated suggestions

---

## Wireframe 5: Mobile Task Management

### Layout Structure (Mobile - Portrait)
```
┌─────────────────────────────┐
│ ☰  Sunday.com    🔍  🔔(2)  │
├─────────────────────────────┤
│                             │
│ 👋 Good morning, Emily!     │
│                             │
│ 🎯 Today's Tasks            │
│ ┌─────────────────────────┐ │
│ │ 🎨 Login Design         │ │
│ │ Due: 2:00 PM            │ │
│ │ 🔴 High Priority        │ │
│ │ [Start Timer] [Update]  │ │
│ └─────────────────────────┘ │
│                             │
│ ┌─────────────────────────┐ │
│ │ 📊 Dashboard Analytics  │ │
│ │ Due: 4:30 PM            │ │
│ │ 🟡 Medium Priority      │ │
│ │ [Start Timer] [Update]  │ │
│ └─────────────────────────┘ │
│                             │
│ ┌─────────────────────────┐ │
│ │ 🔍 Search Feature       │ │
│ │ In Review               │ │
│ │ 🟢 Low Priority         │ │
│ │ [View] [Comment]        │ │
│ └─────────────────────────┘ │
│                             │
│ 📊 Quick Stats              │
│ Tasks: 3 active │ 2 done    │
│ Time: 5.5h logged today     │
│                             │
│ 🚀 Quick Actions            │
│ ┌─────────┐ ┌─────────────┐ │
│ │[+ Task] │ │[📷 Photo]   │ │
│ └─────────┘ └─────────────┘ │
│ ┌─────────┐ ┌─────────────┐ │
│ │[⏱️ Timer]│ │[💬 Chat]   │ │
│ └─────────┘ └─────────────┘ │
│                             │
│ ═══════════════════════════ │
│ 📊 Dashboard │ 📋 Tasks     │
│ 👥 Team     │ ⚙️ Settings  │
└─────────────────────────────┘
```

### Annotations
1. **Mobile Header**: Hamburger menu, logo, search, and notifications
2. **Personalized Greeting**: Context-aware welcome message
3. **Today's Tasks**: Priority-sorted tasks with quick actions
4. **Task Cards**: Essential information with touch-friendly buttons
5. **Quick Stats**: Key metrics at a glance
6. **Quick Actions**: Primary actions in accessible grid layout
7. **Bottom Navigation**: Primary navigation for mobile users
8. **Touch-Friendly**: All interactive elements sized for thumbs

---

## Responsive Design Considerations

### Breakpoint Strategy
- **Mobile**: 320px - 768px (Single column, touch-first)
- **Tablet**: 768px - 1024px (Two-column layout, hybrid interaction)
- **Desktop**: 1024px+ (Multi-column layout, mouse/keyboard optimized)

### Key Responsive Features
1. **Progressive Enhancement**: Mobile-first design approach
2. **Touch Targets**: Minimum 44px touch targets on mobile
3. **Content Priority**: Most important content surfaces first on small screens
4. **Navigation**: Collapsible navigation on mobile, expanded on desktop
5. **Data Visualization**: Charts adapt to screen size with horizontal scrolling
6. **Modal Behavior**: Full-screen modals on mobile, overlays on desktop

---

## Accessibility Considerations

### WCAG 2.1 AA Compliance
1. **Color Contrast**: 4.5:1 ratio for normal text, 3:1 for large text
2. **Keyboard Navigation**: Full functionality without mouse
3. **Screen Reader Support**: Semantic HTML and ARIA labels
4. **Focus Indicators**: Clear visual focus states
5. **Alternative Text**: Descriptive alt text for all images
6. **Text Scaling**: Support up to 200% zoom without horizontal scrolling

### Inclusive Design Features
1. **High Contrast Mode**: Optional high contrast theme
2. **Reduced Motion**: Respect prefers-reduced-motion setting
3. **Voice Commands**: Integration with voice assistants
4. **Keyboard Shortcuts**: Power user keyboard shortcuts
5. **Multiple Input Methods**: Support for mouse, keyboard, touch, and voice

---

## Interaction Patterns

### Micro-Interactions
1. **Button Feedback**: Visual and haptic feedback for all actions
2. **Loading States**: Progressive loading indicators
3. **Drag & Drop**: Visual feedback during drag operations
4. **Hover States**: Subtle hover effects to indicate interactivity
5. **Error States**: Clear error messaging with recovery suggestions

### Navigation Patterns
1. **Breadcrumbs**: Clear navigation hierarchy
2. **Deep Linking**: URLs for all application states
3. **Back Button**: Browser back button support
4. **Keyboard Shortcuts**: Quick navigation for power users
5. **Search**: Global search with smart suggestions

---

*Document Version: 1.0*
*Created: December 2024*
*Next Review: Q1 2025*