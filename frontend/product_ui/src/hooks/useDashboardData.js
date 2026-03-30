import { useQuery } from '@tanstack/react-query';
import {
  getDashboardFilters,
  getDashboardSummary,
  getDashboardTrends,
  getDashboardByProvince,
  getTopFacilities,
} from '../api/dashboardApi';

export function useDashboardFilters(province, district) {
  return useQuery({
    queryKey: ['dashboard-filters', province, district],
    queryFn: () => getDashboardFilters(province, district),
  });
}

export function useDashboardSummary(province, district, facility, year) {
  return useQuery({
    queryKey: ['dashboard-summary', province, district, facility, year],
    queryFn: () => getDashboardSummary(province, district, facility, year),
  });
}

export function useDashboardTrends(province, district, facility, year) {
  return useQuery({
    queryKey: ['dashboard-trends', province, district, facility, year],
    queryFn: () => getDashboardTrends(province, district, facility, year),
  });
}

export function useDashboardByProvince(province, district, facility, year) {
  return useQuery({
    queryKey: ['dashboard-by-province', province, district, facility, year],
    queryFn: () => getDashboardByProvince(province, district, facility, year),
  });
}

export function useTopFacilities(province, district, facility, year) {
  return useQuery({
    queryKey: ['dashboard-top-facilities', province, district, facility, year],
    queryFn: () => getTopFacilities(province, district, facility, year),
  });
}