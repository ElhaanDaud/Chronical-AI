# Chronicle AI — Frontend Redesign Orchestrator

**Author:** UI/UX Design Lead | **Date:** 2026-04-27 | **Branch:** main
**Status:** Active — Editorial Intelligence redesign

You are a senior frontend engineer and UI designer implementing a complete visual redesign of the Chronicle AI frontend. The target aesthetic is **Modern Editorial Minimalism + High-Fidelity Dashboarding** — a newsroom-grade intelligence platform that feels like premium vellum in light mode and a cinematic command center in dark mode.

Your design bible is the `/stitch_chronicle_ai_product_interface/` directory containing 6 HTML reference designs (dashboard, story detail, search — each in light and dark), 2 DESIGN.md specifications, and 6 screenshots. **Study every file before touching code.**

---

## Design System Specification

### Typography — Dual-Font Strategy

The serif/sans pairing is the soul of this design. Headlines use Newsreader for editorial authority; everything else uses Inter for functional clarity.

| Token | Font | Size | Weight | Line Height | Letter Spacing | Usage |
|-------|------|------|--------|-------------|----------------|-------|
| `display-xl` | Newsreader | 64px (4rem) | 600 | 1.1 | -0.02em | Hero headlines (story detail) |
| `headline-lg` | Newsreader | 40px (2.5rem) | 500 | 1.2 | — | Page titles (Intelligence Feed) |
| `headline-md` | Newsreader | 24px (1.5rem) | 600 | 1.3 | — | Card headlines, section headers |
| `body-lg` | Inter | 18px (1.125rem) | 400 | 1.6 | — | Lead paragraphs, executive synthesis |
| `body-md` | Inter | 16px (1rem) | 400 | 1.5 | — | Body text, descriptions |
| `body-sm` | Inter | 14px (0.875rem) | 400 | 1.5 | — | Secondary descriptions |
| `label-caps` | Inter | 13px (0.8125rem) | 600 | 1.0 | 0.05em | Section labels (uppercase) |
| `metadata` | Inter | 12px (0.75rem) | 500 | 1.4 | — | Timestamps, source counts |
| `label-caps-sm` | Inter | 12px (0.75rem) | 600 | 1.0 | 0.1em | Small labels, badge text |

**Font loading:** Google Fonts — Newsreader (400, 500, 600, 600 italic) + Inter (400, 500, 600). Replace Geist entirely. Remove local Geist font files.

### Color System — Light Mode

Paper & Ink fundamentals elevated for digital. Off-white "paper" surface, deep slate ink.

| Token | Value | Usage |
|-------|-------|-------|
| `--background` | `#f9f9f8` | Page background |
| `--surface-lowest` | `#ffffff` | Card backgrounds |
| `--surface-container-low` | `#f3f4f3` | Sidebar background, section fills |
| `--surface-container` | `#edeeed` | Hover states, input backgrounds |
| `--surface-container-high` | `#e7e8e7` | Active states, selected items |
| `--on-surface` | `#191c1c` | Primary text |
| `--on-surface-variant` | `#45464d` | Secondary text |
| `--outline` | `#76777d` | Borders, dividers |
| `--outline-variant` | `#c6c6cd` | Subtle borders |
| `--primary` | `#000000` | Headlines, primary buttons |
| `--on-primary` | `#ffffff` | Text on primary |
| `--secondary` | `#a93100` | International Orange — LIVE, breaking, accents |
| `--secondary-container` | `#d34000` | Badge backgrounds |
| `--on-secondary` | `#ffffff` | Text on secondary |
| `--secondary-fixed` | `#ffdbd0` | Search highlight background |
| `--error` | `#ba1a1a` | Error states |

### Color System — Dark Mode

Cinematic Intelligence Navy. Deep oceanic tones for focused night-time monitoring.

