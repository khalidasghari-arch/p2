import client from "./client";

const cleanParams = (params) => {
  return Object.fromEntries(
    Object.entries(params).filter(
      ([, value]) => value !== "" && value !== null && value !== undefined
    )
  );
};

export const getDashboardFilters = async (province, district) => {
  const res = await client.get("/product/dashboard/filters/", {
    params: cleanParams({ province, district }),
  });

  return res.data;
};

export const getDashboardSummary = async (province, district, facility, year) => {
  const res = await client.get("/product/dashboard/summary/", {
    params: cleanParams({ province, district, facility, year }),
  });

  return res.data;
};

export const getDashboardTrends = async (province, district, facility, year) => {
  const res = await client.get("/product/dashboard/trends/", {
    params: cleanParams({ province, district, facility, year }),
  });

  return res.data;
};

export const getDashboardByProvince = async (
  province,
  district,
  facility,
  year
) => {
  const res = await client.get("/product/dashboard/by-province/", {
    params: cleanParams({ province, district, facility, year }),
  });

  return res.data;
};

export const getTopFacilities = async (province, district, facility, year) => {
  const res = await client.get("/product/dashboard/top-facilities/", {
    params: cleanParams({ province, district, facility, year }),
  });

  return res.data;
};