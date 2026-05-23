# Planning Guide

A comprehensive administrative dashboard for managing CLT drivers working with ride-sharing platforms (Uber, 99), providing real-time monitoring, performance tracking, and operational insights for fleet managers.

**Experience Qualities**:
1. **Professional** - Clean, data-dense interface that conveys authority and reliability for business-critical operations
2. **Insightful** - Rich visualizations and clear metrics that surface actionable intelligence immediately
3. **Efficient** - Quick navigation, minimal clicks to key information, and streamlined workflows for daily management tasks

**Complexity Level**: Complex Application (advanced functionality, likely with multiple views)
This is a multi-module enterprise dashboard with 7 distinct feature areas (drivers, vehicles, journeys, reports, goals, maintenance, etc.), real-time status monitoring, complex data visualizations, role-based workflows, and extensive CRUD operations across multiple entities.

## Essential Features

**1. Dashboard Overview**
- Functionality: Real-time KPI display with 4 metric cards (active drivers, km traveled, revenue, alerts), 3 charts (revenue comparison, hours tracking, journey status distribution), and alerts table
- Purpose: Provides immediate operational visibility and surfaces critical issues requiring attention
- Trigger: Default landing page after login
- Progression: User logs in → Dashboard loads with current day data → User scans KPIs → Reviews charts for trends → Checks alerts table → Clicks through to specific modules for details
- Success criteria: All KPIs load within 2 seconds, charts are interactive with tooltips, alerts are clickable and navigate to relevant records

**2. Driver Management**
- Functionality: Searchable/filterable table of all drivers with profile drawer showing personal info, CLT hours tracking, journey history, and bonus accumulation
- Purpose: Centralized driver information management and performance monitoring
- Trigger: Click "Motoristas" in sidebar
- Progression: User navigates to drivers → Applies filters/search → Views table → Clicks driver name → Drawer opens with tabbed details → Reviews CLT hours progress, journey history, or bonus data → Closes drawer or edits driver info
- Success criteria: Table supports pagination, filters work instantly, drawer loads complete driver profile, CLT progress bar accurately reflects monthly hours vs 220h target

**3. Journey Tracking**
- Functionality: Filterable journey log with km/revenue charts and detailed modal showing full journey data (km, revenue breakdown, hours, pauses, refueling, incidents)
- Purpose: Comprehensive journey auditing and performance analysis
- Trigger: Click "Jornadas" in sidebar
- Progression: User navigates to journeys → Sets date/driver/status filters → Views km comparison chart → Scans journey table → Clicks journey row → Modal opens with complete details including mini-map → Reviews revenue, pauses, refueling → Closes modal
- Success criteria: Filters update table in real-time, chart shows comparative km performance, modal displays all journey components including geographic endpoints

**4. Vehicle Fleet Management**
- Functionality: Grid of vehicle cards showing status, maintenance needs, and key dates (IPVA, inspections) with quick status overview bar
- Purpose: Track vehicle availability, maintenance schedules, and compliance requirements
- Trigger: Click "Veículos" in sidebar
- Progression: User navigates to vehicles → Scans status bar for quick overview → Reviews vehicle cards in grid → Identifies vehicles needing attention (maintenance alerts, expiring documents) → Clicks edit or history → Updates vehicle information
- Success criteria: Cards display current status with color coding, alerts shown for documents expiring within 30 days, maintenance status clearly visible

**5. Performance Reports**
- Functionality: Multi-tab reporting interface with platform comparison (declared vs actual km/revenue), monthly performance radar charts, and CSV import for platform data
- Purpose: Data integrity validation and driver performance benchmarking
- Trigger: Click "Relatórios" in sidebar
- Progression: User navigates to reports → Selects tab (comparison/performance/import) → Sets date filters → Views inconsistency alerts in comparison tab → Analyzes radar chart for driver strengths/weaknesses → Optionally imports CSV data → Exports report
- Success criteria: Comparison table flags discrepancies >20%, radar chart normalizes metrics 0-100, CSV parser handles Uber/99 formats

**6. Goals & Bonuses**
- Functionality: Goal card grid showing active targets (revenue/km/hours) with reference scope (team/individual), bonus accumulation chart, and goal creation modal
- Purpose: Incentive program management and bonus calculation transparency
- Trigger: Click "Metas & Bônus" in sidebar
- Progression: User navigates to goals → Reviews active goal cards → Checks bonus accumulation chart → Clicks "Nova Meta" → Fills form (type, reference, thresholds, bonus value) → Submits → New goal appears in grid
- Success criteria: Goals display progress, bonus chart shows current month accumulation by driver, goal creation validates thresholds

