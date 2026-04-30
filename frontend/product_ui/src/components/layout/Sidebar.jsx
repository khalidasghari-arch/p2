import {
  Box,
  Drawer,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Typography,
} from '@mui/material';
import DashboardRoundedIcon from '@mui/icons-material/DashboardRounded';
import ShowChartRoundedIcon from '@mui/icons-material/ShowChartRounded';
import { Link, useLocation } from 'react-router-dom';

const drawerWidth = 260;

const menu = [
  { name: 'Dashboard', path: '/', icon: <DashboardRoundedIcon /> },
  { name: 'Trends', path: '/trends', icon: <ShowChartRoundedIcon /> },
];

export default function Sidebar() {
  const location = useLocation();

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: drawerWidth,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: drawerWidth,
          boxSizing: 'border-box',
          borderRight: '1px solid #e6ebf1',
          background: 'linear-gradient(180deg, #ffffff 0%, #f8fafc 100%)',
        },
      }}
    >
      <Toolbar
        sx={{
          minHeight: '72px !important',
          display: 'flex',
          alignItems: 'center',
          px: 3,
        }}
      >
        <Box>
          <Typography variant="h6" sx={{ fontWeight: 700, lineHeight: 1.2 }}>
            MNHIMS Dashboard
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Analytics Portal
          </Typography>
        </Box>
      </Toolbar>

      <Box sx={{ px: 2, pb: 2 }}>
        <List sx={{ display: 'grid', gap: 1 }}>
          {menu.map((item) => {
            const selected = location.pathname === item.path;
            return (
              <ListItemButton
                key={item.name}
                component={Link}
                to={item.path}
                selected={selected}
                sx={{
                  borderRadius: 3,
                  py: 1.2,
                  px: 1.5,
                  color: selected ? 'primary.main' : 'text.primary',
                  bgcolor: selected ? 'rgba(21, 101, 192, 0.08)' : 'transparent',
                  border: selected ? '1px solid rgba(21, 101, 192, 0.15)' : '1px solid transparent',
                  '&:hover': {
                    bgcolor: 'rgba(21, 101, 192, 0.06)',
                  },
                  '& .MuiListItemIcon-root': {
                    minWidth: 40,
                    color: selected ? 'primary.main' : 'text.secondary',
                  },
                }}
              >
                <ListItemIcon>{item.icon}</ListItemIcon>
                <ListItemText
                  primary={item.name}
                  primaryTypographyProps={{
                    fontWeight: selected ? 700 : 500,
                  }}
                />
              </ListItemButton>
            );
          })}
        </List>
      </Box>
    </Drawer>
  );
}