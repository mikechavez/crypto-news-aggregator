import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { Briefing } from './pages/Briefing';
import { Signals } from './pages/Signals';
import { Narratives } from './pages/Narratives';
import { Articles } from './pages/Articles';
import { CostMonitor } from './pages/CostMonitor';
// import { EntityDetail } from './pages/EntityDetail';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 30000, // 30 seconds
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Briefing />} />
            <Route path="/signals" element={<Signals />} />
            <Route path="/narratives" element={<Narratives />} />
            <Route path="/articles" element={<Articles />} />
            <Route path="/cost-monitor" element={<CostMonitor />} />
            {/* TODO: Uncomment when backend /api/v1/entities endpoints are implemented */}
            {/* <Route path="/entity/:id" element={<EntityDetail />} /> */}
          </Routes>
        </Layout>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