| Token | Value | Usage |
|-------|-------|-------|
| `--background` | `#0f172a` | Page background (Intelligence Navy) |
| `--surface-lowest` | `#1e293b` | Card backgrounds |
| `--surface-container-low` | `#1e293b` | Sidebar, panels |
| `--surface-container` | `#273449` | Hover states |
| `--surface-container-high` | `#334155` | Active states |
| `--on-surface` | `#f8fafc` | Primary text |
| `--on-surface-variant` | `#94a3b8` | Secondary text |
| `--outline` | `rgba(255,255,255,0.1)` | Glow borders |
| `--outline-variant` | `rgba(255,255,255,0.06)` | Subtle borders |
| `--primary` | `#ea580c` | Vibrant orange accent |
| `--on-primary` | `#ffffff` | Text on primary |
| `--secondary` | `#ea580c` | Same orange — LIVE, breaking |
| `--secondary-container` | `rgba(234,88,12,0.15)` | Glow accent backgrounds |
| `--on-secondary` | `#ffffff` | Text on secondary |

### Spacing System

4px base unit. Airy margins = premium feel.

| Token | Value | Usage |
|-------|-------|-------|
| `--space-xs` | `4px` | Tight gaps (icon-to-text) |
| `--space-sm` | `8px` | Small padding, badge internal |
| `--space-md` | `16px` | Card padding, standard gaps |
| `--space-lg` | `24px` | Section gaps, gutter width |
| `--space-xl` | `48px` | Major section separators |
| `--space-2xl` | `64px` | Layout margins, hero spacing |
| `--layout-gutter` | `24px` | Grid gutter |
| `--layout-margin` | `64px` | Page outer margin |
| `--container-max` | `1280px` | Max content width |

### Elevation — Tonal Layering

No heavy shadows. Depth from tonal shifts + whisper shadows.

| Level | Light Mode | Dark Mode |
|-------|------------|-----------|
| 0 (base) | `#f9f9f8` background | `#0f172a` background |
| 1 (cards) | `#ffffff` + 1px `#c6c6cd` border + `0 2px 8px rgba(0,0,0,0.04)` | `#1e293b` + 1px `rgba(255,255,255,0.1)` border |
| 2 (hover/active) | Shadow lifts to `0 10px 20px rgba(0,0,0,0.08)` | `glow-border` class (1px solid rgba(255,255,255,0.15)) |
| 3 (floating) | `0 10px 30px rgba(0,0,0,0.12)` | `0 10px 30px -10px rgba(15,23,42,0.5)` ambient |

### Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| `--radius-sm` | `0.125rem` (2px) | Inputs, small elements |
| `--radius-DEFAULT` | `0.25rem` (4px) | Cards, buttons, containers |
| `--radius-md` | `0.375rem` (6px) | Larger cards |
| `--radius-lg` | `0.5rem` (8px) | Modals |
| `--radius-full` | `9999px` | Pills, badges, avatars |

### Icons

**Material Symbols Outlined** via Google Fonts. Replace lucide-react. Consistent weight 300, optical size 24, grade 0.

---

## Current State → Target State Gap Analysis

| Aspect | Current State | Target State |
|--------|---------------|--------------|
| Typography | Geist mono font, single family | Newsreader + Inter dual-font |
| Colors | oklch grayscale, no brand | Paper & Ink light + Navy dark |
| Layout | Single-column max-w-7xl | 3-column: sidebar + feed + widgets |
| Navigation | Minimal navbar (brand + search) | Full nav: top bar + left sidebar |
| Dashboard | Plain 3-col grid of cards | Featured hero card + 2-up grid + sidebar widgets |
| Story Detail | Vertical stack, no hero | Hero section + executive synthesis + entity sidebar |
| Search | Basic list, no filters | Prominent search + filter bar + result cards |
| Cards | shadcn Card, basic Badge | Editorial cards with accent bars, hover lift, source avatars |
| Dark mode | CSS variables only | Full cinematic navy theme with glow borders |
| Sidebar | None | Intelligence Hub with nav, CTA, user context |
| Empty states | Plain text | Designed empty states with icons + CTAs |
| Footer | None | Chronicle AI footer with legal/API links |
| Animations | None | Hover transitions, LIVE pulse, card lift |

