# LendFoundry Chatbot API Documentation

> **Complete API Reference for Frontend Integration**
> 
> All schemas are now fully documented in Swagger at `/docs`. Frontend engineers can use Swagger UI alone for integration.

---

## Quick Start

1. **Swagger UI**: `http://localhost:8000/docs`
2. **ReDoc**: `http://localhost:8000/redoc`
3. **OpenAPI JSON**: `http://localhost:8000/openapi.json`

---

## Unified Chat Endpoint

### `POST /chat`

**Content-Type:** `multipart/form-data`

#### Request Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | string | ✅ Yes | User's natural language query (1-2000 chars) |
| `session_id` | string | ❌ No | Session ID from previous response. Omit for new conversations. |
| `file` | File (PDF) | ❌ No | PDF file for document Q&A (max 5MB, 20 pages) |

#### Response Schema

```typescript
interface ChatResponse {
  // Core fields (always present)
  backend: "lf_assist" | "doc_assist" | "db_assist" | "viz_assist" | "scope_guard";
  answer: string;           // The main text response - ALWAYS display this
  session_id: string;       // Store and send back in subsequent requests

  // Conditional fields (based on backend)
  tags?: string[];          // (lf_assist only) Topic tags - display as chips
  data?: Record<string, any>[]; // (viz_assist) Data rows - render as table/chart
  sql_query?: string;       // (viz_assist) Generated SQL - show in collapsible
  chart_analysis?: {        // (viz_assist) Chart configuration
    chartable: boolean;
    reasoning?: string;
    auto_chart?: {
      type: "bar" | "line" | "pie" | "scatter" | "area" | "histogram";
      title: string;
      x_axis?: string;
      y_axis?: string;
      reason?: string;
    };
    suggested_charts?: Array<{type: string; title: string}>;
  };
  record_count?: number;    // Number of data records (if data present)
  error?: string;           // Error message - display prominently if present
}
```

#### Error Responses

| Status | Description | Response Body |
|--------|-------------|---------------|
| 400 | Bad Request | `{"detail": "Invalid file type. Please upload a PDF."}` |
| 400 | File Too Large | `{"detail": "File size exceeds the 5MB limit."}` |
| 400 | Too Many Pages | `{"detail": "PDF exceeds the 20-page limit."}` |
| 422 | Validation Error | `{"detail": [{"loc": ["body", "message"], "msg": "field required", "type": "value_error.missing"}]}` |
| 500 | Server Error | `{"detail": "Internal server error"}` |

---

## Backend-Specific UI Behavior

| Backend | What to Display | Special Elements |
|---------|-----------------|------------------|
| `lf_assist` | Answer + Tags | Display `tags` as colored chips/badges |
| `doc_assist` | Answer only | Show file upload indicator |
| `db_assist` | Answer only | Standard text response |
| `viz_assist` | Answer + Chart/Table + SQL | If `chartable=true`: render chart using `auto_chart`<br>If `chartable=false`: render `data` as table<br>Show `sql_query` in collapsible |
| `scope_guard` | Answer only | Polite deflection message |

---

## Sub-Router Endpoints

### LF Assist - Company Knowledge

#### `POST /lf-assist/chat`
```typescript
// Request
interface LFAssistRequest {
  query: string;           // 1-2000 chars
  session_id?: string;     // default: "default"
}

// Response
interface LFAssistResponse {
  query: string;
  tags: string[];
  answer: string;
  session_id: string;
}
```

#### `POST /lf-assist/chat/clear?session_id=xxx`
Clears conversation history for a session.

#### `GET /lf-assist/chat/sessions`
Lists all active sessions.

#### `GET /lf-assist/chat/history/{session_id}`
Gets conversation history for a session.

---

### Doc Assist - Document Q&A

#### `POST /doc-assist/ask`
**Content-Type:** `multipart/form-data`

```typescript
// Request
interface DocAssistRequest {
  question: string;    // Form field
  file: File;          // PDF file
}

// Response
interface DocAssistResponse {
  answer: string;
}
```

**Limitations:**
- PDF only
- Max 5MB
- Max 20 pages

---

### DB Assist - Database Queries

