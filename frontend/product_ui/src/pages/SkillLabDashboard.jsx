import React, { useEffect, useState } from "react";
import "./SkillLabDashboard.css";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import {
  Activity,
  Users,
  BookOpen,
  GraduationCap,
  CheckCircle,
  AlertTriangle,
} from "lucide-react";

import {
  getSkillLabSummary,
  getSessionsByProvince,
  getSessionsByMonth,
  getSessionsBySkillLab,
  getLsMcByThematicArea,
  getCompetencyStatus,
  getMenteesByProfession,
  getTopicCoverage,
} from "../api/skilllabApi";

const COLORS = ["#2563eb", "#16a34a", "#f59e0b", "#dc2626", "#7c3aed"];

function KpiCard({ title, value, icon: Icon, note }) {
  return (
    <div className="kpi-card">
      <div>
        <p className="kpi-title">{title}</p>
        <h2>{value}</h2>
        {note && <p className="kpi-note">{note}</p>}
      </div>
      <div className="kpi-icon">
        <Icon size={26} />
      </div>
    </div>
  );
}

function ChartCard({ title, children }) {
  return (
    <div className="chart-card">
      <h3>{title}</h3>
      {children}
    </div>
  );
}

function SkillLabDashboard() {
  const [activeTab, setActiveTab] = useState("kpis");
  const [loading, setLoading] = useState(true);

  const [summary, setSummary] = useState({});
  const [provinceData, setProvinceData] = useState([]);
  const [monthData, setMonthData] = useState([]);
  const [skillLabData, setSkillLabData] = useState([]);
  const [thematicData, setThematicData] = useState([]);
  const [competencyData, setCompetencyData] = useState([]);
  const [professionData, setProfessionData] = useState([]);
  const [topicData, setTopicData] = useState([]);

  useEffect(() => {
    async function loadDashboard() {
      try {
        const [
          summaryRes,
          provinceRes,
          monthRes,
          skillLabRes,
          thematicRes,
          competencyRes,
          professionRes,
          topicRes,
        ] = await Promise.all([
          getSkillLabSummary(),
          getSessionsByProvince(),
          getSessionsByMonth(),
          getSessionsBySkillLab(),
          getLsMcByThematicArea(),
          getCompetencyStatus(),
          getMenteesByProfession(),
          getTopicCoverage(),
        ]);

        setSummary(summaryRes.data);
        setProvinceData(provinceRes.data);
        setMonthData(monthRes.data);
        setSkillLabData(skillLabRes.data);
        setThematicData(thematicRes.data);
        setCompetencyData(competencyRes.data);
        setProfessionData(professionRes.data);
        setTopicData(topicRes.data);
      } catch (error) {
        console.error("Skill Lab dashboard loading error:", error);
      } finally {
        setLoading(false);
      }
    }

    loadDashboard();
  }, []);

  if (loading) {
    return <div className="dashboard-loading">Loading Skill Lab Dashboard...</div>;
  }

  return (
    <div className="skilllab-dashboard">
      <div className="dashboard-header">
        <div>
          <h1>Skill Lab Dashboard</h1>
          <p>Maternal and Newborn Health Skill Lab Monitoring Dashboard</p>
        </div>
      </div>

      <div className="tabs">
        <button className={activeTab === "kpis" ? "active" : ""} onClick={() => setActiveTab("kpis")}>
          Key KPIs
        </button>
        <button className={activeTab === "overview" ? "active" : ""} onClick={() => setActiveTab("overview")}>
          Skill Lab Overview
        </button>
        <button className={activeTab === "topics" ? "active" : ""} onClick={() => setActiveTab("topics")}>
          Topic Coverage
        </button>
        <button className={activeTab === "competency" ? "active" : ""} onClick={() => setActiveTab("competency")}>
          Competency
        </button>
        <button className={activeTab === "mentees" ? "active" : ""} onClick={() => setActiveTab("mentees")}>
          Mentee Profile
        </button>
      </div>

      {activeTab === "kpis" && (
        <>
          <div className="kpi-grid">
            <KpiCard title="Skill Labs" value={summary.total_skill_labs || 0} icon={Activity} />
            <KpiCard title="Sessions" value={summary.total_sessions || 0} icon={BookOpen} />
            <KpiCard title="Mentees" value={summary.total_mentees || 0} icon={Users} />
            <KpiCard title="Participant Records" value={summary.total_participant_records || 0} icon={GraduationCap} />
            <KpiCard title="LS Records" value={summary.ls_count || 0} icon={CheckCircle} />
            <KpiCard title="MC Records" value={summary.mc_count || 0} icon={CheckCircle} />
            <KpiCard title="Completed Sessions" value={summary.completed_sessions || 0} icon={CheckCircle} />
            <KpiCard title="Follow-up Needed" value={summary.followup_needed || 0} icon={AlertTriangle} />
          </div>

          <div className="chart-grid">
            <ChartCard title="Sessions Trend by Month">
              <ResponsiveContainer width="100%" height={320}>
                <LineChart data={monthData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month_label" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="total_sessions" name="Sessions" stroke="#2563eb" strokeWidth={3} />
                </LineChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard title="Sessions by Province">
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={provinceData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="province" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="total_sessions" name="Sessions" fill="#16a34a" />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>
        </>
      )}

      {activeTab === "overview" && (
        <div className="chart-grid">
          <ChartCard title="Sessions by Skill Lab">
            <ResponsiveContainer width="100%" height={420}>
              <BarChart data={skillLabData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis dataKey="skill_lab" type="category" width={180} />
                <Tooltip />
                <Bar dataKey="total_sessions" name="Sessions" fill="#2563eb" />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="LS and MC by Thematic Area">
            <ResponsiveContainer width="100%" height={420}>
              <BarChart data={thematicData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="thematic_area" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="ls_count" name="LS" fill="#2563eb" />
                <Bar dataKey="mc_count" name="MC" fill="#16a34a" />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        </div>
      )}

      {activeTab === "topics" && (
        <div className="table-card">
          <h3>Topic Coverage</h3>
          <table>
            <thead>
              <tr>
                <th>Topic Code</th>
                <th>Topic Name</th>
                <th>Total Records</th>
                <th>LS</th>
                <th>MC</th>
              </tr>
            </thead>
            <tbody>
              {topicData.map((row, index) => (
                <tr key={index}>
                  <td>{row.topic_code}</td>
                  <td>{row.topic_name}</td>
                  <td>{row.total_records}</td>
                  <td>{row.ls_count}</td>
                  <td>{row.mc_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === "competency" && (
        <div className="chart-grid">
          <ChartCard title="Competency Status">
            <ResponsiveContainer width="100%" height={360}>
              <PieChart>
                <Pie
                  data={competencyData}
                  dataKey="total"
                  nameKey="competency_status"
                  outerRadius={120}
                  label
                >
                  {competencyData.map((_, index) => (
                    <Cell key={index} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="Competency Status Bar Chart">
            <ResponsiveContainer width="100%" height={360}>
              <BarChart data={competencyData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="competency_status" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="total" name="Total" fill="#7c3aed" />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        </div>
      )}

      {activeTab === "mentees" && (
        <ChartCard title="Mentees by Profession">
          <ResponsiveContainer width="100%" height={420}>
            <BarChart data={professionData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" />
              <YAxis dataKey="profession" type="category" width={180} />
              <Tooltip />
              <Bar dataKey="total" name="Mentees" fill="#f59e0b" />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      )}
    </div>
  );
}

export default SkillLabDashboard;