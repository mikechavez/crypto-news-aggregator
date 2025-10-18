import type { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { TrendingUp, Newspaper, FileText, Moon, Sun } from 'lucide-react';
import { cn } from '../lib/cn';
import { useTheme } from '../contexts/ThemeContext';

interface LayoutProps {
  children: ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const location = useLocation();
  const { theme, toggleTheme } = useTheme();

  const navItems = [
    { path: '/signals', label: 'Signals', icon: TrendingUp },
    { path: '/narratives', label: 'Narratives', icon: Newspaper },
    { path: '/articles', label: 'Articles', icon: FileText },
  ];

  return (
    <div className="h-screen flex flex-col bg-gray-50 dark:bg-dark-bg overscroll-none">
      <nav className="flex-shrink-0 bg-white dark:bg-dark-card shadow-sm border-b border-gray-200 dark:border-dark-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center">
                <h1 className="text-2xl font-bold text-blue-600">Context Owl</h1>
              </div>
              <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                {navItems.map((item) => {
                  const Icon = item.icon;
                  return (
                    <Link
                      key={item.path}
                      to={item.path}
                      className={cn(
                        'inline-flex items-center gap-2 px-1 pt-1 border-b-2 text-sm font-medium',
                        location.pathname === item.path
                          ? 'border-blue-500 text-gray-900 dark:text-gray-100'
                          : 'border-transparent text-gray-500 dark:text-gray-400 hover:border-gray-300 hover:text-gray-700 dark:hover:text-gray-300'
                      )}
                    >
                      <Icon className="w-4 h-4" />
                      {item.label}
                    </Link>
                  );
                })}
              </div>
            </div>
            <div className="flex items-center">
              <button
                onClick={toggleTheme}
                className="p-2 rounded-lg bg-gray-100 dark:bg-dark-hover hover:bg-gray-200 dark:hover:bg-dark-border transition-colors"
                aria-label="Toggle theme"
              >
                {theme === 'dark' ? (
                  <Sun className="w-5 h-5 text-gray-900 dark:text-gray-100" />
                ) : (
                  <Moon className="w-5 h-5 text-gray-900 dark:text-gray-100" />
                )}
              </button>
            </div>
          </div>
        </div>
      </nav>

      <main className="flex-1 overflow-y-auto max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
    </div>
  );
}
