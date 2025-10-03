# Context Owl UI - Project Structure

## Overview

A complete React + TypeScript frontend built with Vite, featuring:
- ✅ React 18 with TypeScript
- ✅ Tailwind CSS for styling
- ✅ React Query for data fetching
- ✅ React Router for navigation
- ✅ Fully typed API client
- ✅ Responsive UI components

## Directory Structure

```
context-owl-ui/
├── src/
│   ├── api/                    # API Integration Layer
│   │   ├── client.ts          # Base HTTP client with auth
│   │   ├── signals.ts         # Signals API endpoints
│   │   ├── narratives.ts      # Narratives API endpoints
│   │   ├── entities.ts        # Entities API endpoints
│   │   └── index.ts           # API exports
│   │
│   ├── components/            # Reusable UI Components
│   │   ├── Card.tsx           # Card container components
│   │   ├── Layout.tsx         # App layout with navigation
│   │   ├── Loading.tsx        # Loading states
│   │   └── ErrorMessage.tsx   # Error display
│   │
│   ├── pages/                 # Route Pages
│   │   ├── Signals.tsx        # Market signals dashboard
│   │   ├── Narratives.tsx     # Narrative clusters view
│   │   └── EntityDetail.tsx   # Entity deep dive
│   │
│   ├── types/                 # TypeScript Definitions
│   │   └── index.ts           # All type definitions
│   │
│   ├── lib/                   # Utilities
│   │   ├── formatters.ts      # Date, number, sentiment formatters
│   │   └── cn.ts              # ClassName utility
│   │
│   ├── App.tsx                # Main app with routing setup
│   ├── main.tsx               # Entry point
│   └── index.css              # Tailwind directives
│
├── .env.example               # Environment template
├── README.md                  # Full documentation
├── QUICKSTART.md              # Quick start guide
├── tailwind.config.js         # Tailwind configuration
├── postcss.config.js          # PostCSS configuration
├── vite.config.ts             # Vite configuration
└── package.json               # Dependencies

```

## Key Features Implemented

### 1. Type-Safe API Client
- Centralized HTTP client with authentication
- Typed request/response interfaces
- Error handling
- Query parameter support

### 2. React Query Integration
- Automatic caching and refetching
- Loading and error states
- Optimistic updates ready

### 3. Routing
- `/` - Signals dashboard
- `/narratives` - Narratives view
- `/entity/:id` - Entity details

### 4. UI Components
- Responsive layout with navigation
- Card-based design system
- Loading spinners
- Error messages with retry

### 5. Utility Functions
- Date formatting (relative and absolute)
- Number formatting
- Sentiment analysis display
- Signal strength indicators

## Configuration Files

### Environment Variables (.env)
```env
VITE_API_URL=http://localhost:8000
VITE_API_KEY=your_api_key_here
```

### Tailwind Config
- Content paths configured for React
- Extensible theme
- PostCSS integration

## Next Steps

1. **Start Development**: `npm run dev`
2. **Configure API**: Update `.env` with your backend URL
3. **Customize**: Modify components and styles as needed
4. **Deploy**: Build with `npm run build`

## Dependencies

### Core
- react: ^18.3.1
- react-dom: ^18.3.1
- react-router-dom: ^7.1.3
- @tanstack/react-query: ^5.62.14

### Styling
- tailwindcss: ^3.4.17
- autoprefixer: ^10.4.20
- postcss: ^8.4.49

### Build Tools
- vite: ^7.1.9
- typescript: ~5.6.2
- @vitejs/plugin-react: ^4.3.4

## Development Workflow

1. Make changes to source files
2. Vite HMR updates instantly
3. TypeScript checks types
4. Tailwind compiles styles
5. React Query manages data

All set up and ready to go! 🚀
