import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Box, Paper, Typography } from '@mui/material';

export default function TrendChart({ data }) {
  const safeData = Array.isArray(data) ? data : [];

  return (
    <Paper sx={{ p: 3, height: '100%' }}>
      <Typography variant="h6" sx={{ mb: 2, fontWeight: 700 }}>
        Monthly Trend
      </Typography>

      <Box sx={{ width: '100%', height: 420 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={safeData}
            margin={{ top: 10, right: 30, left: 10, bottom: 10 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#e6ebf1" />
            <XAxis
              dataKey="month"
              tick={{ fill: '#5e6c84', fontSize: 13 }}
              axisLine={{ stroke: '#cfd8e3' }}
              tickLine={{ stroke: '#cfd8e3' }}
            />
            <YAxis
              tick={{ fill: '#5e6c84', fontSize: 13 }}
              axisLine={{ stroke: '#cfd8e3' }}
              tickLine={{ stroke: '#cfd8e3' }}
            />
            <Tooltip
              contentStyle={{
                borderRadius: 12,
                border: '1px solid #e6ebf1',
                boxShadow: '0 8px 24px rgba(16,24,40,0.08)',
              }}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke="#1565c0"
              strokeWidth={3}
              dot={{ r: 4, strokeWidth: 2, fill: '#ffffff' }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </Box>
    </Paper>
  );
}