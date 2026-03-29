import { Paper, Stack, Typography } from '@mui/material';

export default function TrendsPage() {
  return (
    <Stack spacing={3}>
      <div>
        <Typography variant="h4" sx={{ fontWeight: 800, mb: 0.5 }}>
          Trends
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Additional analytical views can be added here.
        </Typography>
      </div>

      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" sx={{ fontWeight: 700, mb: 1 }}>
          Trends Module
        </Typography>
        <Typography variant="body2" color="text.secondary">
          This page is ready for more detailed charts such as top facilities, district comparisons, and indicator trends.
        </Typography>
      </Paper>
    </Stack>
  );
}