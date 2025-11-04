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