---

## Implementation Phases

### Phase 0 — Design Foundation (MUST COMPLETE FIRST)

**Goal:** Replace the entire design token system. Every subsequent phase depends on this.

**Files to modify:**
- `frontend/src/app/globals.css` — Complete rewrite of CSS custom properties
- `frontend/src/app/layout.tsx` — Replace Geist fonts with Newsreader + Inter via Google Fonts (`next/font/google`)
- `frontend/tailwind.config.ts` — Extend with full design token system

**Tasks:**

1. **Replace fonts in `layout.tsx`:**
   - Remove `localFont` imports for Geist Sans and Geist Mono
   - Import Newsreader (400, 500, 600, 600-italic) and Inter (400, 500, 600) from `next/font/google`
   - Set CSS variables: `--font-serif: Newsreader`, `--font-sans: Inter`
   - Apply Inter as the base body font

2. **Rewrite `globals.css`:**
   - Replace all oklch color variables with the hex-based Editorial Intelligence palette (light mode tokens as `:root`, dark mode as `.dark`)
   - Add typography utility classes: `.display-xl`, `.headline-lg`, `.headline-md`, `.body-lg`, `.body-md`, `.label-caps`, `.metadata`
   - Add elevation classes: `.whisper-shadow`, `.ambient-shadow`, `.glow-border`
   - Add animation keyframes: `pulse-live` (for LIVE badges), `card-lift` (hover)
   - Set `background: var(--background)` and `color: var(--on-surface)` on body

3. **Extend `tailwind.config.ts`:**
   - Map all color tokens to CSS variables
   - Add `fontFamily: { serif: ['var(--font-serif)'], sans: ['var(--font-sans)'] }`
   - Add custom spacing scale (xs through 2xl + layout-gutter + layout-margin)
   - Add border radius tokens
   - Add typography plugin entries or extend `fontSize` with the full scale

4. **Install Material Symbols:**
   - Add Material Symbols Outlined via Google Fonts link in `layout.tsx` `<head>` or via `next/font`
   - Create a `<MaterialIcon>` wrapper component: `components/material-icon.tsx`
   - Accepts `name` (icon name string) and `className` props
   - Default: `font-size: 24px`, `font-variation-settings: 'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 24`

**Verification:**
- `npm run build` passes
- All existing pages render with new fonts and colors
- Light/dark mode toggle works with new palette
- No visual regressions in existing components

**Commit:**
```
git add .
git commit -m "feat(frontend): replace design foundation — Newsreader+Inter fonts, Editorial Intelligence color palette, spacing/elevation tokens, Material Symbols"
```

---

### Phase 1 — Shell Layout (Sidebar + Top Nav + Footer)

**Goal:** Transform the single-column layout into the 3-column editorial shell: top nav + left sidebar + main content area + footer.

**Files to create/modify:**
- `frontend/src/components/sidebar.tsx` (new — client component)
- `frontend/src/components/top-nav.tsx` (new — replaces navbar.tsx)
- `frontend/src/components/footer.tsx` (new — server component)
- `frontend/src/app/layout.tsx` (restructure layout shell)
- `frontend/src/components/navbar.tsx` (delete after migration)

**Tasks:**

1. **Create `top-nav.tsx`:**
   - Fixed top bar with `backdrop-blur-sm` and `border-b border-outline-variant`
   - Left: Chronicle AI brand (Newsreader 600 weight)
   - Center: Navigation links — Home Feed (active underline orange in dark), Commit Timeline, Investigations, Sources, Saved, Archives
   - Right: Search input (compact), Ingest Refresh button (primary), notification bell icon, user avatar circle
   - Mobile: Hamburger menu triggers sidebar overlay

