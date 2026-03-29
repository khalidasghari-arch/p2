import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Box, Paper, Typography } from '@mui/material';

export default function ProvinceBarChart({ data }) {
  const safeData = Array.isArray(data) ? [...data] : [];

  // Highest values on top
  safeData.sort((a, b) => (b.value || 0) - (a.value || 0));

  return (
    <Paper sx={{ p: 3, height: '100%' }}>
      <Typography variant="h6" sx={{ mb: 2, fontWeight: 700 }}>
        Visits by Province
      </Typography>

      <Box sx={{ width: '100%', height: 420 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={safeData}
            layout="vertical"
            margin={{ top: 10, right: 30, left: 60, bottom: 10 }}
            barCategoryGap={10}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#e6ebf1" />
            <XAxis
              type="number"
              tick={{ fill: '#5e6c84', fontSize: 13 }}
              axisLine={{ stroke: '#cfd8e3' }}
              tickLine={{ stroke: '#cfd8e3' }}
            />
            <YAxis
              type="category"
              dataKey="province"
              width={140}
              tick={{ fill: '#5e6c84', fontSize: 12 }}
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
            <Bar
              dataKey="value"
              fill="#00897b"
              radius={[0, 8, 8, 0]}
              maxBarSize={28}
            />
          </BarChart>
        </ResponsiveContainer>
      </Box>
    </Paper>
  );
}