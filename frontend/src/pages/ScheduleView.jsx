import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Box, Typography, Paper, CircularProgress, 
  Grid, Card, CardContent, Divider, 
  Chip, Button, Alert, Stack, 
  LinearProgress, IconButton, Tooltip
} from '@mui/material';
import { 
  AccessTime as TimeIcon, 
  Event as EventIcon,
  Refresh as RefreshIcon,
  ArrowBack as ArrowBackIcon,
  PriorityHigh as PriorityIcon,
  CheckCircle as CheckCircleIcon,
  Schedule as ScheduleIcon
} from '@mui/icons-material';
import { format, parseISO } from 'date-fns';
import api from '../services/api';

// Default user ID
const DEFAULT_USER_ID = "default_user";

// Priority colors
const getPriorityColor = (priority) => {
  switch (priority) {
    case 5: return { color: '#d32f2f', label: 'Highest' };
    case 4: return { color: '#f57c00', label: 'High' };
    case 3: return { color: '#0288d1', label: 'Medium' };
    case 2: return { color: '#388e3c', label: 'Low' };
    case 1: return { color: '#616161', label: 'Lowest' };
    default: return { color: '#616161', label: 'Normal' };
  }
};

// Status colors
const getStatusColor = (status) => {
  switch (status) {
    case 'completed': return '#4caf50';
    case 'in_progress': return '#2196f3';
    case 'pending': return '#ff9800';
    default: return '#9e9e9e';
  }
};

// Format time
const formatTime = (timeString) => {
  if (!timeString) return 'N/A';
  try {
    const date = parseISO(timeString);
    return format(date, 'h:mm a');
  } catch (error) {
    console.error('Error formatting time:', error);
    return 'Invalid time';
  }
};

