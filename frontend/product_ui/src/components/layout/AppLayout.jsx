import { Box } from '@mui/material';
import Sidebar from './Sidebar';
import Topbar from './Topbar';

export default function AppLayout({ children }) {
  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
      <Sidebar />

      <Box sx={{ flexGrow: 1, minWidth: 0 }}>
        <Topbar />

        <Box
          sx={{
            px: { xs: 2, sm: 3, md: 4 },
            py: 3,
          }}
        >
          <Box
            sx={{
              width: '100%',
              maxWidth: 1700,
              mx: 'auto',
            }}
          >
            {children}
          </Box>
        </Box>
      </Box>
    </Box>
  );
}