**7. Maintenance Tracking**
- Functionality: Maintenance log table with status tracking, cost aggregation, and upcoming service alerts based on km milestones
- Purpose: Vehicle maintenance scheduling and cost control
- Trigger: Click "Manutenções" in sidebar
- Progression: User navigates to maintenance → Reviews top KPIs (monthly cost, active jobs, upcoming services) → Scans table for in-progress maintenance → Identifies vehicles approaching service intervals → Clicks to view/edit maintenance record
- Success criteria: KPIs aggregate correctly, table shows status progression, alerts trigger at 500km before service interval

## Edge Case Handling

- **No Active Journeys**: Display empty state with illustration and "No journeys today" message instead of zero-filled charts
- **Missing GPS Data**: Show "GPS signal lost" badge with last known location and timestamp in alerts table
- **CSV Format Errors**: Display validation errors with line numbers and allow partial import of valid rows
- **Document Expiration**: Graduated alert colors (yellow at 60 days, orange at 30 days, red when expired)
- **Concurrent Edits**: Show toast notification if record was updated by another user, offer reload option
- **Zero-Revenue Journeys**: Flag with warning badge for investigation (possible app issues)
- **Negative CLT Balance**: Display in red with "deficit" label and calculate required catch-up hours
- **Offline State**: Show connectivity banner at top, queue updates for sync when connection restored

## Design Direction

The design should evoke **authority, clarity, and operational control** - the feeling of a command center where every metric matters and every action is purposeful. Users should feel confident making decisions based on the data presented, with visual hierarchy that naturally guides attention to what's most important.

## Color Selection

Dark professional palette with strong contrast and semantic color coding for immediate status recognition.

- **Primary Color**: Deep Navy Blue (oklch(0.25 0.06 250)) - Conveys professionalism, stability, and trustworthiness for a business-critical system
- **Secondary Colors**: 
  - Light Gray Background (oklch(0.97 0.005 250)) - Reduces eye strain for long dashboard sessions
  - White Cards (oklch(1 0 0)) - Clean data containers with subtle shadows for depth
- **Accent Color**: Royal Blue (oklch(0.55 0.18 250)) - High-contrast CTAs and interactive elements that demand attention
- **Status Colors**:
  - Success Green (oklch(0.65 0.18 145)) - Active drivers, completed journeys, on-target metrics
  - Warning Yellow (oklch(0.75 0.15 85)) - Paused journeys, approaching deadlines
  - Danger Red (oklch(0.60 0.22 25)) - GPS alerts, inconsistencies, expired documents
  - Info Blue (oklch(0.60 0.15 250)) - Open journeys, in-progress items

**Foreground/Background Pairings**:
- Sidebar Navy (oklch(0.25 0.06 250)): White text (oklch(1 0 0)) - Ratio 9.8:1 ✓
- Royal Blue Accent (oklch(0.55 0.18 250)): White text (oklch(1 0 0)) - Ratio 5.2:1 ✓
- Light Background (oklch(0.97 0.005 250)): Dark Gray text (oklch(0.25 0.01 250)) - Ratio 13.1:1 ✓
- Success Green (oklch(0.65 0.18 145)): White text (oklch(1 0 0)) - Ratio 4.9:1 ✓
- Danger Red (oklch(0.60 0.22 25)): White text (oklch(1 0 0)) - Ratio 5.0:1 ✓

## Font Selection

Typography should convey modern professionalism with excellent readability for data-heavy interfaces, using a geometric sans-serif that works across numeric displays, tables, and body text.

**Font Family**: IBM Plex Sans - A technical yet approachable typeface designed for enterprise interfaces, with exceptional legibility in tables and clear distinction between similar characters (0/O, 1/I/l)

- **Typographic Hierarchy**:
  - H1 (Page Titles): IBM Plex Sans SemiBold / 28px / -0.02em letter spacing / 1.2 line height
  - H2 (Section Headers): IBM Plex Sans SemiBold / 20px / -0.01em letter spacing / 1.3 line height
  - H3 (Card Headers): IBM Plex Sans Medium / 16px / 0 letter spacing / 1.4 line height
  - Body (Tables/Content): IBM Plex Sans Regular / 14px / 0 letter spacing / 1.5 line height
  - Small (Labels/Meta): IBM Plex Sans Regular / 12px / 0.01em letter spacing / 1.4 line height
  - Numbers (KPIs/Metrics): IBM Plex Sans SemiBold / varies / tabular-nums for alignment

## Animations

