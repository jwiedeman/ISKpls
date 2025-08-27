import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import './index.css';
import App from './App';
import { TypeNameProvider } from './TypeNamesContext';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <TypeNameProvider>
        <App />
      </TypeNameProvider>
    </BrowserRouter>
  </StrictMode>
);
