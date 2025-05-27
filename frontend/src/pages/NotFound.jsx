import { Box, Typography, Button } from '@mui/material';
import { Link } from 'react-router-dom';

const NotFound = () => {
  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        textAlign: 'center',
        px: 2,
      }}
    >
      <Typography variant="h1" component="h1" sx={{ fontSize: '8rem', fontWeight: 'bold', color: 'primary.main' }}>
        404
      </Typography>
      <Typography variant="h4" component="h2" sx={{ mb: 2 }}>
        Page Not Found
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4, maxWidth: '600px' }}>
        The page you are looking for might have been removed, had its name changed, or is temporarily unavailable.
      </Typography>
      <Button component={Link} to="/" variant="contained" size="large">
        Back to Dashboard
      </Button>
    </Box>
  );
};
export default NotFound; 
