import { Routes, Route } from 'react-router-dom';
import { Analytics } from '@vercel/analytics/react';

import Layout from './components/Layout.jsx';
import UploadPage from './pages/UploadPage.jsx';
import ReviewPage from './pages/ReviewPage.jsx';
import BatchPage from './pages/BatchPage.jsx';
import NotFoundPage from './pages/NotFoundPage.jsx';

export default function App() {
  return (
    <>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<UploadPage />} />
          <Route path="/results/:sessionId" element={<ReviewPage />} />
          <Route path="/batch" element={<BatchPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
      <Analytics />
    </>
  );
}
