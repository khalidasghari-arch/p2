import axios from "axios";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api";

const api = axios.create({
  baseURL: `${API_BASE_URL}/skilllab/dashboard`,
});

export const getSkillLabSummary = () => api.get("/summary/");
export const getSessionsByProvince = () => api.get("/sessions-by-province/");
export const getSessionsByMonth = () => api.get("/sessions-by-month/");
export const getSessionsBySkillLab = () => api.get("/sessions-by-skill-lab/");
export const getLsMcByThematicArea = () => api.get("/ls-mc-by-thematic-area/");
export const getCompetencyStatus = () => api.get("/competency-status/");
export const getMenteesByProfession = () => api.get("/mentees-by-profession/");
export const getTopicCoverage = () => api.get("/topic-coverage/");