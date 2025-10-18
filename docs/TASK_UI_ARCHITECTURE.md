# Task UI Architecture

## Component Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                         Item Detail View                         │
│  ┌────────────┬────────────┐                                    │
│  │  Similar   │   Tasks    │◄─── Tab Navigation                 │
│  │   Items    │   (Active) │                                    │
│  └────────────┴────────────┘                                    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Task List (tasks/list.html)                 │   │
│  │  ┌────────────────────────────────────────────────────┐ │   │
│  │  │ Title │ Status │ GitHub │ Assigned │ Created │ ... │ │   │
│  │  ├────────────────────────────────────────────────────┤ │   │
│  │  │ Task 1 │   🔵   │  #123  │  user1   │ 2025-... │ 👁 │ │   │
│  │  │ Task 2 │   🟢   │   -    │  user2   │ 2025-... │ 👁 │ │   │
│  │  └────────────────────────────────────────────────────┘ │   │
│  │  [+ New Task]                                            │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                    Click Task Title
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Task Detail View (tasks/detail.html)          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Title:        [____________________________________]      │   │
│  │ Description:  ┌──────────────────────────────────┐      │   │
│  │               │ Toast UI Markdown Editor          │      │   │
│  │               │ - Live Preview                    │      │   │
│  │               │ - Syntax Highlighting             │      │   │
│  │               └──────────────────────────────────┘      │   │
│  │ Status:       [🔵 Working ▼]   GitHub: [#123]           │   │
│  │ Tags:         [tag1][tag2][tag3]                         │   │
│  │                                                           │   │
│  │ [💾 Save] [🗑️ Delete] [✨ AI Enhancer] [🧠 Create Issue] │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │           Similar Tasks (max 5)                          │   │
│  │  ┌──────────────────────────────────────────────────┐   │   │
│  │  │ 📝 Similar Task 1        Similarity: 95% │ 🔵    │   │   │
│  │  │ 📝 Similar Task 2        Similarity: 87% │ 🟢    │   │   │
│  │  └──────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Task Creation Flow
```
User                 Frontend              Backend              Services
  │                     │                     │                     │
  │ Fill Form           │                     │                     │
  ├────────────────────►│                     │                     │
  │ Click "Save"        │                     │                     │
  ├────────────────────►│ POST /tasks/create/ │                     │
  │                     ├────────────────────►│                     │
  │                     │                     │ Validate            │
  │                     │                     │ Create Task         │
  │                     │                     │ Save Tags           │
  │                     │                     │                     │
  │                     │      Redirect       │                     │
  │                     │◄────────────────────┤                     │
  │ Show Task Detail    │                     │                     │
  │◄────────────────────┤                     │                     │
```

### AI Enhancement Flow
```
User                 Frontend              Backend              KiGate
  │                     │                     │                     │
  │ Click "AI Enhance"  │                     │                     │
  ├────────────────────►│                     │                     │
  │                     │ Show Spinner        │                     │
  │                     │ POST /api/../ai-enhance                   │
  │                     ├────────────────────►│                     │
  │                     │                     │ POST /agent/execute │
  │                     │                     ├────────────────────►│
  │                     │                     │                     │ text-optimization
  │                     │                     │                     │ keyword-extraction
  │                     │                     │                     │
  │                     │                     │  Enhanced Content   │
  │                     │                     │◄────────────────────┤
  │                     │  JSON Response      │                     │
  │                     │◄────────────────────┤                     │
  │                     │ Update Form         │                     │
  │ Review Changes      │ Hide Spinner        │                     │
  │◄────────────────────┤                     │                     │
```

### GitHub Issue Creation Flow
```
User              Frontend           Backend          GitHub API
  │                  │                  │                  │
  │ Status = Ready   │                  │                  │
  ├─────────────────►│                  │                  │
  │ Click "Create    │                  │                  │
  │  GitHub Issue"   │                  │                  │
  ├─────────────────►│                  │                  │
  │                  │ Show Spinner     │                  │
  │                  │ POST /api/../    │                  │
  │                  │  create-github-  │                  │
  │                  │  issue           │                  │
  │                  ├─────────────────►│                  │
  │                  │                  │ Validate Status  │
  │                  │                  │ Get Repo Info    │
  │                  │                  │ POST /repos/.../ │
  │                  │                  │      issues      │
  │                  │                  ├─────────────────►│
  │                  │                  │                  │ Create
  │                  │                  │  Issue Number    │ Issue
  │                  │                  │  Issue URL       │
  │                  │                  │◄─────────────────┤
  │                  │                  │ Save to Task     │
  │                  │  Success         │                  │
  │                  │◄─────────────────┤                  │
  │ Show Success     │ Hide Spinner     │                  │
  │ Reload Page      │                  │                  │
  │◄─────────────────┤                  │                  │
```

## URL Structure

```
Items
├── /items/                          (List)
├── /items/{id}/                     (Detail with tabs)
│   ├── Tab: Similar Items
│   └── Tab: Tasks
│       └── /items/{id}/tasks/       (Task List)
└── Tasks
    ├── /items/{id}/tasks/create/    (Create)
    ├── /tasks/{id}/                 (Detail)
    ├── /tasks/{id}/edit/            (Edit)
    └── /tasks/{id}/delete/          (Delete)

API Endpoints
├── /api/tasks/{item_id}                      (GET/POST)
├── /api/tasks/{task_id}/detail               (GET/PUT/DELETE)
├── /api/tasks/{task_id}/ai-enhance           (POST)
├── /api/tasks/{task_id}/create-github-issue  (POST)
└── /api/tasks/{task_id}/similar              (GET)
```

## Status Workflow

```
     ⚪                🔵              🟡            🟢           ✅
    New    ────►    Working  ────►  Review  ────► Ready  ────► Done
     │                │                │             │
     └────────────────┴────────────────┴─────────────┘
                  (Can move back)
                  
Rules:
- GitHub Issue creation: Only from Ready status
- Task can be moved to Done from any status
- Status changes are tracked with updated_at timestamp
```

## Security Model

```
┌─────────────────────────────────────────────────────────────┐
│                      Request Flow                            │
└─────────────────────────────────────────────────────────────┘

User Request
     │
     ├──► Session Auth (Views)
     │         │
     │         ├──► Check user_id in session
     │         └──► Redirect to login if not authenticated
     │
     └──► JWT Auth (API)
               │
               ├──► Validate Bearer token
               └──► Return 401 if invalid

Authenticated
     │
     ├──► Authorization Check
     │         │
     │         ├──► Is owner? (task.created_by == user)
     │         ├──► Is admin? (user.role == 'admin')
     │         └──► Return 403 if not authorized
     │
     └──► Execute Action
               │
               ├──► Validate input
               ├──► Apply business rules
               └──► Return response
```

## Database Schema

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│     User     │         │     Item     │         │     Task     │
├──────────────┤         ├──────────────┤         ├──────────────┤
│ id (UUID)    │◄───┐    │ id (UUID)    │◄───┐    │ id (UUID)    │
│ username     │    │    │ title        │    │    │ title        │
│ email        │    │    │ description  │    │    │ description  │
│ role         │    │    │ github_repo  │    │    │ status       │
│ is_active    │    │    │ status       │    │    │ item_id (FK) │────┐
└──────────────┘    │    │ section_id   │    │    │ assigned_to  │────┘
                    │    │ created_by   │────┘    │ created_by   │────┐
                    │    └──────────────┘         │ github_issue │    │
                    │                             │ github_url   │    │
                    └─────────────────────────────┴──────────────┘    │
                                                                       │
┌──────────────┐                                                      │
│     Tag      │                                                      │
├──────────────┤                                                      │
│ id (UUID)    │◄─────────────────────────────────────────────────────
│ name         │         Many-to-Many Relationships:
│ color        │         - Item ↔ Tag
└──────────────┘         - Task ↔ Tag
```

## File Structure

```
IdeaGraph-v1/
├── main/
│   ├── views.py                    (5 task views)
│   ├── api_views.py                (5 task API endpoints)
│   ├── urls.py                     (URL patterns)
│   ├── models.py                   (Task model)
│   ├── test_tasks.py               (13 tests)
│   └── templates/
│       └── main/
│           ├── items/
│           │   └── detail.html     (Tasks tab integration)
│           └── tasks/
│               ├── list.html       (Task list view)
│               ├── detail.html     (Task detail + AI)
│               ├── form.html       (Create/Edit form)
│               └── delete.html     (Delete confirmation)
├── docs/
│   ├── TASK_UI_IMPLEMENTATION.md   (Complete documentation)
│   ├── TASK_UI_SUMMARY.md          (Summary)
│   └── TASK_UI_ARCHITECTURE.md     (This file)
└── requirements.txt                (Dependencies)
```