2. **Create `sidebar.tsx`:**
   - Fixed left column, `w-64`, full height below top nav
   - Header: "INTELLIGENCE HUB" (label-caps) + "GLOBAL MONITORING ACTIVE" subtitle
   - User avatar circle
   - Nav items with Material Symbols icons:
     - `home` → Home Feed
     - `commit` → Commit Timeline
     - `topic` → Topic Signals
     - `archive` → Archived Briefs
   - Active state: left 3px orange bar + surface-container-high background
   - Bottom section: "NEW BRIEFING" CTA button + Settings / Support links
   - Collapsible on mobile (overlay with backdrop)

3. **Create `footer.tsx`:**
   - Centered footer below main content
   - Left: "© 2024 Chronicle AI. Intelligence Synthesis Platform."
   - Right: Ethics Policy · API Access · Privacy Ledger · Terms of Use
   - Subtle top border, `metadata` typography

4. **Restructure `layout.tsx`:**
   - Remove old Navbar
   - New structure:
     ```
     <TopNav />
     <div className="flex pt-[nav-height]">
       <Sidebar />
       <main className="flex-1 ml-64 px-[layout-gutter] py-xl max-w-[container-max]">
         {children}
       </main>
     </div>
     <Footer />
     ```
   - Responsive: sidebar hidden on mobile, main full-width

5. **Delete `navbar.tsx`** after migration is verified.

**Verification:**
- Sidebar renders on all pages with correct nav items
- Top nav shows on all pages with functional search
- Footer shows on all pages
- Mobile responsive: sidebar collapses, top nav shows hamburger
- No horizontal scroll, no layout overflow
- `npm run build` passes

**Commit:**
```
git add .
git commit -m "feat(frontend): implement editorial shell layout — top nav, left sidebar (Intelligence Hub), footer, responsive collapse"
```

---

### Phase 2 — Dashboard Redesign

**Goal:** Transform the flat card grid into the editorial Intelligence Feed with featured hero card, 2-up secondary grid, and right sidebar widgets.

**Reference:** `dashboard_chronicle_ai/code.html` (light) + `dashboard_dark_chronicle_ai/code.html` (dark)

**Files to create/modify:**
- `frontend/src/app/page.tsx` — Complete rewrite
- `frontend/src/components/story-card.tsx` — Redesign with editorial style
- `frontend/src/components/featured-card.tsx` (new)
- `frontend/src/components/morning-digest.tsx` (new)
- `frontend/src/components/sidebar-timeline.tsx` (new)
- `frontend/src/components/live-badge.tsx` (new)
- `frontend/src/components/heat-badge.tsx` — Redesign

**Tasks:**

1. **Rewrite `page.tsx` (dashboard):**
   - Page header: "Intelligence Feed" (`headline-lg`, Newsreader) + subtitle + "LIVE" badge + "42 ACTIVE THREADS" pill
   - Filter toggles: "Latest" / "Trending" pills (right-aligned)
   - 12-column grid layout: 8-col feed + 4-col sidebar
   - Feed column: Featured card (first/hottest story) → 2-up grid of secondary cards
   - Sidebar column: Morning Digest widget → Commit Timeline widget
   - Empty state: Designed card with `search_off` icon + "No active stories" + CTA

2. **Create `featured-card.tsx`:**
   - Large card spanning full feed width
   - Top row: Category pill (e.g., "Geopolitics") + timestamp ("2m ago")
   - LIVE badge (if heat_score ≥ 5.0): orange pill with pulse animation
   - Headline: `headline-md` Newsreader
   - Description: `body-md` Inter, 2-line clamp
   - Bottom row: source count + "AI Confidence" badge + "DEEP DIVE →" link
   - Hover: card lifts to Level 2 shadow
   - Dark mode: `glow-border` class, orange accent glow behind card (`bg-primary/10 blur-3xl`)

3. **Redesign `story-card.tsx`:**
   - White card with 1px border, whisper shadow
   - Top: Category pill + timestamp
   - Heat badge: colored pill (HIGH HEAT = orange, RISING = yellow, COOLING = gray)
   - Headline: `headline-md` Newsreader, 2-line clamp
   - Description: `body-sm` Inter, 2-line clamp
   - Bottom: Source count (metadata), time ago
   - Hover: `transition-shadow duration-200`, lift to Level 2

