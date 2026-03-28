import React from 'react';
import ReactDOM from 'react-dom/client';

import App from './App';
import './index.css';
import { DashboardThemeProvider } from './theme/DashboardThemeProvider';


ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <DashboardThemeProvider>
        <App />
    </DashboardThemeProvider>
  </React.StrictMode>,
);
