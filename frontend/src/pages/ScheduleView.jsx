import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { 
  Box, Typography, Paper, CircularProgress, 
  Grid, Card, CardContent, Divider, 
  Chip, Button, Alert, Stack, 
  LinearProgress, IconButton, Tooltip,
  Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, Collapse, Zoom, Fade,
  FormControl, InputLabel, Select, MenuItem,
  Snackbar
} from '@mui/material';
import MuiAlert from '@mui/material/Alert';
import { 
  AccessTime as TimeIcon, 
  Event as EventIcon,
  Refresh as RefreshIcon,
  ArrowBack as ArrowBackIcon,
  PriorityHigh as PriorityIcon,
  CheckCircle as CheckCircleIcon,
  Schedule as ScheduleIcon,
  Add as AddIcon,
  Coffee as CoffeeIcon,
  LocalCafe as LocalCafeIcon,
  Done as DoneIcon,
  DoneAll as DoneAllIcon
} from '@mui/icons-material';
import { format, parseISO, addMinutes } from 'date-fns';
import api from '../services/api';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { LocalizationProvider, DateTimePicker } from '@mui/x-date-pickers';

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
    case 'break': return '#9c27b0'; // Purple color for breaks
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
  const location = useLocation();
  const navigate = useNavigate();
  const [schedule, setSchedule] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [hoverIndex, setHoverIndex] = useState(null); // Track which gap is being hovered
  const [breakDialogOpen, setBreakDialogOpen] = useState(false);
  const [selectedGap, setSelectedGap] = useState(null);
  const [breakDuration, setBreakDuration] = useState(15); // Default break duration: 15 minutes
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  // State for task completion dialog
  const [completeDialogOpen, setCompleteDialogOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState(null);
  const [isSubmittingTaskUpdate, setIsSubmittingTaskUpdate] = useState(false);
  const [taskUpdateForm, setTaskUpdateForm] = useState({
    actual_start_time: null,
    actual_end_time: null,
    status: 'completed'
  });
  
  // Snackbar notification state
  const [snackbar, setSnackbar] = useState({
    open: false,
    message: '',
    severity: 'success'
  });
  
  useEffect(() => {
    // Extract refresh parameter from URL
    const queryParams = new URLSearchParams(location.search);
    const refreshParam = queryParams.get('refresh');
    
    // Always fetch the schedule when the component mounts or date changes
    fetchSchedule();
    
    // If there's a refresh parameter, remove it from the URL to prevent unnecessary refreshes
    if (refreshParam) {
      // Replace the current URL without the refresh parameter
      navigate(`/schedule/view/${date}`, { replace: true });
      console.log('Detected refresh parameter, schedule data was refreshed');
    }
  }, [date, location.search]);
  
  // Add a new effect to restore breaks after schedule regeneration
  useEffect(() => {
    const restoreBreaksAfterRegeneration = async () => {
      // Check if we have just regenerated the schedule and have breaks to restore
      const preservedBreaksJSON = localStorage.getItem('preserved_breaks');
      
      if (preservedBreaksJSON && schedule.length > 0) {
        try {
          const preservedBreaks = JSON.parse(preservedBreaksJSON);
          
          if (preservedBreaks.length > 0) {
            console.log("Found preserved breaks to restore:", preservedBreaks);
            
            // Remove any existing breaks that might have been regenerated
            const scheduleWithoutBreaks = schedule.filter(task => task.status !== 'break');
            
            if (scheduleWithoutBreaks.length === 0) {
              console.log("No tasks found in schedule to position breaks between");
              return;
            }
            
            // Re-add preserved breaks to the schedule
            const updatedSchedule = [...scheduleWithoutBreaks];
            
            // For each preserved break, find the best position to reinsert it
            for (const breakTask of preservedBreaks) {
              // Store the original break position relative to tasks
              // We need to find the task that comes before this break based on the original sequence
              const originalBreakTime = new Date(breakTask.scheduled_start_time);
              
              // Find the task that should come just before this break
              let previousTaskIndex = -1;
              let previousTaskEndTime = null;
              let earliestNextTaskStartTime = null;
              
              // First, find the task that ended right before this break in the original schedule
              for (let i = 0; i < updatedSchedule.length; i++) {
                const taskEndTime = updatedSchedule[i].scheduled_end_time ? 
                  new Date(updatedSchedule[i].scheduled_end_time) : null;
                  
                const taskStartTime = updatedSchedule[i].scheduled_start_time ?
                  new Date(updatedSchedule[i].scheduled_start_time) : null;
                
                if (taskEndTime && taskEndTime <= originalBreakTime) {
                  // This task ends before or at the break's original start time
                  // If it's the latest such task we've found, update our reference
                  if (previousTaskEndTime === null || taskEndTime > previousTaskEndTime) {
                    previousTaskIndex = i;
                    previousTaskEndTime = taskEndTime;
                  }
                }
                
                // Also track the earliest next task that starts after the break's original end time
                // This helps us adjust the break duration if needed
                const breakEndTime = new Date(breakTask.scheduled_end_time);
                if (taskStartTime && taskStartTime > breakEndTime) {
                  if (earliestNextTaskStartTime === null || taskStartTime < earliestNextTaskStartTime) {
                    earliestNextTaskStartTime = taskStartTime;
                  }
                }
              }
              
              // If we found a task that should come before the break
              if (previousTaskIndex !== -1 && previousTaskEndTime) {
                // Set the break to start right after the previous task
                const newBreakStartTime = new Date(previousTaskEndTime);
                const newBreakEndTime = new Date(newBreakStartTime);
                newBreakEndTime.setMinutes(newBreakEndTime.getMinutes() + breakTask.duration);
                
                // Create updated break task with new times
                const updatedBreakTask = {
                  ...breakTask,
                  scheduled_start_time: newBreakStartTime.toISOString(),
                  scheduled_end_time: newBreakEndTime.toISOString()
                };
                
                // Insert the break after the previous task
                updatedSchedule.splice(previousTaskIndex + 1, 0, updatedBreakTask);
                console.log(`Re-inserted break after task at index ${previousTaskIndex}, with new time ${formatTime(updatedBreakTask.scheduled_start_time)} - ${formatTime(updatedBreakTask.scheduled_end_time)}`);
                
                // Update database with the new break time
                api.put(`/api/tasks/${breakTask.id}`, {
                  scheduled_start_time: updatedBreakTask.scheduled_start_time,
                  scheduled_end_time: updatedBreakTask.scheduled_end_time
                }).catch(err => console.error("Error updating break time in database:", err));
              } else {
                // Fallback: Place break at end of schedule if we can't find a good position
                console.log("Could not find appropriate position for break, adding to end");
                updatedSchedule.push(breakTask);
              }
            }
            
            // Sort the final schedule by start time to ensure correct order
            const sortedSchedule = updatedSchedule.sort((a, b) => {
              if (!a.scheduled_start_time) return 1;
              if (!b.scheduled_start_time) return -1;
              return new Date(a.scheduled_start_time) - new Date(b.scheduled_start_time);
            });
            
            // Update the schedule with restored breaks
            setSchedule(sortedSchedule);
            
            // Clear the preserved breaks from storage
            localStorage.removeItem('preserved_breaks');
            console.log("Restored breaks and cleared preservation data");
          }
        } catch (error) {
          console.error("Error restoring preserved breaks:", error);
        }
      }
    };
    
    restoreBreaksAfterRegeneration();
  }, [schedule.length]); // Re-run when schedule length changes, which happens after regeneration
  
  const fetchSchedule = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const formattedDate = date || format(new Date(), 'yyyy-MM-dd');
      
      // Use a cache-busting parameter to ensure we get fresh data
      const cacheBuster = new Date().getTime();
      
      // Fetch tasks for the specified date
      const response = await api.get(`/api/scheduler/daily/${formattedDate}`, {
        params: { 
          user_id: DEFAULT_USER_ID,
          _cache: cacheBuster  // Add cache-busting parameter
        }
      });
      
      // Sort tasks by scheduled_start_time
      const sortedTasks = response.data.sort((a, b) => {
        if (!a.scheduled_start_time) return 1;
        if (!b.scheduled_start_time) return -1;
        return new Date(a.scheduled_start_time) - new Date(b.scheduled_start_time);
      });
      
      setSchedule(sortedTasks);
      console.log('Schedule refreshed with', sortedTasks.length, 'tasks at', new Date().toLocaleTimeString());
    } catch (err) {
      console.error('Error fetching schedule:', err);
      setError('Failed to load schedule. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleRegenerate = async () => {
    // Before navigating, store any breaks in localStorage so they can be preserved
    const existingBreaks = schedule.filter(task => task.status === 'break');
    if (existingBreaks.length > 0) {
      console.log("Preserving breaks before regenerating schedule:", existingBreaks);
      localStorage.setItem('preserved_breaks', JSON.stringify(existingBreaks));
    }
    
    navigate(`/scheduler/generate?date=${date || format(new Date(), 'yyyy-MM-dd')}`);
  };
  
  const handleBreakClick = (index) => {
    if (index < 0 || index >= schedule.length - 1) return;
    
    const currentTask = schedule[index];
    const nextTask = schedule[index + 1];
    
    // Calculate the time gap between the two tasks
    const currentEndTime = new Date(currentTask.scheduled_end_time);
    const nextStartTime = new Date(nextTask.scheduled_start_time);
    
    const gapMinutes = Math.max(0, (nextStartTime - currentEndTime) / (1000 * 60));
    
    // Set default break duration based on gap (minimum 15 minutes)
    let suggestedDuration = 15;
    if (gapMinutes >= 10) {
      // If there's enough gap, use half of it (capped at 30 minutes)
      suggestedDuration = Math.min(Math.floor(gapMinutes / 2), 30);
    }
    setBreakDuration(suggestedDuration);
    
    // Store information about the gap
    setSelectedGap({
      index,
      previousTaskId: currentTask.id,
      nextTaskId: nextTask.id,
      startTime: currentEndTime,
      maxDuration: gapMinutes,
      endTime: nextStartTime,
      willRequireShift: gapMinutes < suggestedDuration
    });
    
    setBreakDialogOpen(true);
  };
  
  const handleBreakDialogClose = () => {
    setBreakDialogOpen(false);
    setSelectedGap(null);
  };
  
  const handleAddBreak = async () => {
    if (!selectedGap) return;
    
    setIsSubmitting(true);
    const tasksToUpdate = [];
    
    try {
      const startTime = new Date(selectedGap.startTime);
      const endTime = new Date(startTime);
      endTime.setMinutes(endTime.getMinutes() + breakDuration);
      
      // Create the break as a special task
      const breakTask = {
        name: "Break",
        description: "Scheduled break time",
        duration: breakDuration,
        priority: 3,
        status: "break", // Special status for breaks
        user_id: DEFAULT_USER_ID,
        scheduled_start_time: startTime.toISOString(),
        scheduled_end_time: endTime.toISOString()
      };
      
      // Check if we need to shift subsequent tasks
      const needsShift = selectedGap.maxDuration < breakDuration;
      
      if (needsShift) {
        // Calculate how much time we need to shift (in minutes)
        const shiftMinutes = breakDuration - selectedGap.maxDuration;
        
        // Create an array of tasks that need to be updated
        const tasksToShift = schedule.slice(selectedGap.index + 1);
        
        // Prepare each task update
        for (const task of tasksToShift) {
          if (task.scheduled_start_time && task.scheduled_end_time) {
            const taskStartTime = new Date(task.scheduled_start_time);
            const taskEndTime = new Date(task.scheduled_end_time);
            
            // Shift times forward
            taskStartTime.setMinutes(taskStartTime.getMinutes() + shiftMinutes);
            taskEndTime.setMinutes(taskEndTime.getMinutes() + shiftMinutes);
            
            tasksToUpdate.push({
              id: task.id,
              scheduled_start_time: taskStartTime.toISOString(),
              scheduled_end_time: taskEndTime.toISOString()
            });
          }
        }
      }
      
      // First add the break to the database
      const response = await api.post('/api/tasks', breakTask);
      const createdBreak = response.data;
      console.log("Break created:", createdBreak);
      
      // Make a copy of the current schedule for updating
      const updatedSchedule = [...schedule];
      
      // If we need to shift tasks, update their times in our local state
      if (needsShift) {
        for (let i = selectedGap.index + 1; i < updatedSchedule.length; i++) {
          const taskIndex = i - (selectedGap.index + 1);
          if (taskIndex < tasksToUpdate.length) {
            updatedSchedule[i] = {
              ...updatedSchedule[i],
              scheduled_start_time: tasksToUpdate[taskIndex].scheduled_start_time,
              scheduled_end_time: tasksToUpdate[taskIndex].scheduled_end_time
            };
          }
        }
      }
      
      // Create our break object for the UI with the ID from the server response
      // but ensuring we use our properly formatted time strings
      const uiBreakTask = {
        ...createdBreak,
        scheduled_start_time: breakTask.scheduled_start_time,
        scheduled_end_time: breakTask.scheduled_end_time
      };
      
      console.log("UI Break Task with times:", uiBreakTask);
      
      // Important: Insert the break at the correct position - immediately after selectedGap.index
      updatedSchedule.splice(selectedGap.index + 1, 0, uiBreakTask);
      console.log("Break inserted at index:", selectedGap.index + 1);
      
      // Don't sort the schedule as it would change the position of our newly added break
      // Instead, trust the position we've manually set
      setSchedule(updatedSchedule);
      console.log("Schedule state updated with break");
      
      // Close the dialog immediately for better UX
      setBreakDialogOpen(false);
      
      // Then update all tasks that need shifting in the database
      if (tasksToUpdate.length > 0) {
        // Use Promise.all to update all tasks in parallel for better performance
        await Promise.all(tasksToUpdate.map(task => 
          api.put(`/api/tasks/${task.id}`, {
            user_id: DEFAULT_USER_ID,
            scheduled_start_time: task.scheduled_start_time,
            scheduled_end_time: task.scheduled_end_time
          })
        ));
        
        console.log(`Shifted ${tasksToUpdate.length} tasks forward by ${breakDuration - selectedGap.maxDuration} minutes`);
      }
    } catch (error) {
      console.error("Error adding break:", error);
      alert("Failed to add break. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };
  
  const handleMarkAsCompleteClick = (task) => {
    // Set default actual start time to scheduled start time if available
    const defaultStartTime = task.scheduled_start_time ? new Date(task.scheduled_start_time) : new Date();
    
    // Set default actual end time to now
    const defaultEndTime = new Date();
    
    setSelectedTask(task);
    setTaskUpdateForm({
      actual_start_time: defaultStartTime,
      actual_end_time: defaultEndTime,
      status: 'completed'
    });
    setCompleteDialogOpen(true);
  };
  
  const handleCompleteDialogClose = () => {
    setCompleteDialogOpen(false);
    setSelectedTask(null);
  };
  
  const handleTaskUpdateChange = (field, value) => {
    setTaskUpdateForm({
      ...taskUpdateForm,
      [field]: value
    });
  };
  
  const isTaskUpdateValid = () => {
    return taskUpdateForm.actual_start_time !== null && 
           taskUpdateForm.actual_end_time !== null &&
           taskUpdateForm.status !== '';
  };
  
  const handleSnackbarClose = () => {
    setSnackbar({
      ...snackbar,
      open: false
    });
  };
  
  const handleSubmitTaskUpdate = async () => {
    if (!selectedTask) return;
    
    // Validate that end time is after start time
    if (taskUpdateForm.actual_start_time && taskUpdateForm.actual_end_time) {
      if (new Date(taskUpdateForm.actual_end_time) <= new Date(taskUpdateForm.actual_start_time)) {
        alert("End time must be after start time");
        return;
      }
    }
    
    setIsSubmittingTaskUpdate(true);
    
    try {
      // Prepare data for API
      const updateData = {
        ...taskUpdateForm,
        actual_start_time: taskUpdateForm.actual_start_time ? taskUpdateForm.actual_start_time.toISOString() : null,
        actual_end_time: taskUpdateForm.actual_end_time ? taskUpdateForm.actual_end_time.toISOString() : null
      };
      
      // Log for debugging
      console.log(`Updating task ${selectedTask.id} with:`, updateData);
      
      // Update task with PUT request
      const response = await api.put(`/api/tasks/${selectedTask.id}`, updateData);
      
      // Update local state
      const updatedSchedule = schedule.map(task => 
        task.id === selectedTask.id ? { ...task, ...updateData } : task
      );
      setSchedule(updatedSchedule);
      
      // Log success
      console.log(`Task ${selectedTask.id} updated successfully:`, response.data);
      
      // Show success notification
      setSnackbar({
        open: true,
        message: `Task "${selectedTask.name}" has been ${updateData.status}!`,
        severity: 'success'
      });
      
      // Close dialog
      handleCompleteDialogClose();
    } catch (error) {
      console.error("Error updating task:", error);
      
      // Show error notification
      setSnackbar({
        open: true,
        message: 'Failed to update task. Please try again.',
        severity: 'error'
      });
    } finally {
      setIsSubmittingTaskUpdate(false);
    }
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
                const isBreak = task.status === 'break';
                const isCompleted = task.status === 'completed';
                
                return (
                  <Box key={task.id}>
                    <Box sx={{ 
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
                        borderLeft: isBreak ? `4px solid ${getStatusColor('break')}` : `4px solid ${priorityStyle.color}`,
                        backgroundColor: isBreak ? 'rgba(156, 39, 176, 0.08)' : 
                                     (task.status === 'completed' ? 'rgba(76, 175, 80, 0.08)' : 'inherit'),
                        transition: 'all 0.2s ease-in-out',
                      }}>
                        <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                          <Box display="flex" justifyContent="space-between" alignItems="center">
                            <Typography variant="subtitle1" fontWeight="500" sx={{ display: 'flex', alignItems: 'center' }}>
                              {isBreak && <LocalCafeIcon sx={{ mr: 1, color: getStatusColor('break') }} />}
                              {isCompleted && <DoneAllIcon sx={{ mr: 1, color: getStatusColor('completed') }} />}
                              {task.name}
                            </Typography>
                            {!isBreak && (
                              <Chip 
                                size="small" 
                                icon={<PriorityIcon />} 
                                label={`Priority: ${priorityStyle.label}`} 
                                sx={{ bgcolor: `${priorityStyle.color}20`, color: priorityStyle.color }}
                              />
                            )}
                          </Box>
                          <Typography variant="body2" color="text.secondary" mt={1}>
                            {task.description || (isBreak ? "Take a short break" : "No description provided")}
                          </Typography>
                          <Box display="flex" justifyContent="space-between" alignItems="center" mt={1}>
                            <Chip 
                              size="small" 
                              label={`${task.duration} min`} 
                              variant="outlined"
                            />
                            <Box display="flex" gap={1} alignItems="center">
                              {!isBreak && !isCompleted && (
                                <Button
                                  size="small"
                                  variant="outlined"
                                  color="success"
                                  startIcon={<DoneIcon />}
                                  onClick={() => handleMarkAsCompleteClick(task)}
                                >
                                  Mark Complete
                                </Button>
                              )}
                              <Chip 
                                size="small" 
                                label={isBreak ? "Break" : task.status.charAt(0).toUpperCase() + task.status.slice(1)} 
                                sx={{ bgcolor: `${getStatusColor(task.status)}20`, color: getStatusColor(task.status) }}
                              />
                            </Box>
                          </Box>
                        </CardContent>
                      </Card>
                    </Box>
                    
                    {/* Break insertion area */}
                    {index < schedule.length - 1 && (
                      <Box 
                        sx={{ 
                          height: '20px',
                          position: 'relative',
                          zIndex: 5,
                          ml: 5,
                          '&:hover': {
                            '& .break-button': {
                              opacity: 1,
                              transform: 'translateY(0)'
                            }
                          }
                        }}
                        onMouseEnter={() => setHoverIndex(index)}
                        onMouseLeave={() => setHoverIndex(null)}
                      >
                        <Zoom in={hoverIndex === index}>
                          <Button
                            className="break-button"
                            variant="outlined"
                            color="secondary"
                            size="small"
                            startIcon={<CoffeeIcon />}
                            onClick={() => handleBreakClick(index)}
                            sx={{
                              position: 'absolute',
                              top: '-10px',
                              left: '50%',
                              transform: 'translateX(-50%) translateY(5px)',
                              opacity: 0,
                              transition: 'all 0.2s ease-in-out',
                              borderRadius: '20px',
                              boxShadow: '0 2px 4px rgba(0,0,0,0.2)'
                            }}
                          >
                            Add Break
                          </Button>
                        </Zoom>
                      </Box>
                    )}
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
                  <Typography variant="body2" color="text.secondary">Total Items</Typography>
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
                    {schedule.filter(task => task.priority >= 4 && task.status !== 'break').length}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">High Priority Tasks</Typography>
                </Box>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Box textAlign="center" p={2}>
                  <Typography variant="h4">
                    {schedule.filter(task => task.status === 'break').length}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">Break Periods</Typography>
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
      
      {/* Break Dialog */}
      <Dialog open={breakDialogOpen} onClose={handleBreakDialogClose}>
        <DialogTitle sx={{ display: 'flex', alignItems: 'center' }}>
          <CoffeeIcon sx={{ mr: 1 }} /> Add a Break
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Add a short break between tasks to rest and recharge.
          </Typography>
          {selectedGap?.willRequireShift && (
            <Alert severity="info" sx={{ mb: 2 }}>
              Adding this break will shift forward all subsequent tasks by {Math.max(0, breakDuration - selectedGap.maxDuration)} minutes.
            </Alert>
          )}
          <TextField
            label="Duration (minutes)"
            type="number"
            fullWidth
            value={breakDuration}
            onChange={(e) => {
              const newDuration = parseInt(e.target.value) || 5;
              setBreakDuration(Math.max(5, newDuration));
              if (selectedGap) {
                setSelectedGap({
                  ...selectedGap,
                  willRequireShift: selectedGap.maxDuration < newDuration
                });
              }
            }}
            inputProps={{ min: 5 }}
            helperText="Minimum break duration: 5 minutes"
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleBreakDialogClose}>Cancel</Button>
          <Button 
            onClick={handleAddBreak}
            disabled={isSubmitting || !breakDuration || breakDuration < 5}
            variant="contained"
            color="secondary"
            startIcon={isSubmitting ? <CircularProgress size={20} /> : <CoffeeIcon />}
          >
            Add Break
          </Button>
        </DialogActions>
      </Dialog>
      
      {/* Task Complete Dialog */}
      <Dialog open={completeDialogOpen} onClose={handleCompleteDialogClose} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ display: 'flex', alignItems: 'center' }}>
          <DoneIcon sx={{ mr: 1 }} /> Mark Task as Complete
        </DialogTitle>
        <DialogContent>
          {selectedTask && (
            <>
              <Typography variant="h6" gutterBottom>
                {selectedTask.name}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Please specify when you started and finished this task:
              </Typography>
              
              <LocalizationProvider dateAdapter={AdapterDateFns}>
                <Grid container spacing={3}>
                  <Grid item xs={12}>
                    <DateTimePicker
                      label="Actual Start Time"
                      value={taskUpdateForm.actual_start_time}
                      onChange={(newValue) => handleTaskUpdateChange('actual_start_time', newValue)}
                      renderInput={(params) => <TextField {...params} fullWidth variant="outlined" />}
                    />
                  </Grid>
                  <Grid item xs={12}>
                    <DateTimePicker
                      label="Actual End Time"
                      value={taskUpdateForm.actual_end_time}
                      onChange={(newValue) => handleTaskUpdateChange('actual_end_time', newValue)}
                      renderInput={(params) => <TextField {...params} fullWidth variant="outlined" />}
                    />
                  </Grid>
                  <Grid item xs={12}>
                    <FormControl fullWidth>
                      <InputLabel>Status</InputLabel>
                      <Select
                        value={taskUpdateForm.status}
                        label="Status"
                        onChange={(e) => handleTaskUpdateChange('status', e.target.value)}
                      >
                        <MenuItem value="pending">Pending</MenuItem>
                        <MenuItem value="in_progress">In Progress</MenuItem>
                        <MenuItem value="completed">Completed</MenuItem>
                        <MenuItem value="cancelled">Cancelled</MenuItem>
                      </Select>
                    </FormControl>
                  </Grid>
                </Grid>
              </LocalizationProvider>
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCompleteDialogClose}>Cancel</Button>
          <Button 
            onClick={handleSubmitTaskUpdate}
            disabled={isSubmittingTaskUpdate || !isTaskUpdateValid()}
            variant="contained"
            color="success"
            startIcon={isSubmittingTaskUpdate ? <CircularProgress size={20} /> : <DoneAllIcon />}
          >
            Update Task
          </Button>
        </DialogActions>
      </Dialog>
      
      {/* Success/Error Notification */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={handleSnackbarClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <MuiAlert 
          onClose={handleSnackbarClose} 
          severity={snackbar.severity} 
          sx={{ width: '100%' }}
          elevation={6}
          variant="filled"
        >
          {snackbar.message}
        </MuiAlert>
      </Snackbar>
    </Box>
  );
};
export default ScheduleView; 