4. **Create `live-badge.tsx`:**
   - Pill shape (`radius-full`), `secondary-container` background
   - White uppercase text (`label-caps-sm`)
   - Animated dot: 6px circle with `animate-pulse` in orange
   - Conditionally rendered when story heat_score ≥ threshold

5. **Create `morning-digest.tsx`:**
   - Right sidebar card with "Morning Catch-up" header (label-caps)
   - Bulleted list of top 3-5 story summaries (body-sm)
   - Data: derived from top stories by heat score, showing `latest_commit_message`

6. **Create `sidebar-timeline.tsx`:**
   - Right sidebar card with "Commit Timeline" header (label-caps)
   - Vertical timeline: thin line with colored dots (orange for latest, gray for older)
   - Each entry: timestamp (metadata) + short commit message (body-sm)
   - Data: aggregated from most recent commits across all stories

7. **Redesign `heat-badge.tsx`:**
   - Three visual states:
     - Active (heat ≥ 3.0): orange pill, "HIGH HEAT" or "LIVE"
     - Cooling (heat ≥ 1.0): amber/yellow pill, "RISING HEAT"
     - Hibernated (heat < 1.0): gray pill, "COOLING"
   - Dark mode: glow effect on active state

**Verification:**
- Dashboard shows featured card + secondary grid + sidebar widgets
- LIVE badge pulses on hot stories
- Cards lift on hover with smooth transition
- Dark mode shows navy background, glow borders, orange accents
- Data flows correctly from API (stories endpoint)
- Responsive: sidebar stacks below feed on tablet, single column on mobile
- `npm run build` passes

**Commit:**
```
git add .
git commit -m "feat(frontend): redesign dashboard — featured hero card, editorial story cards, Morning Digest + Commit Timeline sidebar, LIVE badges"
```

---

### Phase 3 — Story Detail Redesign

**Goal:** Transform the plain vertical stack into an editorial reading experience with hero, executive synthesis, entity chips, commit timeline, and related clusters.

**Reference:** `story_detail_chronicle_ai/code.html` (light) + `story_detail_dark_chronicle_ai/code.html` (dark)

**Files to create/modify:**
- `frontend/src/app/story/[id]/page.tsx` — Complete rewrite
- `frontend/src/components/executive-synthesis.tsx` (new)
- `frontend/src/components/entity-chips.tsx` (new)
- `frontend/src/components/commit-log.tsx` — Major redesign
- `frontend/src/components/catch-up-panel.tsx` — Redesign as executive synthesis
- `frontend/src/components/related-clusters.tsx` (new)
- `frontend/src/components/sparkline.tsx` (new)
- `frontend/src/lib/api.ts` — May need new endpoint for related clusters

**Tasks:**

1. **Rewrite `story/[id]/page.tsx`:**
   - Breadcrumb: "← Back to Intelligence Feed" link
   - Hero section:
     - Heat badge (RISING HEAT / HIGH HEAT / COOLING)
     - Synthesis metadata: "Synthesized: 12 mins ago · AI Confidence: 94%" (metadata text)
     - Display headline: `display-xl` Newsreader (64px), tight leading
     - Lead paragraph: `body-lg` Inter
     - Right-aligned sparkline (72hr Velocity): simple SVG line chart
   - Two-column below hero: 8-col main + 4-col sidebar
   - Main column: Executive Synthesis → Commit History
   - Sidebar: Key Entities card → Data visualization card (if applicable)
   - Below: Related Clusters 2-up grid
   - Footer

2. **Create `executive-synthesis.tsx`:**
   - Card with 3px left accent bar (`secondary` orange)
   - Header: `label-caps` "EXECUTIVE SYNTHESIS" + sparkle icon
   - Body: Bullet points from catch-up narrative (body-lg Inter)
   - Each bullet has bold label prefix
   - Full-width on mobile, 8-col on desktop
   - This replaces the old CatchUpPanel — uses same `/catchup` endpoint

