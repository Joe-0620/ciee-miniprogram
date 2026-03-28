import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { App as AntApp, ConfigProvider, theme as antdTheme } from 'antd';
import zhCN from 'antd/locale/zh_CN';


const STORAGE_KEY = 'dashboard-theme-mode';
const MEDIA_QUERY = '(prefers-color-scheme: dark)';

const DashboardThemeContext = createContext(null);

function isBrowser() {
  return typeof window !== 'undefined';
}

function getSystemThemeMode() {
  if (!isBrowser() || typeof window.matchMedia !== 'function') {
    return 'light';
  }
  return window.matchMedia(MEDIA_QUERY).matches ? 'dark' : 'light';
}

function getInitialThemeMode() {
  if (!isBrowser()) {
    return 'system';
  }
  const stored = window.localStorage.getItem(STORAGE_KEY);
  return ['light', 'dark', 'system'].includes(stored) ? stored : 'system';
}

export function DashboardThemeProvider({ children }) {
  const [themeMode, setThemeMode] = useState(getInitialThemeMode);
  const [systemThemeMode, setSystemThemeMode] = useState(getSystemThemeMode);

  const resolvedThemeMode = themeMode === 'system' ? systemThemeMode : themeMode;

  useEffect(() => {
    if (!isBrowser() || typeof window.matchMedia !== 'function') {
      return undefined;
    }

    const mediaQuery = window.matchMedia(MEDIA_QUERY);
    const handleChange = (event) => setSystemThemeMode(event.matches ? 'dark' : 'light');

    if (typeof mediaQuery.addEventListener === 'function') {
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    }

    mediaQuery.addListener(handleChange);
    return () => mediaQuery.removeListener(handleChange);
  }, []);

  useEffect(() => {
    if (!isBrowser()) {
      return;
    }
    window.localStorage.setItem(STORAGE_KEY, themeMode);
  }, [themeMode]);

  useEffect(() => {
    if (!isBrowser()) {
      return;
    }
    document.documentElement.dataset.dashboardTheme = resolvedThemeMode;
    document.documentElement.dataset.dashboardThemeMode = themeMode;
    document.documentElement.style.colorScheme = resolvedThemeMode;
  }, [resolvedThemeMode, themeMode]);

  const configTheme = useMemo(
    () => ({
      algorithm:
        resolvedThemeMode === 'dark'
          ? [antdTheme.darkAlgorithm]
          : [antdTheme.defaultAlgorithm],
      token: {
        colorPrimary: '#0f766e',
        borderRadius: 16,
        borderRadiusLG: 20,
        wireframe: false,
      },
      components: {
        Layout: {
          headerBg: 'transparent',
          siderBg: 'transparent',
          bodyBg: 'transparent',
          triggerBg: 'transparent',
        },
        Menu: {
          darkItemBg: 'transparent',
          darkSubMenuItemBg: 'transparent',
          darkItemSelectedBg: 'rgba(20, 184, 166, 0.24)',
          darkItemSelectedColor: '#ffffff',
          darkItemHoverBg: 'rgba(255, 255, 255, 0.08)',
        },
        Card: {
          headerBg: 'transparent',
        },
      },
    }),
    [resolvedThemeMode],
  );

  const contextValue = useMemo(
    () => ({
      themeMode,
      resolvedThemeMode,
      setThemeMode,
    }),
    [resolvedThemeMode, themeMode],
  );

  return (
    <DashboardThemeContext.Provider value={contextValue}>
      <ConfigProvider locale={zhCN} theme={configTheme}>
        <AntApp>{children}</AntApp>
      </ConfigProvider>
    </DashboardThemeContext.Provider>
  );
}

export function useDashboardTheme() {
  const context = useContext(DashboardThemeContext);
  if (!context) {
    throw new Error('useDashboardTheme must be used within DashboardThemeProvider');
  }
  return context;
}
