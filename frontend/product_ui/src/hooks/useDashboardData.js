import { useQuery } from "@tanstack/react-query";

import {
  getDashboardFilters,
  getDashboardSummary,
  getDashboardTrends,
  getDashboardByProvince,
  getTopFacilities,
} from "../api/dashboardApi";

export function useDashboardFilters(province, district) {
  return useQuery({
    queryKey: ["dashboard-filters", province, district],
    queryFn: () => getDashboardFilters(province, district),
    staleTime: 5 * 60 * 1000,
  });
}

export function useDashboardSummary(province, district, facility, year) {
  return useQuery({
    queryKey: ["dashboard-summary", province, district, facility, year],
    queryFn: () => getDashboardSummary(province, district, facility, year),
    staleTime: 5 * 60 * 1000,
    select: (data) => ({
      total_visits: Number(data?.total_visits || 0),
      reporting_facilities: Number(data?.reporting_facilities || 0),
      total_facilities: Number(data?.total_facilities || 0),
      reporting_rate: Number(data?.reporting_rate || 0),
    }),
  });
}

export function useDashboardTrends(province, district, facility, year) {
  return useQuery({
    queryKey: ["dashboard-trends", province, district, facility, year],
    queryFn: () => getDashboardTrends(province, district, facility, year),
    staleTime: 5 * 60 * 1000,
    select: (data) => Array.isArray(data) ? data : [],
  });
}

export function useDashboardByProvince(province, district, facility, year) {
  return useQuery({
    queryKey: ["dashboard-by-province", province, district, facility, year],
    queryFn: () => getDashboardByProvince(province, district, facility, year),
    staleTime: 5 * 60 * 1000,
    select: (data) => Array.isArray(data) ? data : [],
  });
}

export function useTopFacilities(province, district, facility, year) {
  return useQuery({
    queryKey: ["dashboard-top-facilities", province, district, facility, year],
    queryFn: () => getTopFacilities(province, district, facility, year),
    staleTime: 5 * 60 * 1000,
    select: (data) => Array.isArray(data) ? data : [],
  });
}