3. **Create `entity-chips.tsx`:**
   - Sidebar card: "KEY ENTITIES" header (label-caps)
   - Grid of chips: `px-3 py-1.5`, `surface-container` background, `on-surface` text, 1px border
   - Derived from `entity_fingerprint` JSONB field on cluster
   - Dark mode: `bg-slate-800 border-slate-700` chips
   - **Backend note:** `entity_fingerprint` already exists on Cluster model but not exposed in StoryDetail schema — will need adding

4. **Redesign `commit-log.tsx`:**
   - Section header: "Commit History" (headline-md Newsreader)
   - Vertical timeline with left line + colored dots:
     - Latest commit: orange dot (12px)
     - Older commits: gray dot (8px)
   - Each entry:
     - Timestamp: `label-caps-sm` uppercase (e.g., "TODAY, 09:42 UTC")
     - Revision label: `metadata` italic (e.g., "Major Revision")
     - Message: `headline-md` Newsreader
     - Detail: `body-md` Inter
     - Source attribution: `metadata` with source icon
     - Expandable source URLs (existing behavior preserved)
   - Smooth expand/collapse animation

5. **Create `sparkline.tsx`:**
   - Small inline SVG (120×40px) showing commit frequency over 72 hours
   - Derived from commit dates: bucket into 6-hour windows, plot as line
   - Orange stroke in dark mode, primary stroke in light mode
   - Label: "72hr Velocity" (metadata text)

6. **Create `related-clusters.tsx`:**
   - 2-column grid below commit history
   - Each card: `headline-md` title + `body-sm` description + metadata row
   - Data: Could use existing stories endpoint filtered by similar topic_tokens, or hardcode "Related Stories" section using remaining stories
   - Card style: matching editorial card pattern

7. **Update `api.ts`:**
   - Add `entity_fingerprint: string[]` to StoryDetail interface (when backend exposes it)
   - Add fetch for related clusters (or derive client-side from stories list)

**Verification:**
- Story detail shows hero with display-xl headline
- Executive synthesis renders with orange accent bar
- Entity chips display from entity_fingerprint
- Commit timeline has colored dots and proper typography
- Sparkline renders from commit dates
- Related clusters show below timeline
- Dark mode: navy background, glow borders, orange accents
- `npm run build` passes

**Commit:**
```
git add .
git commit -m "feat(frontend): redesign story detail — hero section, executive synthesis, entity chips, editorial commit timeline, sparkline, related clusters"
```

---

### Phase 4 — Search Redesign

**Goal:** Transform the basic search list into a full intelligence search interface with prominent search bar, filter chips, editorial result cards, and designed empty state.

**Reference:** `search_chronicle_ai/code.html` (light) + `search_dark_chronicle_ai/code.html` (dark)

**Files to create/modify:**
- `frontend/src/app/search/page.tsx` — Complete rewrite
- `frontend/src/components/search-bar.tsx` — Major redesign
- `frontend/src/components/search-result-card.tsx` (new)
- `frontend/src/components/filter-bar.tsx` (new)
- `frontend/src/components/empty-state.tsx` (new)

**Tasks:**

1. **Rewrite `search/page.tsx`:**
   - Page header: "Information Synthesis" (headline-lg Newsreader) + subtitle
   - Prominent central search bar with "Analyze" button
   - Below search: Trending Now tags + Recent Queries
   - Sticky filter bar: Topic, Time, Source dropdowns + Heat Level toggles
   - Results header: "Showing N results (Xs synthesis time)" or "Active Signals (N)"
   - Result cards list
   - Empty state when no results

2. **Redesign `search-bar.tsx`:**
   - Large input with 1px border, `headline-md` placeholder text
   - Focus: border transitions to `primary` color, orange focus ring in dark mode
   - Right: "Analyze" button (primary style)
   - Full-width on mobile, centered 800px max on desktop

