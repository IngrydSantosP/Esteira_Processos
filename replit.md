# Overview

This repository contains a complete VaBoo!-inspired recruitment platform built with Python/Flask. The system connects job seekers with employers through an AI-powered matching algorithm and features a modern turquoise gradient design. The application provides separate dashboards for companies (job management) and candidates (job browsing and applications), with an advanced notification system and intelligent compatibility scoring.

## Recent Updates (August 2025)
- **Enhanced Notification System**: Complete overhaul with company names, job titles, type-specific emojis, formatted dates, and priority indicators for new notifications (30-day window)
- **External JavaScript Architecture**: Moved all candidate dashboard JavaScript to static/candidato.js for better performance and maintainability
- **Advanced Favorites System**: Implemented toggle API with visual feedback and persistent storage
- **Improved UX**: Bold titles for unread notifications, color-coded badges (green for new, red for old unread), and animated feedback system

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Backend Architecture

The system uses a dual-backend approach:

**Node.js/Express Backend:**
- JWT-based authentication system using jsonwebtoken and bcrypt
- MongoDB integration via Mongoose ODM for user data storage
- CORS-enabled API with Express middleware
- User model includes experiences and competencies sub-schemas

**Python/Flask Backend:**
- Primary application server handling web routes and business logic
- SQLite database for job postings, candidates, companies, and notifications
- AI-powered candidate matching using local algorithms and optional Hugging Face integration
- Email notification system with HTML templates
- Background scheduler for automated job status management

## Frontend Architecture

**Template Engine:**
- Jinja2 templating with responsive HTML/CSS/JavaScript
- TailwindCSS for styling with custom purple/blue gradient theme
- Mobile-first responsive design
- Accessibility features including ARIA labels and keyboard navigation

**Key UI Components:**
- Separate dashboards for candidates and companies
- Multi-step job creation wizard with progress indicators
- Real-time filtering and search functionality
- Notification bell with badge indicators
- Modal-based interactions for job applications and hiring

## Data Storage Solutions

**SQLite Database Schema:**
- `candidatos`: User profiles with resume text and contact information
- `empresas`: Company profiles with CNPJ and location data
- `vagas`: Job postings with requirements, salary, and location details
- `candidaturas`: Application tracking with compatibility scores
- `notificacoes`: Message system for hiring communications

**File Storage:**
- PDF resume uploads processed via PyPDF2
- Local file system storage for uploaded documents

## Authentication & Authorization

**Dual Authentication System:**
- JWT tokens for Node.js API endpoints with secret key validation
- Flask session-based authentication for web interface
- Role-based access (candidate vs. company) with separate login flows
- Password hashing using bcrypt (Node.js) and Werkzeug (Flask)

## AI Matching System

**Compatibility Algorithm:**
- Factory pattern implementation with local and Hugging Face evaluators
- Multi-criteria scoring: salary compatibility (20%), requirements matching (40%), experience (15%), differentials (10%), location proximity (10%), education (5%)
- Semantic analysis using sentence-transformers for advanced matching
- Geographic distance calculation for location-based scoring

# External Dependencies

## Third-Party Services

**AI/ML Libraries:**
- `sentence-transformers`: Semantic similarity analysis for job matching
- `scikit-learn`: Machine learning utilities for compatibility scoring
- `nltk`: Natural language processing for resume analysis

**Document Processing:**
- `PyPDF2`: PDF resume parsing and text extraction
- `PyMuPDF`: Alternative PDF processing library
- `weasyprint`: HTML to PDF conversion for reports

**Email Services:**
- SMTP integration for notification delivery
- HTML email templates with responsive design
- Environment-based email configuration

**Frontend Libraries:**
- TailwindCSS: Utility-first CSS framework via CDN
- Google Fonts (Poppins): Typography enhancement
- Custom CSS for additional styling and animations

**Development Tools:**
- `nodemon`: Node.js development server with auto-restart
- `schedule`: Python task scheduling for automated processes
- `python-dotenv`: Environment variable management

## Database Dependencies

**SQLite:**
- Primary database for all application data
- No external database server required
- Automatic schema initialization and migration support

## Optional Integrations

**Hugging Face Models:**
- Switchable AI processing mode via environment variables
- Fallback to local algorithms when external models unavailable
- Configurable model endpoints for scalability