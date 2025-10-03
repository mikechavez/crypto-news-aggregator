---
trigger: manual
---

# UI Development Rules
**Activation Mode:** Always On (when working in context-owl-ui/)

## Project Structure:
1. Follow the established folder structure:
   - `/src/components` - Reusable UI components only
   - `/src/pages` - Full page components with data fetching
   - `/src/api` - API client functions (no business logic)
   - `/src/types` - TypeScript interfaces (shared across app)
   - `/src/lib` - Pure utility functions (no React hooks)

2. Component organization:
   - One component per file
   - Export component as default
   - Co-locate types used only in that component
   - Keep components under 200 lines (split if larger)

## React Query Best Practices:
1. All API calls use React Query (useQuery/useMutation)
2. Set appropriate refetchInterval (30s for signals, 60s for narratives)
3. Handle loading, error, and success states explicitly
4. Use staleTime and cacheTime strategically to avoid over-fetching

## TypeScript Requirements:
1. No `any` types - use `unknown` and type guards if needed
2. Define interfaces for all API responses in /src/types
3. Props must be typed (use interfaces, not inline types)
4. Avoid type assertions unless absolutely necessary

## Styling Standards:
1. Tailwind utility classes only (no custom CSS files)
2. Use Tailwind's design tokens (colors, spacing, etc.)
3. Mobile-first responsive design (sm:, md:, lg: breakpoints)
4. Consistent spacing scale (p-4, gap-2, etc.)
5. Dark mode support from day one (use dark: variants)

## Component Patterns:
1. Prefer function components (no class components)
2. Use custom hooks to extract reusable logic
3. Keep components pure (no side effects in render)
4. Lift state up when shared across siblings
5. Use React.memo() sparingly (only for expensive renders)

## Data Fetching:
1. API calls only in pages or custom hooks (never in components)
2. Handle network errors gracefully with user-friendly messages
3. Show loading skeletons (not spinners) for better UX
4. Optimistic updates for mutations when possible

## Performance:
1. Lazy load routes with React.lazy() and Suspense
2. Avoid unnecessary re-renders (check with React DevTools)
3. Debounce user input (search, filters)
4. Virtualize long lists (if >100 items)

## Testing (Post-MVP):
1. Test user interactions with React Testing Library
2. Mock API calls with MSW (Mock Service Worker)
3. Test accessibility (keyboard nav, screen readers)
4. Visual regression tests for critical flows

## Before Committing:
1. Run `npm run build` to catch TypeScript errors
2. Test in both Chrome and Safari (mobile viewport)
3. Verify no console errors or warnings
4. Check that environment variables are documented

## Deployment:
1. Set environment variables in Vercel/Netlify dashboard
2. Verify build succeeds before merging to main
3. Test production build locally with `npm run preview`
4. Monitor Vercel/Netlify logs after deployment