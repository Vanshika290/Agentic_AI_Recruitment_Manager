# Agentic_AI_Recruitment_Manager

Interview Schedular Agent

The Interview Scheduler Backend is a RESTful API service designed to manage and automate interview scheduling between candidates and recruiters.
It handles user data, interview slots, scheduling logic, and notification management efficiently.

This backend can easily integrate with a frontend (like React, Vue, or HTML/JS) to provide a complete interview management system.

🚀 Features

👤 User Management (Candidates & Recruiters)

📅 Interview Creation & Scheduling

🔄 Update or Reschedule Interviews

🗑️ Cancel/Delete Interviews

🔍 Fetch All Scheduled Interviews

⏰ Availability Management

📧 Email Notification Integration (optional)

🧩 Database Integration (SQLite/MySQL/PostgreSQL)


   Structure of folder:

     Agentic_AI/
├── app/
│   ├── __init__.py
│   ├── database.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── models.py
│   └── services/
│       ├── __init__.py
│       └── calendar_service.py
├── scripts/
│   └── seed_data.py
└── main.py