Animations should reinforce data updates and state transitions without delaying critical information access - use motion to guide attention to changes rather than for decoration.

- **Data Updates**: Smooth count-up animations for KPI numbers (300ms ease-out) to emphasize value changes
- **Chart Transitions**: Staggered bar/line animations (200ms per element, 50ms delay) when loading or filtering data
- **Drawer/Modal Entry**: Slide-in from right (350ms cubic-bezier) for contextual panels that don't interrupt main view
- **Status Changes**: Subtle color pulse (600ms) on badges when status updates in real-time
- **Hover States**: Instant (0ms) color shifts on interactive elements, subtle scale (1.02) on cards over 150ms
- **Loading States**: Skeleton screens with shimmer effect rather than spinners for table/chart loading

## Component Selection

- **Components**:
  - **Sidebar**: Custom sidebar with fixed positioning, collapsible on mobile, active state highlighting
  - **Card**: Base container for KPIs and vehicle grid items, with subtle shadow (shadow-sm) and hover lift (shadow-md)
  - **Table**: Striped rows with hover state, sticky header for long lists, integrated with Pagination
  - **Sheet**: Right-side drawer for driver profile details, allowing main context to remain visible
  - **Dialog**: Center modal for journey details and goal creation, with backdrop blur
  - **Tabs**: For multi-view reports and driver profile sections
  - **Badge**: Status indicators with semantic colors (variant prop for success/warning/destructive)
  - **Button**: Primary (accent blue), secondary (outlined), destructive (red) variants
  - **Input, Select, Textarea**: Form controls with consistent border-radius and focus rings
  - **Progress**: Linear progress bar for CLT hours tracking with color thresholds
  - **Tooltip**: Contextual help and full values on chart hover
  - **Alert**: Top-of-page banners for system messages (connectivity, errors)
  - **Avatar**: Driver profile images with fallback to initials
  - **Calendar**: Date picker for report filters and journey date selection
  - **Command**: Quick search/command palette (⌘K) for navigation

- **Customizations**:
  - **KPI Cards**: Custom component with large numeric display, icon badge, and trend indicator (arrow + percentage)
  - **Vehicle Card**: Custom grid card with image placeholder, badge cluster for status, and quick action buttons
  - **Status Timeline**: Custom component for journey pauses showing time segments visually
  - **Mini Map Placeholder**: Decorative SVG with location pins for journey endpoints

- **States**:
  - Buttons: Distinct hover (brightness shift), active (slight scale down), disabled (opacity 50%, cursor not-allowed), loading (spinner + disabled state)
  - Table Rows: Zebra striping (bg-muted/5), hover (bg-accent/10), selected (bg-accent/20 with border-l-4 in accent color)
  - Sidebar Items: Default (muted foreground), hover (foreground), active (accent background + foreground, border-l-4 accent)
  - Form Inputs: Default (border-input), focus (ring-2 ring-ring), error (border-destructive ring-destructive), disabled (bg-muted)

- **Icon Selection**:
  - Dashboard: House
  - Motoristas: Users
  - Veículos: Car
  - Jornadas: ClipboardList
  - Abastecimentos: GasFuel (use DropletHalf from Phosphor)
  - Manutenções: Wrench
  - Metas & Bônus: Target
  - Relatórios: ChartBar
  - Configurações: Gear
  - Alertas: Bell with badge
  - Sair: SignOut
  - Status indicators: CheckCircle (success), Clock (paused), XCircle (error), Circle (neutral)

- **Spacing**:
  - Page padding: p-6 (24px) on desktop, p-4 (16px) on mobile
  - Card padding: p-6 (24px) for KPI cards, p-4 (16px) for vehicle cards
  - Section gaps: gap-6 (24px) between major sections, gap-4 (16px) between related elements
  - Grid layouts: grid-cols-4 (KPIs), grid-cols-3 (vehicles), gap-4
  - Table spacing: py-3 px-4 for cells, ensures comfortable click targets
  - Form spacing: gap-4 between fields, gap-2 for label-input pairs

- **Mobile**:
  - Sidebar collapses to hamburger menu with overlay sheet
  - KPI cards stack to single column (grid-cols-1 sm:grid-cols-2 lg:grid-cols-4)
  - Tables become horizontally scrollable with sticky first column
  - Vehicle grid adjusts to grid-cols-1 sm:grid-cols-2 lg:grid-cols-3
  - Charts maintain aspect ratio, become scrollable if needed
  - Drawer (Sheet) becomes full-screen on mobile
  - Reduce text sizes by one step on mobile (H1: 24px → 20px, etc.)
  - Touch-friendly button/row heights minimum 44px
