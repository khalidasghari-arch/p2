import { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  CircularProgress,
  Grid,
  Stack,
  Typography,
} from '@mui/material';

import KpiCard from '../components/common/KpiCard';
import TrendChart from '../components/common/TrendChart';
import ProvinceBarChart from '../components/common/ProvinceBarChart';
import TopFacilitiesChart from '../components/common/TopFacilitiesChart';
import DashboardFilters from '../components/common/DashboardFilters';

import {
  useDashboardFilters,
  useDashboardSummary,
  useDashboardTrends,
  useDashboardByProvince,
  useTopFacilities,
} from '../hooks/useDashboardData';

export default function DashboardPage() {
  const [province, setProvince] = useState('');
  const [district, setDistrict] = useState('');
  const [facility, setFacility] = useState('');
  const [year, setYear] = useState('');

  const filtersQuery = useDashboardFilters(province, district);
  const summaryQuery = useDashboardSummary(province, district, facility, year);
  const trendsQuery = useDashboardTrends(province, district, facility, year);
  const provinceQuery = useDashboardByProvince(province, district, facility, year);
  const topFacilitiesQuery = useTopFacilities(province, district, facility, year);

  useEffect(() => {
    setDistrict('');
    setFacility('');
  }, [province]);

  useEffect(() => {
    setFacility('');
  }, [district]);

  const isLoading =
    filtersQuery.isLoading ||
    summaryQuery.isLoading ||
    trendsQuery.isLoading ||
    provinceQuery.isLoading ||
    topFacilitiesQuery.isLoading;

  const isError =
    filtersQuery.isError ||
    summaryQuery.isError ||
    trendsQuery.isError ||
    provinceQuery.isError ||
    topFacilitiesQuery.isError;

  if (isLoading) {
    return (
      <Box sx={{ py: 10, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (isError) {
    return <Alert severity="error">Failed to load dashboard data.</Alert>;
  }

  const filterOptions = filtersQuery.data;
  const summary = summaryQuery.data;
  const trends = trendsQuery.data;
  const provinceData = provinceQuery.data;
  const topFacilities = topFacilitiesQuery.data;

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="h4" sx={{ fontWeight: 800, mb: 0.5 }}>
          Dashboard Overview
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Review mentorship performance, reporting coverage, and trends across facilities and provinces.
        </Typography>
      </Box>

      <DashboardFilters
        province={province}
        setProvince={setProvince}
        district={district}
        setDistrict={setDistrict}
        facility={facility}
        setFacility={setFacility}
        year={year}
        setYear={setYear}
        filterOptions={filterOptions}
      />

      <Grid container spacing={3}>
        <Grid item xs={12} sm={6} lg={3}>
          <KpiCard
            title="Total Visits"
            value={summary.total_visits}
            subtitle="All recorded mentorship visits"
          />
        </Grid>

        <Grid item xs={12} sm={6} lg={3}>
          <KpiCard
            title="Reporting Facilities"
            value={summary.reporting_facilities}
            subtitle="Facilities with at least one visit"
          />
        </Grid>

        <Grid item xs={12} sm={6} lg={3}>
          <KpiCard
            title="Total Facilities"
            value={summary.total_facilities}
            subtitle="Facilities in current scope"
          />
        </Grid>

        <Grid item xs={12} sm={6} lg={3}>
          <KpiCard
            title="Reporting Rate"
            value={`${summary.reporting_rate}%`}
            subtitle="Reporting facilities / total facilities"
          />
        </Grid>
      </Grid>

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: {
            xs: '1fr',
            lg: '1.4fr 1fr',
          },
          gap: 3,
          alignItems: 'stretch',
        }}
      >
        <TrendChart data={trends} />
        <ProvinceBarChart data={provinceData} />
      </Box>

      <TopFacilitiesChart data={topFacilities} />
    </Stack>
  );
}