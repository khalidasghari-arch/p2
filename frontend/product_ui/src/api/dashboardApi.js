import client from './client';

export const getDashboardFilters = async (province, district) => {
  const res = await client.get('/product/dashboard/filters/', {
    params: { province, district },
  });
  return res.data;
};

export const getDashboardSummary = async (province, district, facility, year) => {
  const res = await client.get('/product/dashboard/summary/', {
    params: { province, district, facility, year },
  });
  return res.data;
};

export const getDashboardTrends = async (province, district, facility, year) => {
  const res = await client.get('/product/dashboard/trends/', {
    params: { province, district, facility, year },
  });
  return res.data;
};

export const getDashboardByProvince = async (province, district, facility, year) => {
  const res = await client.get('/product/dashboard/by-province/', {
    params: { province, district, facility, year },
  });
  return res.data;
};