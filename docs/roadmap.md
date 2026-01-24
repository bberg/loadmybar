# LoadMyBar Roadmap

## Status: Live at loadmybar.com

**Last Updated:** January 21, 2025

---

## Phase 1: MVP (Complete)
- [x] Core plate calculation logic
- [x] lb/kg toggle with auto-conversion
- [x] Visual barbell plate display with animations
- [x] Mobile-first responsive UI
- [x] Dark mode by default
- [x] localStorage state persistence

---

## Phase 2: Polish & PWA (Complete)
- [x] PWA manifest for installability (`manifest.json`)
- [x] Service worker for offline support (`sw.js`)
- [x] App icons (SVG + 192px PNG)
- [x] Google Analytics integration
- [x] Stepper controls (+5, +45, -5, -45)
- [x] Keyboard shortcuts (arrows, u for units)
- [x] Tap-to-type weight input
- [x] Core Web Vitals optimization

---

## Phase 3: Feature Differentiation (Complete)
- [x] **Warmup Set Calculator** (`warmup.html`)
  - Progressive warmup percentages (40% → 60% → 75% → 90%)
  - Adjustable number of warmup sets (3-6)
  - Copy warmup to clipboard
  - Plate breakdown for each set
- [x] **5/3/1 Program Calculator** (`531.html`)
  - All 4 lifts (Squat, Bench, Deadlift, OHP)
  - 4-week cycle with tabs (Week 1-3 + Deload)
  - Collapsible lift cards
  - Plates for every working set
- [x] **Gym Plate Inventory** (`inventory.html`)
  - Multiple gym profiles
  - Quick presets (Commercial, Home, CrossFit, Minimal)
  - Test calculator with inventory constraints
- [x] **1RM Calculator** (`tools/one-rep-max.html`)
  - Estimate max from reps
- [x] "Closest weight" mode (shows nearest achievable)

---

## Phase 4: SEO & Content (Complete)
- [x] Schema.org WebApplication markup
- [x] Open Graph / Twitter meta tags
- [x] Canonical URLs (loadmybar.com)
- [x] `sitemap.xml` with all pages
- [x] `robots.txt`
- [x] **Reference Pages:**
  - [x] Common Weights chart (`reference/common-weights.html`)
- [x] **Guide Pages:**
  - [x] Plate Colors guide (`guides/plate-colors.html`)
  - [x] Barbell Types guide (`guides/barbell-types.html`)

---

## Phase 5: Monetization (Not Started)
- [ ] Non-intrusive display ad (single banner)
- [ ] Affiliate links (Rogue, REP, Amazon)
- [ ] Pro tier ($2.99/mo): ad-free, unlimited profiles, export
- [ ] Gym license ($99/yr): white-label embed

---

## Phase 6: Growth (Not Started)
- [ ] Reddit community engagement (r/fitness, r/weightroom, r/homegym)
- [ ] Guest posts on fitness blogs
- [ ] HARO responses
- [ ] Submit to fitness tool directories
- [ ] Consider mobile app if >100K monthly visitors

---

## Next Steps (Priority Order)

### Immediate
1. [ ] Add more tools to `/tools/` directory:
   - [ ] Percentage calculator (% of max)
   - [ ] Plate weight converter (lb ↔ kg)
   - [ ] RPE calculator
2. [ ] Starting Strength calculator page
3. [ ] GZCLP calculator page

### Short-term
4. [ ] Email capture for updates (low-friction)
5. [ ] Social sharing buttons on calculators
6. [ ] Print-friendly workout sheets
7. [ ] QR code sharing for workouts

### Medium-term
8. [ ] User accounts (optional, for sync)
9. [ ] Workout history/logging
10. [ ] More program calculators (nSuns, GZCLP, etc.)

---

## Metrics to Track
- Monthly visitors (target: 50K by month 6)
- Keyword rankings ("plate calculator", "barbell calculator", "5/3/1 calculator")
- Returning users (localStorage check)
- PWA installs
- Ad/affiliate revenue (when implemented)

---

## Key Decisions Made
- **Brand**: LoadMyBar
- **Domain**: loadmybar.com
- **Stack**: Vanilla HTML/CSS/JS (no build step, fast)
- **Hosting**: TBD (Cloudflare Pages recommended)
- **Analytics**: Google Analytics (G-RY7R4MB2F1)
- **Monetization**: Freemium with ads + affiliate (future)
- **SEO**: Content pages for each calculator + guides

---

## Completed Today (Jan 21, 2025)

### Core Site Build
- Created shared CSS design system (`styles/shared.css`)
- Built main calculator with stepper UI (`index.html`)
- Built warmup set calculator (`warmup.html`)
- Built 5/3/1 program calculator (`531.html`)
- Built gym inventory manager (`inventory.html`)

### SEO & Infrastructure
- Added Google Analytics to all pages
- Added PWA manifest and service worker
- Added Schema.org structured data
- Added Open Graph meta tags
- Created sitemap.xml and robots.txt

### Content
- Created common weights reference page
- Created plate colors guide
- Created barbell types guide
- Added 1RM calculator to tools