#### `POST /db-assist/chat`
```typescript
// Request
interface DBAssistRequest {
  prompt: string;          // 1-2000 chars
  thread_id?: string;      // Optional session ID
}

// Response
interface DBAssistResponse {
  response: string;
  thread_id: string;
  success: boolean;
}
```

---

### Viz Assist - Visualization

#### `POST /viz-assist/chat`
```typescript
// Request
interface VizAssistRequest {
  question: string;        // 1-2000 chars
  thread_id?: string;      // default: "default"
}

// Response
interface VizAssistResponse {
  sql_query?: string;
  data?: Record<string, any>[];
  chart_analysis?: {
    chartable: boolean;
    reasoning?: string;
    auto_chart?: {
      type: string;
      title: string;
      x_axis?: string;
      y_axis?: string;
      reason?: string;
    };
    suggested_charts?: Array<{type: string; title: string}>;
  };
  error?: string;
  record_count: number;
}
```

---

## Utility Endpoints

### `POST /chat/clear/{session_id}`
Clears conversation history for unified chat session.

```typescript
// Response
interface ClearSessionResponse {
  message: string;
  success: boolean;
}
```

### `GET /health`
```typescript
interface HealthResponse {
  status: {
    lf_assist: "healthy" | "degraded" | "unhealthy";
    doc_assist: "healthy" | "degraded" | "unhealthy";
    db_assist: "healthy" | "degraded" | "unhealthy";
    viz_assist: "healthy" | "initializing" | "degraded" | "unhealthy";
    scope_guard: "healthy" | "degraded" | "unhealthy";
  };
  message: string;
}
```

### `GET /`
Returns API metadata (version, backends, endpoints).

---

## Frontend Implementation Guide

### 1. Session Management

```javascript
let sessionId = null;

async function sendMessage(message, file = null) {
  const formData = new FormData();
  formData.append('message', message);
  if (sessionId) formData.append('session_id', sessionId);
  if (file) formData.append('file', file);

  const response = await fetch('/chat', { method: 'POST', body: formData });
  const data = await response.json();

  // Capture session ID from first response
  sessionId = data.session_id;

  return data;
}
```

### 2. Rendering Logic

```javascript
function renderResponse(data) {
  // Always show answer
  displayMessage(data.answer, 'bot');

  // Handle error
  if (data.error) {
    showError(data.error);
    return;
  }

  // Backend-specific rendering
  switch (data.backend) {
    case 'lf_assist':
      if (data.tags?.length) renderTags(data.tags);
      break;

    case 'viz_assist':
      if (data.chart_analysis?.chartable && data.chart_analysis.auto_chart) {
        renderChart(data.chart_analysis.auto_chart, data.data);
      } else if (data.data?.length) {
        renderTable(data.data);
      }
      if (data.sql_query) renderSqlExpander(data.sql_query);
      break;

    case 'doc_assist':
    case 'db_assist':
    case 'scope_guard':
      // Standard text response - already displayed
      break;
  }
}
```

### 3. Chart Rendering (viz_assist)

```javascript
function renderChart(chartConfig, data) {
  const { type, title, x_axis, y_axis } = chartConfig;
  
  // Using Recharts example
  switch (type) {
    case 'bar':
      return <BarChart data={data}>
        <XAxis dataKey={x_axis} />
        <YAxis />
        <Bar dataKey={y_axis} />
      </BarChart>;
    case 'line':
      return <LineChart data={data}>
        <XAxis dataKey={x_axis} />
        <YAxis />
        <Line dataKey={y_axis} />
      </LineChart>;
    // ... other chart types
  }
}
```

---

## Recent UI Implementation Changes

### Files Modified

1. **`src/types/chat.ts`** - Added BackendType enum, updated ApiResponse interface
2. **`src/services/api.ts`** - Changed to multipart/form-data, added session/file support
3. **`src/components/ChatInput.tsx`** - Added file upload button (PDF only)
4. **`src/components/ChatInterface.tsx`** - Session management from API response
5. **`src/components/BotMessage.tsx`** - BackendBadge, TagsList, conditional rendering

### UI Behavior Summary

| Backend | Display |
|---------|---------|
| `lf_assist` | Answer + Tags badges |
| `doc_assist` | Answer only |
| `db_assist` | Answer only |
| `viz_assist` | Answer + SQL (collapsible) + Chart/Table toggle |
| `scope_guard` | Answer only (polite deflection) |
