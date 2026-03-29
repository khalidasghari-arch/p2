import { AppBar, Box, Toolbar, Typography } from '@mui/material';

export default function Topbar() {
  return (
    <AppBar
      position="sticky"
      elevation={0}
      sx={{
        backgroundColor: 'rgba(255,255,255,0.9)',
        backdropFilter: 'blur(8px)',
        borderBottom: '1px solid #e6ebf1',
        color: 'text.primary',
      }}
    >
      <Toolbar
        sx={{
          minHeight: '72px !important',
          display: 'flex',
          justifyContent: 'space-between',
        }}
      >
        <Box>
          <Typography variant="h6" sx={{ fontWeight: 700, lineHeight: 1.2 }}>
            Mentorship Analytics Dashboard
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Province, year, and performance monitoring overview
          </Typography>
        </Box>
      </Toolbar>
    </AppBar>
  );
}