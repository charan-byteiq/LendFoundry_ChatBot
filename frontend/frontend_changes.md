# Frontend Development Guide for Unified Chatbot API

## Overview
This document outlines the integration details for the Unified Chatbot API. The backend routes user queries to one of four specialized sub-bots (`lf_assist`, `doc_assist`, `db_assist`, `viz_assist`) or a scope guard. The frontend must handle the unified response format and render appropriate UI elements based on the active backend.

## API Endpoint

**URL:** `POST /chat`
**Content-Type:** `multipart/form-data`

### Request Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `message` | string | Yes | The user's natural language query. |
| `session_id` | string | No | Unique session identifier. If omitted, the backend generates one. Send this back in subsequent requests to maintain context. |
| `file` | File | No | Optional PDF file upload for Document Q&A. |

### Response Format (JSON)
The API returns a unified JSON object. The `backend` field is the key discriminator for UI rendering logic.

```typescript
interface ChatResponse {
  backend: "lf_assist" | "doc_assist" | "db_assist" | "viz_assist" | "scope_guard";
  answer: string;           // The main text response to display
  session_id: string;       // Store this for the next request
  tags?: string[];          // (lf_assist only) Topic tags
  data?: Record<string, any>[]; // (viz_assist) Array of data rows
  sql_query?: string;       // (viz_assist) The generated SQL (for debug/info)
  chart_analysis?: {        // (viz_assist) Chart configuration
    chartable: boolean;
    reasoning?: string;
    auto_chart?: {
      type: "bar" | "line" | "pie" | "scatter";
      title: string;
      x_axis?: string;
      y_axis?: string;
    };
  };
  record_count?: number;    // Number of records found (if data is present)
  error?: string;           // Error message if something went wrong
}
```

## UI Rendering Logic by Backend

### 1. General (All Backends)
- **Chat Bubble:** Always display the `answer` text.
- **Session Management:** Capture `session_id` from the first response and send it in all future requests.
- **Loading State:** Show a loading indicator while waiting for the API.
- **Error Handling:** If `error` field is present, display it prominently (e.g., in a red toast or alert).

### 2. Company Knowledge (`lf_assist`)
- **Context:** Questions about company policies, lending procedures, etc.
- **UI Elements:**
  - Display `answer`.
  - **Tags:** If `tags` array is present and not empty, display them as small "chips" or badges below the answer (e.g., "Policy", "Interest Rates").

### 3. Document Q&A (`doc_assist`)
- **Context:** Questions about an uploaded PDF.
- **UI Elements:**
  - Display `answer`.
  - **File Upload:** Ensure the chat input area has a file upload button. If a file is selected, send it in the `file` field of the FormData.
  - **Indicator:** Show a "Document Mode" indicator when a file is attached.

### 4. Database Query (`db_assist`)
- **Context:** Simple lookups (e.g., "What is the status of loan #123?").
- **UI Elements:**
  - Display `answer`.
  - The response is typically text-based. No special visualization is needed unless you want to parse markdown tables if they appear in the text.

### 5. Visualization & Analytics (`viz_assist`)
- **Context:** Requests for charts, trends, or complex data analysis.
- **UI Elements:**
  - Display `answer` (usually contains a summary).
  - **Data Table:** If `data` is present and `chart_analysis.chartable` is `false`, render the `data` array as a sortable/paginated table.
  - **Charts:** If `chart_analysis.chartable` is `true` and `chart_analysis.auto_chart` is present:
    - Render a chart (using Recharts, Chart.js, or similar).
    - **Type:** Use `auto_chart.type` (bar, line, pie, etc.).
    - **Axes:** Use `auto_chart.x_axis` and `auto_chart.y_axis` to map data keys.
    - **Title:** Use `auto_chart.title`.
  - **SQL Toggle:** If `sql_query` is present, provide a collapsible "Show SQL" section for transparency (optional).

### 6. Scope Guard (`scope_guard`)
- **Context:** Out-of-scope questions or greetings.
- **UI Elements:**
  - Display `answer`.
  - This is a polite deflection. Treat it as a normal text response.

## Example Frontend Logic (Pseudo-code)

```javascript
async function sendMessage(userMessage, file = null) {
  const formData = new FormData();
  formData.append('message', userMessage);
  if (currentSessionId) formData.append('session_id', currentSessionId);
  if (file) formData.append('file', file);

  const response = await fetch('/chat', { method: 'POST', body: formData });
  const data = await response.json();

  // Update Session
  currentSessionId = data.session_id;

  // Render Message
  renderChatBubble(data.answer, 'bot');

  // Handle Specifics
  switch (data.backend) {
    case 'lf_assist':
      if (data.tags) renderTags(data.tags);
      break;
    case 'viz_assist':
      if (data.chart_analysis?.chartable) {
        renderChart(data.chart_analysis.auto_chart, data.data);
      } else if (data.data && data.data.length > 0) {
        renderTable(data.data);
      }
      if (data.sql_query) renderSqlExpander(data.sql_query);
      break;
    // ... handle other cases
  }
}

## Recent UI Implementation Changes

### 1. `src/types/chat.ts`
- Added `BackendType` enum for the 5 backend types.
- Updated `ApiResponse` interface to match new unified format.
- Added `tags`, `session_id`, `backend`, `answer`, and `record_count` fields.
- Added `file` field to `Message` interface.

### 2. `src/services/api.ts`
- Changed from JSON to `multipart/form-data`.
- Added support for `session_id` parameter.
- Added support for file uploads.

### 3. `src/components/ChatInput.tsx`
- Added file upload button (PDF only).
- Added file preview with remove option.
- Updated suggestions to match loan data queries.
- Updated placeholder text when file is attached.

### 4. `src/components/ChatInterface.tsx`
- Changed from `threadId` to `sessionId` (managed from API response).
- Updated `handleSendMessage` to accept optional file parameter.
- Session ID is now captured from first response and reused.
- Updated header title to "Lendfoundry Assistant".
- Updated example queries for loan data.

### 5. `src/components/BotMessage.tsx`
- Added `BackendBadge` component showing which backend handled the request.
- Added `TagsList` component for `lf_assist` tags.
- Now displays answer text for all backends.
- SQL and charts only shown for `viz_assist` backend.
- Color-coded badges per backend type.

### UI Behavior by Backend

| Backend | Display |
| :--- | :--- |
| `lf_assist` | Answer + Tags badges |
| `doc_assist` | Answer only |
| `db_assist` | Answer only |
| `viz_assist` | Answer + SQL (collapsible) + Chart/Table toggle |
| `scope_guard` | Answer only (polite deflection) |
```
