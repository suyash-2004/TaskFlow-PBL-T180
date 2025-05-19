# TaskFlow Backend

This is the backend API for TaskFlow, a smart calendar-based task scheduler with productivity reports.

## Tech Stack

- **Framework**: FastAPI
- **Database**: MongoDB (with Motor for async operations)
- **Authentication**: JWT
- **AI Integration**: g4f library for GPT models

## Setup Instructions

### Prerequisites

- Python 3.8+
- MongoDB

### Installation

1. Clone the repository
2. Create a virtual environment:
   ```
   python -m venv venv
   ```
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`
4. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
5. Configure environment variables in `.env` file

### Running the Application

```
python main.py
```

The API will be available at `http://localhost:8000`.

### API Documentation

Once the server is running, you can access:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Project Structure

```
backend/
├── app/
│   ├── database/     # Database connection and models
│   ├── models/       # Pydantic models for MongoDB
│   ├── routes/       # API endpoints
│   ├── schemas/      # Request/response schemas
│   ├── services/     # Business logic
│   └── utils/        # Helper functions
├── main.py           # Application entry point
├── requirements.txt  # Dependencies
└── .env              # Environment variables
```
