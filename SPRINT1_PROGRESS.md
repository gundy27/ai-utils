# Portfolio Chatbot Widget - Sprint 1 Progress

## ✅ Phase 1: Backend Enhancements (COMPLETED)

### 1.1 Lead Capture to Metadata Store ✅

- **File**: `libs/metadata-store/src/gundy_ai/metadata_store/models.py`
  - Added `Lead` model with SQLAlchemy schema
  - Fields: id, session_id, name, email, company, role, interest_level, captured_at, metadata
  - Added indexes for session_id, interest_level, and captured_at

- **File**: `libs/metadata-store/src/gundy_ai/metadata_store/store.py`
  - Implemented `create_lead()` - Create new lead
  - Implemented `get_lead()` - Get lead by ID
  - Implemented `get_lead_by_session()` - Get lead by session
  - Implemented `list_leads()` - List leads with filtering
  - Implemented `update_lead()` - Update lead information
  - Implemented `get_lead_stats()` - Get lead statistics

### 1.2 OpenAI Function Calling ✅

- **File**: `services/rag-api/app/tools/base.py`
  - Created `Tool` Pydantic model
  - Created `ToolRegistry` class with register/execute/get_tool_schemas methods

- **File**: `services/rag-api/app/tools/calendly.py`
  - Implemented `schedule_meeting` tool
  - Supports: intro_call, technical_interview, coffee_chat

- **File**: `services/rag-api/app/tools/contact.py`
  - Implemented `get_contact_info` tool
  - Supports: email, linkedin, github

- **File**: `services/rag-api/app/tools/portfolio.py`
  - Implemented `view_portfolio_resource` tool
  - Supports: portfolio, resume, projects, case_studies

### 1.3 Lead Signal Detection ✅

- **File**: `services/rag-api/app/lead_detection.py`
  - Implemented `detect_interest_signal()` function
  - Detects: hiring keywords, technical depth, experience questions, engagement level, availability inquiries, compensation questions
  - Returns: should_capture, interest_level, trigger, score

### 1.4 Enhanced Chat Endpoint ✅

- **File**: `services/rag-api/app/models.py`
  - Added `ToolCall` model
  - Added `LeadCapturePrompt` model
  - Added `LeadCaptureRequest` model
  - Added `LeadCaptureResponse` model
  - Enhanced `ChatResponse` with tool_calls and lead_capture fields

- **File**: `services/rag-api/app/pipeline.py`
  - Initialized `ToolRegistry` in RAGPipeline
  - Enhanced `chat()` method to support OpenAI function calling
  - Integrated lead signal detection
  - Returns tool calls and lead capture prompts

- **File**: `services/rag-api/app/main.py`
  - Updated `/chat` endpoint to handle tool calls and lead capture
  - Added `/leads/capture` endpoint for lead submission
  - Added `/admin/conversations` endpoint for listing conversations
  - Added `/admin/conversations/{session_id}` endpoint for viewing full conversations
  - Added `/admin/leads` endpoint for listing leads with filtering
  - Added `/admin/analytics` endpoint for analytics dashboard

### 1.5 Dependencies ✅

- Updated `services/rag-api/pyproject.toml` to include `openai` package

## 🚧 Phase 2: Widget Core (IN PROGRESS)

### 2.1 Setup Widget Project ✅

- **File**: `applications/portfolio-chatbot-widget/widget/package.json`
  - Created with Preact, Vite, TypeScript dependencies
- **File**: `applications/portfolio-chatbot-widget/widget/tsconfig.json`
  - TypeScript configuration for Preact

- **File**: `applications/portfolio-chatbot-widget/widget/vite.config.ts`
  - Vite configuration for library mode
  - IIFE format for self-contained bundle
  - Minification and optimization settings

### 2.2 Widget Infrastructure ✅

- **File**: `applications/portfolio-chatbot-widget/widget/src/types/index.ts`
  - Complete type definitions

- **File**: `applications/portfolio-chatbot-widget/widget/src/api/client.ts`
  - ChatbotAPIClient with sendMessage() and captureLead()

- **File**: `applications/portfolio-chatbot-widget/widget/src/utils/storage.ts`
  - Session storage utilities with 24-hour expiration

- **File**: `applications/portfolio-chatbot-widget/widget/src/utils/analytics.ts`
  - Analytics event tracking

### 2.3 Widget Components (TODO)

- ChatBubble component (floating button)
- ChatWindow component (main UI)
- MessageList component
- MessageInput component
- ActionButton component (for tool calls)
- LeadForm component
- Main ChatWidget orchestrator
- CSS styles

### 2.4 Widget Initialization (TODO)

- index.tsx entry point
- Global window mount function
- Configuration handling

## ⏳ Phase 3: Admin Dashboard (NOT STARTED)

Backend admin endpoints are complete. Frontend dashboard needs to be built.

### 3.1 Setup Admin Project

- Next.js with TypeScript
- Auth integration with auth-secrets-service
- Tailwind CSS

### 3.2 Admin Views

- Conversations view with filtering
- Leads management interface
- Analytics dashboard with charts

## ⏳ Phase 4: Integration & Testing (NOT STARTED)

### 4.1 CORS Configuration

- Update CORS settings for widget domains

### 4.2 Rate Limiting

- Per-IP rate limiting for public widget

### 4.3 Testing

- Unit tests for tools and lead detection
- Integration tests for widget → API flow
- E2E tests with Playwright
- Manual testing on test portfolio page

### 4.4 Widget Loader

- Minimal loader script for easy embedding
- CDN setup documentation

## 📊 Summary

**Completed**:

- ✅ Phase 1: Backend Enhancements (100%)
- ✅ Phase 2.1: Widget project setup
- ✅ Phase 2.2: Widget infrastructure

**In Progress**:

- 🚧 Phase 2.3: Widget Preact components

**Remaining**:

- ⏳ Phase 2.4: Widget initialization
- ⏳ Phase 3: Admin Dashboard (full frontend)
- ⏳ Phase 4: Integration & Testing

**Estimated Completion**:

- Phase 2: ~2-3 hours (widget components + loader)
- Phase 3: ~3-4 hours (admin dashboard)
- Phase 4: ~1-2 hours (testing & deployment docs)

**Total Sprint Progress**: ~40% complete
