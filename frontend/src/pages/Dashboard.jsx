import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  Box, Typography, Grid, Paper, Button, 
  CircularProgress, Divider, List, ListItem, 
  ListItemText, ListItemIcon, Chip, Alert
} from '@mui/material';
import { 
  CalendarToday as CalendarIcon,
  Assignment as TaskIcon,
  Check as CheckIcon,
  Pending as PendingIcon,
  Error as ErrorIcon,
  ArrowForward as ArrowForwardIcon
} from '@mui/icons-material';
import api from '../services/api';
import { format } from 'date-fns';

// Default user ID for all tasks since we removed authentication
const DEFAULT_USER_ID = "default_user";

const Dashboard = () => {
  const [isLoading, setIsLoading] = useState(true);
  const [taskStats, setTaskStats] = useState({
    total: 0,
    completed: 0,
    pending: 0,
    overdue: 0
  });
  const [upcomingTasks, setUpcomingTasks] = useState([]);
  const [error, setError] = useState(null);
  const [retryCount, setRetryCount] = useState(0);
  const [hasSchedule, setHasSchedule] = useState(false);
  
  useEffect(() => {
    const fetchDashboardData = async () => {
      setIsLoading(true);
      setError(null);
      
      try {
        // Get today's date in YYYY-MM-DD format
        const today = format(new Date(), 'yyyy-MM-dd');
        
        console.log(`Fetching tasks for date: ${today} with user_id: ${DEFAULT_USER_ID}`);
        
        // Fetch today's tasks with default user_id
        const tasksResponse = await api.get(`/api/calendar/day/${today}`, {
          params: { user_id: DEFAULT_USER_ID }
        });
        
        console.log('Tasks response:', tasksResponse);
        const tasks = tasksResponse.data || [];
        
        // Check if any tasks are scheduled for today (have scheduled_start_time)
        const scheduledTasks = tasks.filter(task => task.scheduled_start_time);
        setHasSchedule(scheduledTasks.length > 0);
        
        // Calculate task statistics
        const completed = tasks.filter(task => task.status === 'completed').length;
        const pending = tasks.filter(task => task.status === 'pending' || task.status === 'in_progress').length;
        const overdue = tasks.filter(task => {
          if (task.status !== 'completed' && task.deadline) {
            const deadlineDate = new Date(task.deadline);
            return deadlineDate < new Date();
          }
          return false;
        }).length;
        
        setTaskStats({
          total: tasks.length,
          completed,
          pending,
          overdue
        });
        
        // Get upcoming tasks (pending tasks sorted by priority)
        const upcoming = tasks
          .filter(task => task.status === 'pending' || task.status === 'in_progress')
          .sort((a, b) => b.priority - a.priority)
          .slice(0, 5);
        
        setUpcomingTasks(upcoming);
      } catch (err) {
        console.error('Error fetching dashboard data:', err);
        setError('Failed to load dashboard data. Please try again later.');
        
        // If error is 500, create a mock dashboard for demonstration
        if (err.response && err.response.status === 500) {
          console.log('Creating mock dashboard data for demonstration');
          setTaskStats({
            total: 5,
            completed: 2,
            pending: 2,
            overdue: 1
          });
          
          setUpcomingTasks([
            {
              id: 'mock1',
              name: 'Complete project proposal',
              duration: 60,
              priority: 5,
              status: 'pending'
            },
            {
              id: 'mock2',
              name: 'Team meeting',
              duration: 30,
              priority: 4,
              status: 'pending'
            }
          ]);
        }
      } finally {
        setIsLoading(false);
      }
    };
    
    // Retry fetching data a few times if needed
    if (retryCount < 3) {
      fetchDashboardData();
    }
  }, [retryCount]);
  
  const handleRetry = () => {
    setRetryCount(prevCount => prevCount + 1);
  };
  
  const getPriorityColor = (priority) => {
    switch (priority) {
      case 5: return 'error';
      case 4: return 'warning';
      case 3: return 'success';
      default: return 'default';
    }
  };
  
  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
        <CircularProgress />
      </Box>
    );
  }
  
  return (
    <Box>
      {error && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {error}
          <Button onClick={handleRetry} size="small" sx={{ ml: 2 }}>
            Retry
          </Button>
        </Alert>
      )}

      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Typography variant="h4">Dashboard</Typography>
        <Typography variant="subtitle1">
          {format(new Date(), 'EEEE, MMMM d, yyyy')}
        </Typography>
      </Box>
      
      {/* Task Statistics */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 3, textAlign: 'center', height: '100%' }}>
            <TaskIcon color="primary" sx={{ fontSize: 40, mb: 1 }} />
            <Typography variant="h4">{taskStats.total}</Typography>
            <Typography variant="body1" color="text.secondary">Total Tasks</Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 3, textAlign: 'center', height: '100%' }}>
            <CheckIcon color="success" sx={{ fontSize: 40, mb: 1 }} />
            <Typography variant="h4">{taskStats.completed}</Typography>
            <Typography variant="body1" color="text.secondary">Completed</Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 3, textAlign: 'center', height: '100%' }}>
            <PendingIcon color="primary" sx={{ fontSize: 40, mb: 1 }} />
            <Typography variant="h4">{taskStats.pending}</Typography>
            <Typography variant="body1" color="text.secondary">Pending</Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 3, textAlign: 'center', height: '100%' }}>
            <ErrorIcon color="error" sx={{ fontSize: 40, mb: 1 }} />
            <Typography variant="h4">{taskStats.overdue}</Typography>
            <Typography variant="body1" color="text.secondary">Overdue</Typography>
          </Paper>
        </Grid>
      </Grid>
      
      {/* Upcoming Tasks */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">Upcoming Tasks</Typography>
              <Button 
                component={Link} 
                to="/tasks" 
                size="small" 
                endIcon={<ArrowForwardIcon />}
              >
                View All
              </Button>
            </Box>
            <Divider sx={{ mb: 2 }} />
            
            {upcomingTasks.length > 0 ? (
              <List>
                {upcomingTasks.map((task) => (
                  <ListItem key={task.id} sx={{ px: 1 }}>
                    <ListItemIcon>
                      <CalendarIcon color="primary" />
                    </ListItemIcon>
                    <ListItemText 
                      primary={task.name}
                      secondary={`Duration: ${task.duration} min`}
                    />
                    <Chip 
                      label={`Priority ${task.priority}`} 
                      size="small" 
                      color={getPriorityColor(task.priority)} 
                      variant="outlined"
                    />
                  </ListItem>
                ))}
              </List>
            ) : (
              <Typography variant="body1" color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
                No upcoming tasks for today
              </Typography>
            )}
          </Paper>
        </Grid>
        
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">Quick Actions</Typography>
            </Box>
            <Divider sx={{ mb: 3 }} />
            
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <Button 
                  component={Link}
                  to="/tasks"
                  variant="outlined" 
                  fullWidth 
                  startIcon={<TaskIcon />}
                  sx={{ py: 1.5 }}
                >
                  Create New Task
                </Button>
              </Grid>
              <Grid item xs={12} sm={6}>
                <Button 
                  component={Link}
                  to="/calendar"
                  variant="outlined" 
                  fullWidth 
                  startIcon={<CalendarIcon />}
                  sx={{ py: 1.5 }}
                >
                  View Calendar
                </Button>
              </Grid>
              <Grid item xs={12}>
                {hasSchedule ? (
                  <Grid container spacing={2}>
                    <Grid item xs={12} sm={6}>
                      <Button 
                        component={Link}
                        to={`/schedule/view/${format(new Date(), 'yyyy-MM-dd')}`}
                        variant="contained" 
                        color="primary"
                        fullWidth 
                        sx={{ py: 1.5, mt: 1 }}
                      >
                        View Today's Schedule
                      </Button>
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <Button 
                        component={Link}
                        to={`/scheduler/generate?date=${format(new Date(), 'yyyy-MM-dd')}`}
                        variant="outlined"
                        color="secondary" 
                        fullWidth 
                        sx={{ py: 1.5, mt: 1 }}
                      >
                        Regenerate Schedule
                      </Button>
                    </Grid>
                  </Grid>
                ) : (
                  <Button 
                    component={Link}
                    to="/scheduler/generate"
                    variant="contained" 
                    fullWidth 
                    sx={{ py: 1.5, mt: 1 }}
                  >
                    Generate Today's Schedule
                  </Button>
                )}
              </Grid>
            </Grid>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard; 