3. **Create `search-result-card.tsx`:**
   - Card with left accent bar (3px, orange for high-confidence, gray for standard)
   - Source + timestamp + AI Confidence badge row (metadata)
   - Severity badge: "BREAKING" (orange), "CRITICAL" (orange), "ELEVATED" (slate)
   - Headline: `headline-md` Newsreader
   - Excerpt: `body-md` Inter, search terms highlighted with `secondary-fixed` background
   - Actions row: "Read Full Brief" + "View Timeline" links
   - Dark mode: dark card, glow border on hover

4. **Create `filter-bar.tsx`:**
   - Horizontal bar with chip-style filters
   - Each filter: pill with close (×) button to remove
   - "+ Add Filter" dashed border chip
   - Heat Level toggle: Low / Med / High circular indicators
   - Sticky on scroll (below search bar)
   - Client-side filtering (no backend changes needed — filter the search results)

5. **Create `empty-state.tsx`:**
   - Reusable component with dashed border container
   - Centered: Material Symbol icon + title + description + CTA button(s)
   - Props: `icon`, `title`, `description`, `actions[]`
   - Used in: search (no results), dashboard (no stories)
   - Dark mode: dashed border lighter, icon muted

**Verification:**
- Search page shows prominent search bar with Analyze button
- Results render with accent bars and severity badges
- Filter bar renders with removable chips
- Empty state shows when no results
- Search highlighting works on matched terms
- Dark mode: navy background, orange focus ring, glow cards
- `npm run build` passes

**Commit:**
```
git add .
git commit -m "feat(frontend): redesign search — prominent search bar, filter chips, editorial result cards, severity badges, designed empty state"
```

---

### Phase 5 — Dark Mode Polish + Animations + Responsive

**Goal:** Perfect the dark mode cinematic experience, add micro-interactions, and ensure mobile responsiveness across all pages.

**Files to modify:**
- `frontend/src/app/globals.css` — Dark mode refinements
- All component files — Dark mode class additions
- `frontend/src/components/theme-toggle.tsx` (new)

**Tasks:**

1. **Dark mode refinements:**
   - Verify every component has proper dark mode classes
   - Add `.glow-border` utility (1px solid rgba(255,255,255,0.1), hover: 0.15)
   - Featured card: orange glow accent (`::before` pseudo-element with blur)
   - Commit timeline dots: orange glow in dark mode
   - Ensure text contrast meets WCAG AA on navy backgrounds

2. **Create `theme-toggle.tsx`:**
   - Sun/moon icon toggle in top nav
   - Uses `next-themes` or manual `.dark` class toggle on `<html>`
   - Persists preference in localStorage
   - Smooth transition between modes

3. **Micro-animations:**
   - Card hover: `transition-all duration-200` → shadow lift + subtle translate-y
   - LIVE badge: `animate-pulse` on dot (already in Phase 2)
   - Page transitions: subtle fade-in on route change
   - Button hover: `transition-colors duration-150`
   - Sidebar active item: left border slides in
   - Skeleton loading states for all async content (using existing Skeleton component)

4. **Responsive breakpoints:**
   - Desktop (≥1280px): Full 3-column layout
   - Tablet (768-1279px): Sidebar collapses to icon-only rail, right sidebar stacks below feed
   - Mobile (<768px): Sidebar hidden (hamburger overlay), single column, footer stacks vertically
   - Search: filters collapse into "Filters" dropdown on mobile
   - Story detail: sidebar stacks below narrative on tablet

5. **Loading states:**
   - Dashboard: Skeleton cards (3-up grid) while stories load
   - Story detail: Skeleton hero + skeleton synthesis while loading
   - Search: Skeleton result cards while searching
   - Use existing `Skeleton` component with editorial sizing

**Verification:**
- Dark mode renders correctly on all 3 pages
- Theme toggle persists across page navigations
- All animations are smooth (60fps, no jank)
- Mobile layout works on iPhone SE (375px) through iPad Pro (1024px)
- No horizontal scroll on any breakpoint
- `npm run build` passes
- Lighthouse accessibility score ≥ 90

