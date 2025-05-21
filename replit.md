# On-Time Delivery Tracker Repository Guide

## Overview

This repository contains a Flask-based web application for tracking and managing on-time delivery performance for shipping and logistics operations. The application provides functionality for managing drivers, loads, tracking vehicles, and generating performance scorecards. It uses Flask for the backend, SQLAlchemy for database operations, and integrates with external APIs like Google Maps and Motive for location tracking.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

The application follows a classic Model-View-Controller (MVC) architecture:

1. **Models**: SQLAlchemy models for database entities (User, Driver, Vehicle, Load, etc.)
2. **Views**: Flask templates with HTML/CSS for the frontend
3. **Controllers**: Flask routes organized into Blueprints for different features

The system uses:
- Flask as the web framework
- SQLAlchemy for ORM and database access
- Flask-Login for user authentication and session management
- RESTful API patterns for data access and manipulation
- External service integrations (Google Maps, Motive API)

## Key Components

### Backend Components

1. **app.py**: Application initialization, database setup, and configuration
2. **main.py**: Entry point for running the application
3. **models.py**: Database models and relationships
4. **services/**: Service modules for external API integration and business logic
   - `geofencing.py`: Geofencing calculations and alerts
   - `google_maps_api.py`: Integration with Google Maps for routing and ETA
   - `motive_api.py`: Integration with Motive API for vehicle tracking
   - `notification_service.py`: Notification management
   - `pdf_extractor.py`: PDF parsing for load information extraction

5. **routes/**: Controller modules organized as Flask Blueprints
   - `auth.py`: User authentication (login/register)
   - `dashboard.py`: Main dashboard views and API endpoints
   - `drivers.py`: Driver management
   - `geofencing.py`: Geofencing management
   - `loads.py`: Load management
   - `notifications.py`: Notification system

### Frontend Components

1. **templates/**: HTML templates for the views
   - `layout.html`: Base template with common structure
   - Various feature-specific templates (dashboard, login, loads, etc.)

2. **static/**: Static assets
   - `js/`: JavaScript modules for client-side functionality
     - `animations.js`: UI animations and gamification
     - `dashboard.js`: Dashboard functionality
     - `maps.js`: Google Maps integration
     - `pdf_upload.py`: PDF upload and processing
     - `tracking.js`: Real-time tracking features
   - `css/`: CSS stylesheets for the UI

## Data Flow

1. **Authentication Flow**:
   - User submits login/register form
   - Backend validates credentials
   - Session is created using Flask-Login
   - User is redirected to the dashboard

2. **Load Management Flow**:
   - Dispatcher creates or uploads load information (via manual form or PDF upload)
   - Load is assigned to a driver
   - System tracks load status (scheduled, in transit, delivered)
   - Geofencing monitors vehicle location relative to pickup/delivery points
   - On-time performance is recorded and used for driver scorecards

3. **Driver Performance Tracking**:
   - System monitors on-time pickup and delivery metrics
   - Scorecards are generated based on performance
   - Gamification elements provide feedback and motivation
   - Leaderboards showcase top performers

4. **Real-time Tracking Flow**:
   - Vehicle positions are retrieved from Motive API
   - Google Maps API calculates ETAs and routing
   - Geofencing detects entry/exit from facility boundaries
   - Alerts are generated for potential delays or issues

## External Dependencies

1. **Database**: 
   - SQL database (PostgreSQL expected based on configuration)
   - Accessed through SQLAlchemy ORM

2. **APIs**:
   - Google Maps API: For routing, geocoding, and ETA calculations
   - Motive API: For vehicle location tracking and driver information

3. **Frontend Libraries**:
   - Bootstrap CSS for responsive UI
   - Feather Icons for iconography
   - Chart.js for performance visualizations

4. **Python Packages**:
   - Flask and extensions (login, sqlalchemy)
   - Requests for API calls
   - PyPDF2 for PDF processing
   - Gunicorn for production deployment

## Deployment Strategy

The application is configured to be deployed as a web service with:

1. **Gunicorn** as the WSGI HTTP server
2. **Environment Variables** for configuration (DATABASE_URL, API keys, etc.)
3. **Replit Deployment** targeting autoscaling infrastructure
4. **PostgreSQL** database connection (connection string via environment variable)
5. **HTTP Port 5000** for the web server

The `.replit` file includes custom deployment settings and workflow configurations to make the application run smoothly in the Replit environment.

## Development Patterns

1. **Model Definitions**: Use SQLAlchemy models with appropriate relationships
2. **API Endpoints**: Use Flask routes with JSON responses for frontend data
3. **Authentication**: Leverage Flask-Login for session management
4. **External Services**: Encapsulate API calls in dedicated service modules
5. **UI Updates**: Use JavaScript fetch API to retrieve data from backend endpoints