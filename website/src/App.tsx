import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ThemeProvider } from "@/components/ThemeProvider";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Explore from "./pages/Explore";

const App = () => (
  <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
    <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false} disableTransitionOnChange>
      <TooltipProvider>
        <Toaster />
        <Routes>
          <Route path="/" element={<Navigate to="/explore" replace />} />
          <Route path="/explore" element={<Explore />} />
          <Route path="*" element={<Navigate to="/explore" replace />} />
        </Routes>
      </TooltipProvider>
    </ThemeProvider>
  </BrowserRouter>
);

export default App;
