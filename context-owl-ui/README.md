# Context Owl UI

A modern React frontend for the Context Owl crypto news aggregator, providing real-time insights into market signals and emerging narratives.

## Features

- 📊 **Market Signals Dashboard** - Real-time detection of unusual market activity
- 📰 **Narrative Clustering** - Emerging trends and story clusters
- 🔍 **Entity Deep Dive** - Detailed views of crypto entities with signals and mentions
- ⚡ **Fast & Responsive** - Built with Vite and React Query for optimal performance
- 🎨 **Modern UI** - Tailwind CSS for a clean, professional interface

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **React Router** - Client-side routing
- **React Query** - Data fetching and caching
- **Tailwind CSS** - Utility-first styling

## Getting Started

### Prerequisites

- Node.js 18+ and npm

### Installation

1. Install dependencies:
```bash
npm install
```

2. Create a `.env` file from the example:
```bash
cp .env.example .env
```

3. Update the `.env` file with your API configuration:
```env
VITE_API_URL=http://localhost:8000
VITE_API_KEY=your_api_key_here
```

### Development

Start the development server:
```bash
npm run dev
```

The app will be available at `http://localhost:5173`

### Build

Create a production build:
```bash
npm run build
```

Preview the production build:
```bash
npm run preview
```

## Project Structure

```
src/
├── api/              # API client and endpoint functions
│   ├── client.ts     # Base API client
│   ├── signals.ts    # Signals API
│   ├── narratives.ts # Narratives API
│   └── entities.ts   # Entities API
├── components/       # Reusable UI components
│   ├── Card.tsx
│   ├── Layout.tsx
│   ├── Loading.tsx
│   └── ErrorMessage.tsx
├── pages/            # Page components
│   ├── Signals.tsx
│   ├── Narratives.tsx
│   └── EntityDetail.tsx
├── types/            # TypeScript type definitions
│   └── index.ts
├── lib/              # Utility functions
│   ├── formatters.ts # Date, number, and data formatters
│   └── cn.ts         # Class name utility
├── App.tsx           # Main app component with routing
└── main.tsx          # App entry point
```

## API Integration

The app connects to the Context Owl API. Ensure your backend is running and accessible at the URL specified in your `.env` file.

### API Endpoints Used

- `GET /api/v1/signals` - Fetch market signals
- `GET /api/v1/narratives` - Fetch narrative clusters
- `GET /api/v1/entities/:id` - Fetch entity details
- `GET /api/v1/entities/:id/detail` - Fetch comprehensive entity data

## Development

### Code Style

- Use TypeScript for type safety
- Follow React best practices and hooks patterns
- Use Tailwind utility classes for styling
- Keep components small and focused

### Adding New Features

1. Define TypeScript types in `src/types/`
2. Create API functions in `src/api/`
3. Build reusable components in `src/components/`
4. Create page components in `src/pages/`
5. Add routes in `src/App.tsx`

## License

MIT
