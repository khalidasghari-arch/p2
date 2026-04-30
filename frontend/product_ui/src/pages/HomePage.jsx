import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Grid,
  Stack,
  Typography,
} from "@mui/material";
import FavoriteIcon from "@mui/icons-material/Favorite";
import LocalHospitalIcon from "@mui/icons-material/LocalHospital";
import GroupsIcon from "@mui/icons-material/Groups";
import SchoolIcon from "@mui/icons-material/School";
import MapIcon from "@mui/icons-material/Map";
import InsightsIcon from "@mui/icons-material/Insights";

const carouselImages = [
  {
    src: "https://images.unsplash.com/photo-1584515933487-779824d29309?auto=format&fit=crop&w=1200&q=80",
    title: "Mother and newborn care",
  },
  {
    src: "https://images.unsplash.com/photo-1576765608535-5f04d1e3f289?auto=format&fit=crop&w=1200&q=80",
    title: "Facility-based quality care",
  },
  {
    src: "https://images.unsplash.com/photo-1576091160550-2173dba999ef?auto=format&fit=crop&w=1200&q=80",
    title: "Data for decision-making",
  },
];

const quickLinks = [
  {
    title: "Mentorship Dashboard",
    text: "Review visits, reporting coverage, province trends, and facility performance.",
    link: "/dashboard",
    button: "Open Dashboard",
    icon: GroupsIcon,
  },
  {
    title: "Skill Lab Dashboard",
    text: "Monitor learning sessions, coaching, topic coverage, and competency progress.",
    link: "/skilllab-dashboard",
    button: "Open Skill Lab",
    icon: SchoolIcon,
  },
  {
    title: "Trends",
    text: "Explore monthly trends and compare program performance over time.",
    link: "/trends",
    button: "View Trends",
    icon: InsightsIcon,
  },
];

const monitorAreas = [
  { title: "Maternal Care", icon: FavoriteIcon },
  { title: "Newborn Care", icon: LocalHospitalIcon },
  { title: "Mentorship Visits", icon: GroupsIcon },
  { title: "Skill Lab Sessions", icon: SchoolIcon },
  { title: "Facility Reporting", icon: MapIcon },
  { title: "Quality Improvement", icon: InsightsIcon },
];

function AnimatedCounter({ value, suffix = "" }) {
  const [count, setCount] = useState(0);

  useEffect(() => {
    let start = 0;
    const end = Number(value) || 0;
    const duration = 900;
    const stepTime = 20;
    const steps = duration / stepTime;
    const increment = end / steps;

    const timer = setInterval(() => {
      start += increment;
      if (start >= end) {
        setCount(end);
        clearInterval(timer);
      } else {
        setCount(Math.floor(start));
      }
    }, stepTime);

    return () => clearInterval(timer);
  }, [value]);

  return (
    <Typography variant="h4" sx={{ fontWeight: 900, color: "#0f2748" }}>
      {count}
      {suffix}
    </Typography>
  );
}

