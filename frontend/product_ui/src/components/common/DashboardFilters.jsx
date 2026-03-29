import { MenuItem, Paper, Stack, TextField, Typography, Box } from '@mui/material';

export default function DashboardFilters({
  province,
  setProvince,
  district,
  setDistrict,
  facility,
  setFacility,
  year,
  setYear,
  filterOptions,
}) {
  const provinces = filterOptions?.provinces || [];
  const districts = filterOptions?.districts || [];
  const facilities = filterOptions?.facilities || [];
  const years = filterOptions?.years || [];

  return (
    <Paper sx={{ p: 2.5, mb: 3 }}>
      <Stack
        direction={{ xs: 'column', md: 'row' }}
        spacing={2}
        alignItems={{ xs: 'stretch', md: 'center' }}
        justifyContent="space-between"
      >
        <Box>
          <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
            Filters
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Filter dashboard by province, district, facility, and year
          </Typography>
        </Box>

        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} flexWrap="wrap">
          <TextField
            select
            label="Province"
            value={province}
            onChange={(e) => setProvince(e.target.value)}
            sx={{ minWidth: 200 }}
          >
            <MenuItem value="">All Provinces</MenuItem>
            {provinces.map((item) => (
              <MenuItem key={item.id} value={item.id}>
                {item.name}
              </MenuItem>
            ))}
          </TextField>

          <TextField
            select
            label="District"
            value={district}
            onChange={(e) => setDistrict(e.target.value)}
            sx={{ minWidth: 200 }}
            disabled={districts.length === 0}
          >
            <MenuItem value="">All Districts</MenuItem>
            {districts.map((item) => (
              <MenuItem key={item.id} value={item.id}>
                {item.name}
              </MenuItem>
            ))}
          </TextField>

          <TextField
            select
            label="Facility"
            value={facility}
            onChange={(e) => setFacility(e.target.value)}
            sx={{ minWidth: 260 }}
            disabled={facilities.length === 0}
          >
            <MenuItem value="">All Facilities</MenuItem>
            {facilities.map((item) => (
              <MenuItem key={item.id} value={item.id}>
                {item.name}
              </MenuItem>
            ))}
          </TextField>

          <TextField
            select
            label="Year"
            value={year}
            onChange={(e) => setYear(e.target.value)}
            sx={{ minWidth: 160 }}
          >
            <MenuItem value="">All Years</MenuItem>
            {years.map((item) => (
              <MenuItem key={item} value={item}>
                {item}
              </MenuItem>
            ))}
          </TextField>
        </Stack>
      </Stack>
    </Paper>
  );
}