import { useEffect, useState } from "react";
// import { Link } from "react-router-dom";

import {
  Alert,
  Box,
  CircularProgress,
  Grid,
  Stack,
  Typography,
} from "@mui/material";

import KpiCard from "../components/common/KpiCard";
import TrendChart from "../components/common/TrendChart";
import ProvinceBarChart from "../components/common/ProvinceBarChart";
import TopFacilitiesChart from "../components/common/TopFacilitiesChart";
import DashboardFilters from "../components/common/DashboardFilters";

import {
  useDashboardFilters,
  useDashboardSummary,
  useDashboardTrends,
  useDashboardByProvince,
  useTopFacilities,
} from "../hooks/useDashboardData";

export default function DashboardPage() {
  const [province, setProvince] = useState("");
  const [district, setDistrict] = useState("");
  const [facility, setFacility] = useState("");
  const [year, setYear] = useState("");

  const filtersQuery = useDashboardFilters(province, district);
  const summaryQuery = useDashboardSummary(province, district, facility, year);
  const trendsQuery = useDashboardTrends(province, district, facility, year);
  const provinceQuery = useDashboardByProvince(province, district, facility, year);
  const topFacilitiesQuery = useTopFacilities(province, district, facility, year);

  // Reset dependent filters
  useEffect(() => {
    setDistrict("");
    setFacility("");
  }, [province]);

  useEffect(() => {
    setFacility("");
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
      <Box sx={{ py: 10, display: "flex", justifyContent: "center" }}>
        <CircularProgress />
      </Box>
    );
  }

  if (isError) {
    return (
      <Alert severity="error" sx={{ mt: 4 }}>
        Failed to load dashboard data. Please try again.
      </Alert>
    );
  }

  const filterOptions = filtersQuery.data || {};
  const summary = summaryQuery.data || {};
  const trends = trendsQuery.data || [];
  const provinceData = provinceQuery.data || [];
  const topFacilities = topFacilitiesQuery.data || [];

  return (
    <Stack spacing={3}>
      {/* ===== HEADER ===== */}
      <Box>
        <Typography variant="h4" sx={{ fontWeight: 800 }}>
          Dashboard Overview
        </Typography>

        <Typography variant="body1" color="text.secondary">
          Review mentorship performance, reporting coverage, and trends across facilities and provinces.
        </Typography>

        {/* ✅ BUTTON (VISIBLE ALWAYS) */}
        {/* <Box sx={{ mt: 2 }}>
          <Link to="/skilllab-dashboard" style={{ textDecoration: "none" }}>
            <Button
              variant="contained"
              sx={{
                background: "linear-gradient(135deg, #2563eb, #0f766e)",
                borderRadius: "12px",
                fontWeight: 600,
                px: 3,
                py: 1,
              }}
            >
              Open Skill Lab Dashboard
            </Button>
          </Link>
        </Box> */}
      </Box>

      {/* ===== FILTERS ===== */}
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

      {/* ===== KPI CARDS ===== */}
      <Grid container spacing={3}>
        <Grid item xs={12} sm={6} lg={3}>
          <KpiCard
            title="Total Visits"
            value={summary.total_visits ?? 0}
            subtitle="All recorded mentorship visits"
          />
        </Grid>

        <Grid item xs={12} sm={6} lg={3}>
          <KpiCard
            title="Reporting Facilities"
            value={summary.reporting_facilities ?? 0}
            subtitle="Facilities with at least one visit"
          />
        </Grid>

        <Grid item xs={12} sm={6} lg={3}>
          <KpiCard
            title="Total Facilities"
            value={summary.total_facilities ?? 0}
            subtitle="Facilities in current scope"
          />
        </Grid>

        <Grid item xs={12} sm={6} lg={3}>
          <KpiCard
            title="Reporting Rate"
            value={`${summary.reporting_rate ?? 0}%`}
            subtitle="Reporting facilities / total facilities"
          />
        </Grid>
      </Grid>

      {/* ===== CHARTS ===== */}
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            lg: "1.4fr 1fr",
          },
          gap: 3,
        }}
      >
        <TrendChart data={trends} />
        <ProvinceBarChart data={provinceData} />
      </Box>

      {/* ===== TOP FACILITIES ===== */}
      <TopFacilitiesChart data={topFacilities} />
    </Stack>
  );
}