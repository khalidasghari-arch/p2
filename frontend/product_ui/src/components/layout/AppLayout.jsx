import { NavLink, Outlet } from "react-router-dom";
import {
  Box,
  Drawer,
  List,
  ListItemButton,
  ListItemText,
  Typography,
} from "@mui/material";

const drawerWidth = 220;

export default function AppLayout({ children }) {
  const menuItems = [
    { label: "Dashboard", path: "/" },
    { label: "Skill Lab Dashboard", path: "/skilllab-dashboard" },
    { label: "Trends", path: "/trends" },
  ];

  return (
    <Box sx={{ display: "flex", minHeight: "100vh", bgcolor: "#eef3f8" }}>
      <Drawer
        variant="permanent"
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          "& .MuiDrawer-paper": {
            width: drawerWidth,
            boxSizing: "border-box",
            borderRight: "1px solid #e2e8f0",
            bgcolor: "#ffffff",
            px: 1.5,
            py: 2,
          },
        }}
      >
        <Box sx={{ mb: 3, px: 1 }}>
          <Typography variant="h6" sx={{ fontWeight: 800, color: "#0f2748" }}>
            MNH Dashboard
          </Typography>
          <Typography variant="caption" sx={{ color: "#64748b" }}>
            Analytics Portal
          </Typography>
        </Box>

        <List sx={{ p: 0 }}>
          {menuItems.map((item) => (
            <ListItemButton
              key={item.path}
              component={NavLink}
              to={item.path}
              end={item.path === "/"}
              sx={{
                mb: 1,
                borderRadius: "18px",
                px: 2,
                py: 1.2,
                color: "#0f2748",
                "&.active": {
                  bgcolor: "#dff1ff",
                  color: "#0067c5",
                  fontWeight: 700,
                },
                "&:hover": {
                  bgcolor: "#eef6ff",
                },
              }}
            >
              <ListItemText
                primary={item.label}
                primaryTypographyProps={{
                  fontSize: 14,
                  fontWeight: 600,
                }}
              />
            </ListItemButton>
          ))}
        </List>
      </Drawer>

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: { xs: 2, md: 2.5 },
          ml: 0,
          minHeight: "100vh",
          overflowX: "hidden",
        }}
      >
        {children || <Outlet />}
      </Box>
    </Box>
  );
}