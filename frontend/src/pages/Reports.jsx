import { useState, useEffect } from 'react';
import { 
  Box, Typography, Paper, Button, CircularProgress, Card, 
  CardContent, CardActions, Grid, List, ListItem, ListItemText,
  Divider, Chip, LinearProgress
} from '@mui/material';
import { 
  PictureAsPdf as PdfIcon,
  CalendarToday as CalendarIcon
} from '@mui/icons-material';
import { format } from 'date-fns';
import api from '../services/api';

// Default user ID for all tasks since we removed authentication
const DEFAULT_USER_ID = "default_user";

const Reports = () => {
  const [reports, setReports] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    fetchReports();
  }, []);
  
  const fetchReports = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await api.get('/api/reports', {
        params: { user_id: DEFAULT_USER_ID }
      });
      setReports(response.data);
    } catch (err) {
      console.error('Error fetching reports:', err);
      setError('Failed to load reports. Please try again later.');
    } finally {
      setIsLoading(false);
    }
  };
  
  const generateDailyReport = async (date) => {
    try {
      const formattedDate = format(date || new Date(), 'yyyy-MM-dd');
      setIsLoading(true);
      setError(null);

      try {
        // Try the simple endpoint first 
        const response = await api.post(`/api/reports/simple/${formattedDate}`, { 
          user_id: DEFAULT_USER_ID 
        });
        
        console.log('Report generated successfully:', response.data);
        fetchReports();
      } catch (simpleErr) {
        console.error('Error with simple report generation:', simpleErr);

        // Try the original endpoint as fallback
        try {
          const response = await api.post(`/api/reports/generate/${formattedDate}`, { 
            user_id: DEFAULT_USER_ID 
          });
          console.log('Report generated with original endpoint:', response.data);
          fetchReports();
        } catch (err) {
          console.error('Error generating report with both methods:', err);
          setError('Failed to generate report. Please try again later.');
        }
      }
    } catch (err) {
      console.error('Error generating report:', err);
      setError('Failed to generate report. Please try again later.');
    } finally {
      setIsLoading(false);
    }
  };
  
  const downloadReportPdf = async (reportId) => {
    try {
      window.open(`/api/reports/${reportId}/pdf`, '_blank');
    } catch (err) {
      console.error('Error downloading report:', err);
      setError('Failed to download report. Please try again later.');
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
        <Typography variant="h4">Productivity Reports</Typography>
        <Button 
          variant="contained" 
          startIcon={<CalendarIcon />}
          onClick={() => generateDailyReport(new Date())}
        >
          Generate Today's Report
        </Button>
      </Box>
      
      {error && (
        <Typography color="error" mb={2}>{error}</Typography>
      )}
      
      {reports.length > 0 ? (
        <Grid container spacing={3}>
          {reports.map((report) => (
            <Grid item xs={12} key={report.id}>
              <Paper elevation={3}>
                <Card>
                  <CardContent>
                    <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                      <Typography variant="h5" component="div">
                        Report for {format(new Date(report.date), 'MMMM d, yyyy')}
                      </Typography>
                      <Chip 
                        label={`Score: ${report.metrics.productivity_score}%`}
                        color={report.metrics.productivity_score > 75 ? 'success' : 
                               report.metrics.productivity_score > 50 ? 'warning' : 'error'}
                      />
                    </Box>
                    
                    <Grid container spacing={2} mb={2}>
                      <Grid item xs={12} md={6}>
                        <Box mb={2}>
                          <Typography variant="subtitle1">Metrics</Typography>
                          <Divider sx={{ mb: 1 }} />
                          <Typography variant="body2" gutterBottom>
                            Completion Rate: {report.metrics.completion_rate}%
                          </Typography>
                          <LinearProgress 
                            variant="determinate" 
                            value={report.metrics.completion_rate} 
                            color="primary"
                            sx={{ mb: 1, height: 8, borderRadius: 1 }}
                          />
                          
                          <Typography variant="body2" gutterBottom>
                            On-Time Rate: {report.metrics.on_time_rate}%
                          </Typography>
                          <LinearProgress 
                            variant="determinate" 
                            value={report.metrics.on_time_rate} 
                            color="secondary"
                            sx={{ mb: 1, height: 8, borderRadius: 1 }}
                          />
                          
                          <Typography variant="body2" gutterBottom>
                            Time Efficiency: {(report.metrics.time_efficiency * 100).toFixed(1)}%
                          </Typography>
                          <LinearProgress 
                            variant="determinate" 
                            value={report.metrics.time_efficiency * 100} 
                            color="success"
                            sx={{ height: 8, borderRadius: 1 }}
                          />
                        </Box>
                      </Grid>
                      
                      <Grid item xs={12} md={6}>
                        <Typography variant="subtitle1">Summary</Typography>
                        <Divider sx={{ mb: 1 }} />
                        <Typography variant="body2" sx={{ fontStyle: 'italic' }}>
                          {report.ai_summary || 'No summary available.'}
                        </Typography>
                      </Grid>
                    </Grid>
                    
                    <Typography variant="subtitle1">Tasks</Typography>
                    <Divider sx={{ mb: 1 }} />
                    <List dense>
                      {report.tasks.map((task) => (
                        <ListItem key={task.task_id}>
                          <ListItemText
                            primary={task.name}
                            secondary={`Status: ${task.status} | Priority: ${task.priority} | Duration: ${task.scheduled_duration} min`}
                          />
                        </ListItem>
                      ))}
                    </List>
                  </CardContent>
                  <CardActions>
                    <Button
                      startIcon={<PdfIcon />}
                      onClick={() => downloadReportPdf(report.id)}
                    >
                      Download PDF
                    </Button>
                  </CardActions>
                </Card>
              </Paper>
            </Grid>
          ))}
        </Grid>
      ) : (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="h6" gutterBottom color="text.secondary">
            No reports available
          </Typography>
          <Typography variant="body2" color="text.secondary" mb={2}>
            Generate your first productivity report to see insights about your task completion.
          </Typography>
          <Button
            variant="outlined"
            onClick={() => generateDailyReport(new Date())}
            startIcon={<CalendarIcon />}
          >
            Generate Today's Report
          </Button>
        </Paper>
      )}
    </Box>
  );
};

export default Reports; 