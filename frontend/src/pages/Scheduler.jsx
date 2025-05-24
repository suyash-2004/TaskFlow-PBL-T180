import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { 
  Box, Typography, Paper, TextField, Button, 
  Grid, CircularProgress, Alert, FormControl,
  InputLabel, MenuItem, Select, Stack, Tooltip, IconButton
} from '@mui/material';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { format, parse } from 'date-fns';
import api from '../services/api';

// Default user ID for all tasks since we removed authentication
const DEFAULT_USER_ID = "default_user";

// Time options for dropdown
const TIME_OPTIONS = [
  "08:00", "08:30", "09:00", "09:30", "10:00", "10:30", "11:00", "11:30", 
  "12:00", "12:30", "13:00", "13:30", "14:00", "14:30", "15:00", "15:30",
  "16:00", "16:30", "17:00", "17:30", "18:00", "18:30", "19:00", "19:30",
  "20:00", "20:30", "21:00"
];

// Algorithm options
const ALGORITHM_OPTIONS = [
  { 
    value: "round_robin", 
    label: "Round Robin", 
    description: "Priority-based Round Robin (considers both priority and deadlines)" 
  },
  { 
    value: "fcfs", 
    label: "First Come First Served", 
    description: "Schedules tasks in the order they were created" 
  },
  { 
    value: "sjf", 
    label: "Shortest Job First", 
    description: "Schedules shortest duration tasks first" 
  },
  { 
    value: "ljf", 
    label: "Longest Job First", 
    description: "Schedules longest duration tasks first" 
  },
  { 
    value: "priority", 
    label: "Priority Only", 
    description: "Schedules based solely on task priority" 
  }
];

const SchedulerPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const queryParams = new URLSearchParams(location.search);
  const dateParam = queryParams.get('date');
  
  const [date, setDate] = useState(dateParam ? parse(dateParam, 'yyyy-MM-dd', new Date()) : new Date());
  const [startTime, setStartTime] = useState("09:00");
  const [endTime, setEndTime] = useState("17:00");
  const [algorithm, setAlgorithm] = useState("round_robin");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  
  const handleGenerateSchedule = async () => {
    // Reset states
    setIsLoading(true);
    setError(null);
    setSuccess(null);
    
    try {
      const formattedDate = format(date, 'yyyy-MM-dd');
      
      // Request body
      const requestData = {
        date: formattedDate,
        start_time: startTime,
        end_time: endTime,
        user_id: DEFAULT_USER_ID,
        algorithm: algorithm
      };
      
      // Call API to generate schedule
      const response = await api.post('/api/scheduler/generate', requestData);
      
      // Set success message
      setSuccess(`Successfully scheduled ${response.data.length} tasks using ${getAlgorithmLabel(algorithm)}!`);
      
      // Clear any cached data for this date by calling the reset endpoint
      try {
        await api.post(`/api/scheduler/reset/${formattedDate}`, {
          user_id: DEFAULT_USER_ID
        });
        console.log('Cleared previous schedule data for', formattedDate);
      } catch (resetErr) {
        console.error('Error clearing previous schedule:', resetErr);
        // Continue even if this fails
      }
      
      // Add a small delay to ensure database operations complete
      setTimeout(() => {
        // Add a timestamp to force cache refresh when redirecting
        const timestamp = new Date().getTime();
        navigate(`/schedule/view/${formattedDate}?refresh=${timestamp}`);
      }, 1500);
      
    } catch (err) {
      console.error('Error generating schedule:', err);
      setError(err.response?.data?.detail || 'Failed to generate schedule. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };
  
  // Helper function to get algorithm label from value
  const getAlgorithmLabel = (value) => {
    const algorithm = ALGORITHM_OPTIONS.find(option => option.value === value);
    return algorithm ? algorithm.label : value;
  };
  
  return (
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      <Box>
        <Typography variant="h4" mb={3}>Generate Schedule</Typography>
         
        <Paper elevation={3} sx={{ p: 3, maxWidth: 600, mx: 'auto' }}>
          <Typography variant="h6" mb={3}>
            Schedule unplanned tasks for a specific date
          </Typography>
          
          {error && (
            <Alert severity="error" sx={{ mb: 3 }}>
              {error}
            </Alert>
          )}
          
          {success && (
            <Alert severity="success" sx={{ mb: 3 }}>
              {success}
            </Alert>
          )}
          
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <DatePicker
                label="Date"
                value={date}
                onChange={(newDate) => setDate(newDate)}
                renderInput={(params) => <TextField {...params} fullWidth />}
              />
            </Grid>
            
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel id="start-time-label">Start Time</InputLabel>
                <Select
                  labelId="start-time-label"
                  value={startTime}
                  label="Start Time"
                  onChange={(e) => setStartTime(e.target.value)}
                >
                  {TIME_OPTIONS.map((time) => (
                    <MenuItem key={time} value={time}>{time}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel id="end-time-label">End Time</InputLabel>
                <Select
                  labelId="end-time-label"
                  value={endTime}
                  label="End Time"
                  onChange={(e) => setEndTime(e.target.value)}
                >
                  {TIME_OPTIONS.map((time) => (
                    <MenuItem key={time} value={time}>{time}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel id="algorithm-label">Scheduling Algorithm</InputLabel>
                <Select
                  labelId="algorithm-label"
                  value={algorithm}
                  label="Scheduling Algorithm"
                  onChange={(e) => setAlgorithm(e.target.value)}
                >
                  {ALGORITHM_OPTIONS.map((option) => (
                    <MenuItem key={option.value} value={option.value}>
                      {option.label}
                    </MenuItem>
                  ))}
                </Select>
                <Box mt={1} display="flex" alignItems="center">
                  <Typography variant="caption" color="text.secondary">
                    {ALGORITHM_OPTIONS.find(option => option.value === algorithm)?.description}
                  </Typography>
                  <Tooltip title="Different algorithms prioritize tasks differently. Choose the one that best fits your needs.">
                    <IconButton size="small">
                      <HelpOutlineIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </Box>
              </FormControl>
            </Grid>
            
            <Grid item xs={12}>
              <Stack direction="row" spacing={2} justifyContent="flex-end">
                <Button 
                  variant="outlined" 
                  onClick={() => navigate('/')}
                >
                  Cancel
                </Button>
                <Button 
                  variant="contained" 
                  onClick={handleGenerateSchedule}
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <CircularProgress size={24} color="inherit" />
                  ) : (
                    'Generate Schedule'
                  )}
                </Button>
              </Stack>
            </Grid>
          </Grid>
        </Paper>
      </Box>
    </LocalizationProvider>
  );
};

export default SchedulerPage; 