export default function HomePage() {
  const [activeImage, setActiveImage] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setActiveImage((prev) => (prev + 1) % carouselImages.length);
    }, 3500);

    return () => clearInterval(timer);
  }, []);

  const stats = useMemo(
    () => [
      { label: "Mentorship Visits", value: 196 },
      { label: "Reporting Rate", value: 92, suffix: "%" },
      { label: "Facilities", value: 50 },
      { label: "Skill Lab Mentees", value: 306 },
    ],
    []
  );

  const currentImage = carouselImages[activeImage];

  return (
    <Box sx={{ minHeight: "100vh" }}>
      {/* HERO */}
      <Box
        sx={{
          borderRadius: "28px",
          p: { xs: 3, md: 5 },
          mb: 3,
          color: "white",
          background: "linear-gradient(135deg, #0f766e 0%, #1d4ed8 55%, #2563eb 100%)",
          boxShadow: "0 18px 40px rgba(15, 23, 42, 0.18)",
          overflow: "hidden",
        }}
      >
        <Grid container spacing={4} alignItems="center">
          <Grid item xs={12} md={7}>
            <Chip
              label="MNHIMS Analytics Portal"
              sx={{
                mb: 2,
                bgcolor: "rgba(255,255,255,0.2)",
                color: "white",
                fontWeight: 800,
              }}
            />

            <Typography
              variant="h3"
              sx={{
                fontWeight: 900,
                lineHeight: 1.15,
                fontSize: { xs: "2rem", md: "3rem" },
              }}
            >
              Maternal and Newborn Health Information Management System
            </Typography>

            <Typography
              variant="h6"
              sx={{
                mt: 2,
                maxWidth: 850,
                opacity: 0.95,
                lineHeight: 1.6,
                fontWeight: 400,
              }}
            >
              A unified platform for monitoring mentorship, skill lab learning,
              quality improvement, facility performance, and program progress.
            </Typography>

            {/* <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ mt: 4 }}>
              <Button
                component={Link}
                to="/dashboard"
                variant="contained"
                size="large"
                sx={{
                  bgcolor: "white",
                  color: "#0f2748",
                  fontWeight: 900,
                  borderRadius: "14px",
                  px: 3,
                  "&:hover": { bgcolor: "#eef6ff" },
                }}
              >
                Open Mentorship Dashboard
              </Button>

              <Button
                component={Link}
                to="/skilllab-dashboard"
                variant="outlined"
                size="large"
                sx={{
                  color: "white",
                  borderColor: "white",
                  fontWeight: 900,
                  borderRadius: "14px",
                  px: 3,
                  "&:hover": {
                    borderColor: "white",
                    bgcolor: "rgba(255,255,255,0.12)",
                  },
                }}
              >
                Open Skill Lab Dashboard
              </Button>
            </Stack> */}
          </Grid>

          {/* IMAGE CAROUSEL */}
          <Grid item xs={12} md={5}>
            <Box
              sx={{
                position: "relative",
                borderRadius: "24px",
                overflow: "hidden",
                boxShadow: "0 18px 40px rgba(0,0,0,0.28)",
                height: { xs: 240, md: 340 },
              }}
            >
              <Box
                component="img"
                src={currentImage.src}
                alt={currentImage.title}
                sx={{
                  width: "100%",
                  height: "100%",
                  objectFit: "cover",
                  display: "block",
                }}
              />

              <Box
                sx={{
                  position: "absolute",
                  left: 0,
                  right: 0,
                  bottom: 0,
                  p: 2,
                  background: "linear-gradient(transparent, rgba(0,0,0,0.65))",
                }}
              >
                <Typography sx={{ fontWeight: 900 }}>{currentImage.title}</Typography>

                <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                  {carouselImages.map((_, index) => (
                    <Box
                      key={index}
                      onClick={() => setActiveImage(index)}
                      sx={{
                        width: index === activeImage ? 24 : 8,
                        height: 8,
                        borderRadius: "99px",
                        bgcolor: "white",
                        opacity: index === activeImage ? 1 : 0.5,
                        cursor: "pointer",
                        transition: "all 0.25s ease",
                      }}
                    />
                  ))}
                </Stack>
              </Box>
            </Box>
          </Grid>
        </Grid>
      </Box>

      {/* STATS */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {stats.map((item) => (
          <Grid item xs={12} sm={6} md={3} key={item.label}>
            <Card sx={{ borderRadius: "22px", boxShadow: "0 8px 24px rgba(15,23,42,0.08)" }}>
              <CardContent>
                <AnimatedCounter value={item.value} suffix={item.suffix || ""} />
                <Typography color="text.secondary" sx={{ fontWeight: 700 }}>
                  {item.label}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* QUICK ACCESS */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h5" sx={{ fontWeight: 900, mb: 1 }}>
          Quick Access
        </Typography>
        <Typography color="text.secondary" sx={{ mb: 2 }}>
          Select a dashboard to start reviewing program data.
        </Typography>

        <Grid container spacing={2}>
          {quickLinks.map((item) => {
            const Icon = item.icon;
            return (
              <Grid item xs={12} md={4} key={item.title}>
                <Card
                  sx={{
                    height: "100%",
                    borderRadius: "22px",
                    boxShadow: "0 8px 24px rgba(15, 23, 42, 0.08)",
                    border: "1px solid #e2e8f0",
                  }}
                >
                  <CardContent sx={{ p: 3 }}>
                    <Box
                      sx={{
                        width: 48,
                        height: 48,
                        borderRadius: "16px",
                        bgcolor: "#eff6ff",
                        color: "#2563eb",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        mb: 2,
                      }}
                    >
                      <Icon />
                    </Box>

                    <Typography variant="h6" sx={{ fontWeight: 900, mb: 1 }}>
                      {item.title}
                    </Typography>

                    <Typography color="text.secondary" sx={{ minHeight: 72, lineHeight: 1.6 }}>
                      {item.text}
                    </Typography>

                    <Button
                      component={Link}
                      to={item.link}
                      variant="contained"
                      sx={{
                        mt: 2,
                        borderRadius: "12px",
                        fontWeight: 900,
                        background: "linear-gradient(135deg, #2563eb, #0f766e)",
                      }}
                    >
                      {item.button}
                    </Button>
                  </CardContent>
                </Card>
              </Grid>
            );
          })}
        </Grid>
      </Box>

      {/* MONITORING + MAP */}
      <Grid container spacing={2}>
        <Grid item xs={12} md={7}>
          <Box
            sx={{
              borderRadius: "24px",
              bgcolor: "white",
              p: { xs: 2.5, md: 3 },
              boxShadow: "0 8px 24px rgba(15, 23, 42, 0.06)",
              border: "1px solid #e2e8f0",
              height: "100%",
            }}
          >
            <Typography variant="h5" sx={{ fontWeight: 900, mb: 1 }}>
              What We Monitor
            </Typography>

            <Typography color="text.secondary" sx={{ mb: 2 }}>
              Core program areas tracked through routine facility and learning data.
            </Typography>

            <Grid container spacing={1.5}>
              {monitorAreas.map((item) => {
                const Icon = item.icon;
                return (
                  <Grid item xs={12} sm={6} key={item.title}>
                    <Box
                      sx={{
                        p: 2,
                        borderRadius: "16px",
                        bgcolor: "#f8fafc",
                        border: "1px solid #e2e8f0",
                        display: "flex",
                        alignItems: "center",
                        gap: 1.5,
                        fontWeight: 900,
                        color: "#0f2748",
                      }}
                    >
                      <Icon sx={{ color: "#0f766e" }} />
                      {item.title}
                    </Box>
                  </Grid>
                );
              })}
            </Grid>
          </Box>
        </Grid>

        <Grid item xs={12} md={5}>
          <Box
            sx={{
              borderRadius: "24px",
              bgcolor: "white",
              p: 3,
              boxShadow: "0 8px 24px rgba(15, 23, 42, 0.06)",
              border: "1px solid #e2e8f0",
              height: "100%",
            }}
          >
            <Typography variant="h5" sx={{ fontWeight: 900, mb: 1 }}>
              Geographic Coverage
            </Typography>

            <Typography color="text.secondary" sx={{ mb: 2 }}>
              Province and facility-level monitoring preview.
            </Typography>

            {/* MAP PREVIEW */}
            <Box
              sx={{
                height: 280,
                borderRadius: "20px",
                bgcolor: "#e0f2fe",
                position: "relative",
                overflow: "hidden",
                border: "1px solid #bfdbfe",
              }}
            >
              <Box
                sx={{
                  position: "absolute",
                  inset: 0,
                  background:
                    "radial-gradient(circle at 25% 35%, #0f766e 0 5px, transparent 6px), radial-gradient(circle at 55% 45%, #2563eb 0 5px, transparent 6px), radial-gradient(circle at 70% 30%, #f59e0b 0 5px, transparent 6px), radial-gradient(circle at 40% 70%, #16a34a 0 5px, transparent 6px), radial-gradient(circle at 75% 75%, #dc2626 0 5px, transparent 6px)",
                }}
              />

              <Box
                sx={{
                  position: "absolute",
                  left: "14%",
                  top: "22%",
                  width: "72%",
                  height: "58%",
                  border: "3px solid rgba(15, 39, 72, 0.18)",
                  borderRadius: "45% 35% 48% 42%",
                  transform: "rotate(-8deg)",
                  bgcolor: "rgba(255,255,255,0.45)",
                }}
              />

              <Box
                sx={{
                  position: "absolute",
                  left: 18,
                  bottom: 18,
                  bgcolor: "white",
                  borderRadius: "16px",
                  p: 1.5,
                  boxShadow: "0 8px 20px rgba(15,23,42,0.12)",
                }}
              >
                <Typography sx={{ fontWeight: 900, fontSize: 13 }}>
                  Coverage Preview
                </Typography>
                <Typography sx={{ fontSize: 12, color: "#64748b" }}>
                  Provinces • Facilities • Skill Labs
                </Typography>
              </Box>
            </Box>
          </Box>
        </Grid>
      </Grid>
    </Box>
  );
}