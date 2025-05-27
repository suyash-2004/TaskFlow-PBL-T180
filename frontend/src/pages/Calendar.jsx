import { useState, useEffect } from 'react';
import { Calendar as BigCalendar, momentLocalizer } from 'react-big-calendar';
import moment from 'moment';
import 'react-big-calendar/lib/css/react-big-calendar.css';
import { Box, Typography, Paper, CircularProgress } from '@mui/material';
import api from '../services/api';

// Default user ID for all tasks since we removed authentication
const DEFAULT_USER_ID = "default_user";

// Setup the localizer for BigCalendar
const localizer = momentLocalizer(moment);

const Calendar = () => 
{
  const [events, setEvents] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => 
  {
    const fetchCalendarData = async () => 
    {
      setIsLoading(true);
      setError(null);
      
      try 
      {
        // Get current date info
        const now = new Date();
        const year = now.getFullYear();
        const month = now.getMonth() + 1;
        
        // Fetch tasks for current month with default user_id
        const response = await api.get(`/api/calendar/month/${year}/${month}`, {
          params: { user_id: DEFAULT_USER_ID }
        });
        
        // Convert tasks to calendar events
        const calendarEvents = response.data.map(task => ({
          id: task.id,
          title: task.name,
          start: new Date(task.scheduled_start_time || task.deadline),
          end: new Date(task.scheduled_end_time || task.deadline),
          allDay: !task.scheduled_start_time,
          resource: {
            priority: task.priority,
            status: task.status,
            description: task.description
          }
        })).filter(event => event.start && !isNaN(event.start.getTime()));
        
        setEvents(calendarEvents);
      } catch (err) 
      {
        console.error('Error fetching calendar data:', err);
        setError('Failed to load calendar data. Please try again later.');
      } 
      finally 
      {
        setIsLoading(false);
      }
    };
    
    fetchCalendarData();
  }, []);
  
  // Event styling based on priority
  const eventStyleGetter = (event) => {
    const priority = event.resource?.priority || 1;
    let backgroundColor;
    
    switch (priority) {
      case 5:
        backgroundColor = '#f44336'; // Red for highest priority
        break;
      case 4:
        backgroundColor = '#ff9800'; // Orange for high priority
        break;
      case 3:
        backgroundColor = '#4caf50'; // Green for medium priority
        break;
      case 2:
        backgroundColor = '#2196f3'; // Blue for low priority
        break;
      default:
        backgroundColor = '#9e9e9e'; // Gray for lowest priority
    }
    
    // Apply different style for completed tasks
    if (event.resource?.status === 'completed') 
    {
      return {
        style: {
          backgroundColor,
          opacity: 0.7,
          textDecoration: 'line-through',
          border: 'none'
        }
      };
    }
    
    return 
    {
      style: {
        backgroundColor,
        border: 'none'
      }
    };
  };

  if (isLoading) 
  {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height="70vh">
        <CircularProgress />
      </Box>
    );
  }
  
  if (error) 
  {
    return (
      <Box mt={4} p={2}>
        <Typography color="error" variant="h6">{error}</Typography>
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" mb={3}>Calendar</Typography>
      <Paper elevation={3} sx={{ p: 2, height: '75vh' }}>
        <BigCalendar
          localizer={localizer}
          events={events}
          startAccessor="start"
          endAccessor="end"
          eventPropGetter={eventStyleGetter}
          views={['month', 'week', 'day']}
          defaultView="week"
          defaultDate={new Date()}
          tooltipAccessor={(event) => event.resource?.description || event.title}
        />
      </Paper>
    </Box>
  );
};

export default Calendar; 
//Updated
