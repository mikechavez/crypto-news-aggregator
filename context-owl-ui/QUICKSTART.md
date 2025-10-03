# Quick Start Guide

## 1. Setup Environment

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` and set your API configuration:
```env
VITE_API_URL=http://localhost:8000
VITE_API_KEY=your_api_key_here
```

## 2. Start Development Server

```bash
npm run dev
```

The app will be available at: http://localhost:5173

## 3. Available Pages

- **/** - Signals Dashboard (default)
- **/narratives** - Narrative Clusters
- **/entity/:id** - Entity Detail View

## 4. Next Steps

### Connect to Your Backend

Make sure your Context Owl API is running on the URL specified in `.env`. The frontend expects these endpoints:

- `GET /api/v1/signals`
- `GET /api/v1/narratives`
- `GET /api/v1/entities/:id`
- `GET /api/v1/entities/:id/detail`

### Customize the UI

- **Colors & Theme**: Edit `tailwind.config.js`
- **API Client**: Modify `src/api/client.ts`
- **Add Components**: Create new files in `src/components/`
- **Add Pages**: Create new files in `src/pages/` and add routes in `src/App.tsx`

### Build for Production

```bash
npm run build
npm run preview
```

The production build will be in the `dist/` directory.
