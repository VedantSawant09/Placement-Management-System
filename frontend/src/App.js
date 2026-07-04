import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { Container, Box } from '@mui/material';

// Components
import Navbar from './components/Navbar';
import StudentLogin from './pages/StudentLogin';
import StudentRegister from './pages/StudentRegister';
import StudentDashboard from './pages/StudentDashboard';
import StudentProfile from './pages/StudentProfile';
import AptitudeTest from './pages/AptitudeTest';
import AdminLogin from './pages/AdminLogin';
import AdminRegister from './pages/AdminRegister';
import AdminDashboard from './pages/AdminDashboard';
import StudentManagement from './pages/StudentManagement';

// Context
import { AuthProvider } from './context/AuthContext';

const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
  typography: {
    h4: {
      fontWeight: 600,
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AuthProvider>
        <Router>
          <Box sx={{ flexGrow: 1, minHeight: '100vh', bgcolor: '#f5f5f5' }}>
            <Navbar />
            <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
              <Routes>
                {/* Default route - redirect to student login */}
                <Route path="/" element={<Navigate to="/student/login" />} />

                {/* Student Routes */}
                <Route path="/student/login" element={<StudentLogin />} />
                <Route path="/student/register" element={<StudentRegister />} />
                <Route path="/student/dashboard" element={<StudentDashboard />} />
                <Route path="/student/profile" element={<StudentProfile />} />
                <Route path="/student/test" element={<AptitudeTest />} />

                {/* Admin Routes */}
                <Route path="/admin/login" element={<AdminLogin />} />
                <Route path="/admin/register" element={<AdminRegister />} />
                <Route path="/admin/dashboard" element={<AdminDashboard />} />
                <Route path="/admin/students" element={<StudentManagement />} />
              </Routes>
            </Container>
          </Box>
        </Router>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;