**Commit:**
```
git add .
git commit -m "feat(frontend): dark mode polish, theme toggle, micro-animations, full responsive layout across all breakpoints"
```

---

### Phase 6 — Backend Schema Extension + Final Integration

**Goal:** Expose entity_fingerprint in the API, add any missing data fields, and verify end-to-end data flow.

**Files to modify:**
- `backend/app/schemas/story.py` — Add `entity_fingerprint` to StoryDetail
- `backend/app/api/stories.py` — Include entity_fingerprint in query
- `frontend/src/lib/api.ts` — Update interfaces

**Tasks:**

1. **Expose `entity_fingerprint` in StoryDetail schema:**
   - Add `entity_fingerprint: list[str]` to `StoryDetail` Pydantic model
   - Default to empty list if null

2. **Update stories API:**
   - Ensure entity_fingerprint is included in story detail response
   - No migration needed — field already exists on Cluster model

3. **Update frontend API types:**
   - Add `entity_fingerprint: string[]` to `StoryDetail` interface

4. **End-to-end verification:**
   - Start Docker Compose stack
   - Trigger full pipeline: `curl -X POST "http://localhost:8000/api/ingest?full_pipeline=true"`
   - Verify dashboard loads with new design
   - Verify story detail shows entity chips
   - Verify search renders with new cards
   - Verify dark mode on all pages
   - Verify mobile responsive on all pages

**Commit:**
```
git add .
git commit -m "feat: expose entity_fingerprint in story detail API, update frontend types, verify end-to-end integration"
```

---

## Agent Instructions

### Before Each Phase

1. Read the relevant reference HTML file(s) from `/stitch_chronicle_ai_product_interface/`
2. Read the DESIGN.md files for exact token values
3. Read existing code files that will be modified
4. Understand data flow: check `api.ts` interfaces and backend schemas

### Code Conventions (MUST FOLLOW)

- Server components by default. Client components ("use client") ONLY for interactivity
- No comments in code — codebase is comment-free by design
- No `as any`, `@ts-ignore`, `@ts-expect-error`
- Absolute imports only
- Use CSS variables for all colors/spacing — never hardcode hex values in components
- Use Tailwind classes — no inline styles except for dynamic values
- Material Symbols via `<MaterialIcon>` component — never raw `<span>` with icon text
- All new components go in `frontend/src/components/`
- All new pages go in `frontend/src/app/`
- Type all props — no implicit `any`

### Testing Each Phase

After completing each phase:
1. Run `npm run build` from `frontend/` — must pass with zero errors
2. Run `npm run lint` — must pass
3. Visual check: compare your output against the reference screenshots
4. Test light and dark mode
5. Test mobile (375px viewport minimum)

### AGENTS.md Updates

After each phase commit, append to the Change Log in `AGENTS.md`:

```
| Date | Phase | Changes | Files Touched |
|------|-------|---------|---------------|
| YYYY-MM-DD | Frontend Phase N | [description] | [files] |
```

Also update the `## Structure` section if new directories or significant files were added.

Also update the `## Conventions` section's Frontend entry to reflect the new design system (Newsreader + Inter, Material Symbols, editorial palette).

---

## Reference File Map

| Design | Light Mode | Dark Mode |
|--------|------------|-----------|
| Dashboard | `dashboard_chronicle_ai/code.html` | `dashboard_dark_chronicle_ai/code.html` |
| Story Detail | `story_detail_chronicle_ai/code.html` | `story_detail_dark_chronicle_ai/code.html` |
| Search | `search_chronicle_ai/code.html` | `search_dark_chronicle_ai/code.html` |
| Design Spec v1 | `editorial_intelligence_1/DESIGN.md` | — |
| Design Spec v2 | `editorial_intelligence_2/DESIGN.md` | — |
| Screenshots | `*/screen.png` (6 files) | — |
