# Agentic_AI_Recruitment_Manager

Interview Schedular Agent

                ┌──────────────────────┐
                │   User Interface     │
                │ (CLI / Web / Chatbot)│
                └──────────┬───────────┘
                           │
                 ┌─────────▼─────────┐
                 │  Agent Controller │
                 │ (Decision Manager)│
                 └─────────┬─────────┘
                           │
          ┌────────────────┴────────────────┐
          │                                 │
┌─────────▼──────────┐             ┌────────▼─────────┐
│  Llama Reasoning AI│             │ Scheduler Engine │
│  (Natural language │             │ (finds free slot)│
│   & decision logic)│             └────────┬─────────┘
└─────────┬──────────┘                      │
          │                                 │
   ┌──────▼──────┐                 ┌────────▼─────────┐
   │ Data Storage│                 │ Communication Tool│
   │ (JSON/DB)   │                 │ (email / console)│
   └──────────────┘                 └──────────────────┘


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

