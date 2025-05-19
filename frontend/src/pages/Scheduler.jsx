import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { 
  Box, Typography, Paper, TextField, Button, 
  Grid, CircularProgress, Alert, FormControl,
  InputLabel, MenuItem, Select, Stack
} from '@mui/material';
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

const SchedulerPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const queryParams = new URLSearchParams(location.search);
  const dateParam = queryParams.get('date');
  
  const [date, setDate] = useState(dateParam ? parse(dateParam, 'yyyy-MM-dd', new Date()) : new Date());
  const [startTime, setStartTime] = useState("09:00");
  const [endTime, setEndTime] = useState("17:00");
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
        user_id: DEFAULT_USER_ID
      };
      
      // Call API to generate schedule
      const response = await api.post('/api/scheduler/generate', requestData);
      
      // Set success message
      setSuccess(`Successfully scheduled ${response.data.length} tasks!`);
      
      // Redirect to schedule view page after 1 second
      setTimeout(() => {
        navigate(`/schedule/view/${formattedDate}`);
      }, 1000);
      
    } catch (err) {
      console.error('Error generating schedule:', err);
      setError(err.response?.data?.detail || 'Failed to generate schedule. Please try again.');
    } finally {
      setIsLoading(false);
    }
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