const ScheduleView = () => {
  const { date } = useParams();
  const navigate = useNavigate();
  const [schedule, setSchedule] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    fetchSchedule();
  }, [date]);
  
  const fetchSchedule = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const formattedDate = date || format(new Date(), 'yyyy-MM-dd');
      
      // Fetch tasks for the specified date
      const response = await api.get(`/api/scheduler/daily/${formattedDate}`, {
        params: { user_id: DEFAULT_USER_ID }
      });
      
      // Sort tasks by scheduled_start_time
      const sortedTasks = response.data.sort((a, b) => {
        if (!a.scheduled_start_time) return 1;
        if (!b.scheduled_start_time) return -1;
        return new Date(a.scheduled_start_time) - new Date(b.scheduled_start_time);
      });
      
      setSchedule(sortedTasks);
    } catch (err) {
      console.error('Error fetching schedule:', err);
      setError('Failed to load schedule. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleRegenerate = () => {
    navigate(`/scheduler/generate?date=${date || format(new Date(), 'yyyy-MM-dd')}`);
  };
  
  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
        <CircularProgress />
      </Box>
    );
  }
  
  // Parse the date for display
  const displayDate = date ? format(parseISO(date), 'EEEE, MMMM d, yyyy') : format(new Date(), 'EEEE, MMMM d, yyyy');
  
  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={3}>
        <Box display="flex" alignItems="center">
          <IconButton onClick={() => navigate(-1)} sx={{ mr: 2 }}>
            <ArrowBackIcon />
          </IconButton>
          <Typography variant="h4">
            Daily Schedule: {displayDate}
          </Typography>
        </Box>
        <Button 
          variant="contained" 
          color="primary" 
          startIcon={<RefreshIcon />}
          onClick={handleRegenerate}
        >
          Regenerate Schedule
        </Button>
      </Stack>
      
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}
      
      {schedule.length === 0 ? (
        <Paper elevation={3} sx={{ p: 4, textAlign: 'center', mt: 2 }}>
          <ScheduleIcon sx={{ fontSize: 60, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            No scheduled tasks found for this date
          </Typography>
          <Typography variant="body2" color="text.secondary" mb={3}>
            You don't have any scheduled tasks for this day. Would you like to generate a schedule?
          </Typography>
          <Button 
            variant="contained" 
            onClick={handleRegenerate}
            startIcon={<ScheduleIcon />}
          >
            Generate Schedule
          </Button>
        </Paper>
      ) : (
        <Box>
          {/* Timeline view */}
          <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
              <TimeIcon sx={{ mr: 1 }} /> Timeline
            </Typography>
            <Divider sx={{ mb: 2 }} />
            <Box sx={{ position: 'relative', pt: 1, pb: 1 }}>
              {/* Timeline line */}
              <Box sx={{ position: 'absolute', left: '20px', top: 0, bottom: 0, width: '2px', bgcolor: 'divider' }} />
              
              {schedule.map((task, index) => {
                const priorityStyle = getPriorityColor(task.priority);
                
                return (
                  <Box key={task.id} sx={{ 
                    position: 'relative', 
                    pl: 5, 
                    pb: 3,
                    '&:last-child': { pb: 0 }
                  }}>
                    {/* Timeline dot */}
                    <Box sx={{ 
                      position: 'absolute', 
                      left: '16px', 
                      width: '10px', 
                      height: '10px', 
                      borderRadius: '50%', 
                      bgcolor: getStatusColor(task.status),
                      border: '2px solid white',
                      zIndex: 1,
                      mt: 1
                    }} />
                    
                    {/* Time label */}
                    <Typography variant="body2" color="text.secondary" fontWeight="bold" sx={{ mb: 0.5 }}>
                      {formatTime(task.scheduled_start_time)} - {formatTime(task.scheduled_end_time)}
                    </Typography>
                    
                    {/* Task card */}
                    <Card sx={{ 
                      borderLeft: `4px solid ${priorityStyle.color}`,
                      backgroundColor: task.status === 'completed' ? 'rgba(76, 175, 80, 0.08)' : 'inherit'
                    }}>
                      <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                        <Box display="flex" justifyContent="space-between" alignItems="center">
                          <Typography variant="subtitle1" fontWeight="500">{task.name}</Typography>
                          <Chip 
                            size="small" 
                            icon={<PriorityIcon />} 
                            label={`Priority: ${priorityStyle.label}`} 
                            sx={{ bgcolor: `${priorityStyle.color}20`, color: priorityStyle.color }}
                          />
                        </Box>
                        <Typography variant="body2" color="text.secondary" mt={1}>
                          {task.description || "No description provided"}
                        </Typography>
                        <Box display="flex" justifyContent="space-between" alignItems="center" mt={1}>
                          <Chip 
                            size="small" 
                            label={`${task.duration} min`} 
                            variant="outlined"
                          />
                          <Chip 
                            size="small" 
                            label={task.status.charAt(0).toUpperCase() + task.status.slice(1)} 
                            sx={{ bgcolor: `${getStatusColor(task.status)}20`, color: getStatusColor(task.status) }}
                          />
                        </Box>
                      </CardContent>
                    </Card>
                  </Box>
                );
              })}
            </Box>
          </Paper>
          
          {/* Schedule summary */}
          <Paper elevation={3} sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
              <EventIcon sx={{ mr: 1 }} /> Schedule Summary
            </Typography>
            <Divider sx={{ mb: 2 }} />
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6} md={3}>
                <Box textAlign="center" p={2}>
                  <Typography variant="h4">{schedule.length}</Typography>
                  <Typography variant="body2" color="text.secondary">Total Tasks</Typography>
                </Box>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Box textAlign="center" p={2}>
                  <Typography variant="h4">
                    {schedule.reduce((total, task) => total + (task.duration || 0), 0)} min
                  </Typography>
                  <Typography variant="body2" color="text.secondary">Total Duration</Typography>
                </Box>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Box textAlign="center" p={2}>
                  <Typography variant="h4">
                    {schedule.filter(task => task.priority >= 4).length}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">High Priority Tasks</Typography>
                </Box>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Box textAlign="center" p={2}>
                  <Typography variant="h4">
                    {schedule.filter(task => task.status === 'completed').length}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">Completed Tasks</Typography>
                </Box>
              </Grid>
            </Grid>
            <Box mt={3} display="flex" justifyContent="center">
              <Button 
                variant="outlined" 
                startIcon={<ArrowBackIcon />}
                onClick={() => navigate('/')}
              >
                Back to Dashboard
              </Button>
            </Box>
          </Paper>
        </Box>
      )}
    </Box>
  );
};

export default ScheduleView; 