import { useState, useEffect } from 'react';
import { 
  Box, Typography, Paper, Button, TextField, Dialog, DialogTitle, 
  DialogContent, DialogActions, List, ListItem, ListItemText, 
  ListItemSecondaryAction, IconButton, Chip, MenuItem, FormControl,
  InputLabel, Select, Divider, CircularProgress, Grid
} from '@mui/material';
import { Add as AddIcon, Edit as EditIcon, Delete as DeleteIcon } from '@mui/icons-material';
import { DateTimePicker } from '@mui/x-date-pickers';
import { LocalizationProvider } from '@mui/x-date-pickers';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { format } from 'date-fns';
import api from '../services/api';

// Default user ID for all tasks since we removed authentication
const DEFAULT_USER_ID = "default_user";

const Tasks = () => {
  const [tasks, setTasks] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  // Form state
  const [taskForm, setTaskForm] = useState({
    name: '',
    description: '',
    duration: 30,
    priority: 3,
    deadline: null,
    dependencies: [],
    user_id: DEFAULT_USER_ID
  });
  
  const priorityLabels = {
    1: 'Lowest',
    2: 'Low',
    3: 'Medium',
    4: 'High',
    5: 'Highest'
  };
  
  useEffect(() => {
    fetchTasks();
  }, []);
  
  const fetchTasks = async () => {
    setIsLoading(true);
    setError(null);
    try {
      // Add user_id filter to only get tasks for our default user
      const response = await api.get('/api/tasks', { params: { user_id: DEFAULT_USER_ID } });
      setTasks(response.data);
    } catch (err) {
      console.error('Error fetching tasks:', err);
      setError('Failed to load tasks. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleDialogOpen = () => {
    setDialogOpen(true);
  };
  
  const handleDialogClose = () => {
    setTaskForm({
      name: '',
      description: '',
      duration: 30,
      priority: 3,
      deadline: null,
      dependencies: [],
      user_id: DEFAULT_USER_ID
    });
    setDialogOpen(false);
  };
  
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setTaskForm({
      ...taskForm,
      [name]: value
    });
  };
  
  const handleDeadlineChange = (newValue) => {
    setTaskForm({
      ...taskForm,
      deadline: newValue
    });
  };
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    
    try {
      await api.post('/api/tasks', {
        ...taskForm,
        user_id: DEFAULT_USER_ID, // Ensure we always use the default user ID
        deadline: taskForm.deadline ? taskForm.deadline.toISOString() : null
      });
      
      fetchTasks();
      handleDialogClose();
    } catch (err) {
      console.error('Error creating task:', err);
      setError('Failed to create task. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };
  
  const getPriorityColor = (priority) => {
    switch (priority) {
      case 5: return 'error';
      case 4: return 'warning';
      case 3: return 'success';
      case 2: return 'primary';
      default: return 'default';
    }
  };
  
  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height="70vh">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Tasks</Typography>
        <Button 
          variant="contained" 
          startIcon={<AddIcon />}
          onClick={handleDialogOpen}
        >
          Add Task
        </Button>
      </Box>
      
      {error && (
        <Typography color="error" mb={2}>{error}</Typography>
      )}
      
      <Paper elevation={3} sx={{ p: 3 }}>
        {tasks.length > 0 ? (
          <List>
            {tasks.map((task) => (
              <Box key={task.id}>
                <ListItem 
                  secondaryAction={
                    <Box>
                      <Chip 
                        label={`Priority: ${priorityLabels[task.priority]}`}
                        color={getPriorityColor(task.priority)}
                        size="small"
                        sx={{ mr: 1 }}
                      />
                      <IconButton edge="end" aria-label="edit">
                        <EditIcon />
                      </IconButton>
                    </Box>
                  }
                >
                  <ListItemText 
                    primary={task.name} 
                    secondary={
                      <Box component="span">
                        <Typography variant="body2" component="span">
                          {task.description || 'No description'}
                        </Typography>
                        <br />
                        <Typography variant="caption" component="span">
                          Duration: {task.duration} min | Status: {task.status}
                          {task.deadline && ` | Deadline: ${format(new Date(task.deadline), 'MMM d, yyyy h:mm a')}`}
                        </Typography>
                      </Box>
                    } 
                  />
                </ListItem>
                <Divider component="li" />
              </Box>
            ))}
          </List>
        ) : (
          <Typography align="center" py={4}>
            No tasks found. Click "Add Task" to create one.
          </Typography>
        )}
      </Paper>
      
      {/* Task Form Dialog */}
      <Dialog open={dialogOpen} onClose={handleDialogClose} maxWidth="sm" fullWidth>
        <DialogTitle>Add New Task</DialogTitle>
        <DialogContent>
          <Box component="form" onSubmit={handleSubmit} mt={1}>
            <TextField
              margin="dense"
              label="Task Name"
              name="name"
              fullWidth
              value={taskForm.name}
              onChange={handleInputChange}
              required
            />
            
            <TextField
              margin="dense"
              label="Description"
              name="description"
              fullWidth
              value={taskForm.description}
              onChange={handleInputChange}
              multiline
              rows={3}
            />
            
            <Grid container spacing={2} mt={1}>
              <Grid item xs={6}>
                <TextField
                  label="Duration (minutes)"
                  name="duration"
                  type="number"
                  fullWidth
                  value={taskForm.duration}
                  onChange={handleInputChange}
                  required
                  InputProps={{ inputProps: { min: 1 } }}
                />
              </Grid>
              <Grid item xs={6}>
                <FormControl fullWidth>
                  <InputLabel id="priority-label">Priority</InputLabel>
                  <Select
                    labelId="priority-label"
                    name="priority"
                    value={taskForm.priority}
                    onChange={handleInputChange}
                    label="Priority"
                  >
                    <MenuItem value={1}>1 - Lowest</MenuItem>
                    <MenuItem value={2}>2 - Low</MenuItem>
                    <MenuItem value={3}>3 - Medium</MenuItem>
                    <MenuItem value={4}>4 - High</MenuItem>
                    <MenuItem value={5}>5 - Highest</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
            </Grid>
            
            <Box mt={2}>
              <LocalizationProvider dateAdapter={AdapterDateFns}>
                <DateTimePicker
                  label="Deadline (Optional)"
                  value={taskForm.deadline}
                  onChange={handleDeadlineChange}
                  renderInput={(params) => <TextField {...params} fullWidth />}
                />
              </LocalizationProvider>
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleDialogClose}>Cancel</Button>
          <Button 
            onClick={handleSubmit}
            variant="contained" 
            disabled={isSubmitting || !taskForm.name || !taskForm.duration}
          >
            {isSubmitting ? <CircularProgress size={24} /> : 'Create Task'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Tasks; 