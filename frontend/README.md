# LendFoundry Chatbot Frontend

Modern React-based chat interface for the LendFoundry Unified Chatbot API.

## Tech Stack

- **React 18** + **TypeScript**
- **Vite** - Fast build tool
- **Tailwind CSS** + **shadcn/ui** - Styling & components
- **Recharts** + **Chart.js** - Data visualization
- **Axios** - HTTP client

## Getting Started

### Prerequisites

- Node.js 18+ or Bun
- Backend API running at `http://localhost:8000`

### Installation

```bash
cd frontend

# Using npm
npm install

# Using bun (faster)
bun install
```

### Development

```bash
npm run dev
# or
bun dev
```

Open http://localhost:5174

### Production Build

```bash
npm run build
npm run preview
```

## Configuration

API base URL is configured in `src/services/api.ts`:

```typescript
const API_BASE_URL = 'http://localhost:8000';
```

## Project Structure

```
src/
├── App.tsx                     # App shell
├── main.tsx                    # Entry point
├── index.css                   # Global styles
│
├── components/
│   ├── ChatInterface.tsx       # Main chat container
│   ├── ChatInput.tsx           # Message input + file upload
│   ├── ChatMessage.tsx         # User message component
│   ├── BotMessage.tsx          # Bot response with backend badge
│   ├── DataChart.tsx           # Chart rendering (viz_assist)
│   ├── DataTable.tsx           # Table rendering (viz_assist)
│   ├── CodeBlock.tsx           # SQL display
│   ├── TypingIndicator.tsx     # Loading animation
│   └── ui/                     # shadcn/ui components
│
├── services/
│   └── api.ts                  # API client (multipart/form-data)
│
├── types/
│   └── chat.ts                 # TypeScript interfaces
│
├── hooks/                      # Custom React hooks
└── lib/
    └── utils.ts                # Utility functions
```

## API Integration

The frontend communicates with the Unified API using `multipart/form-data`:

```typescript
// src/services/api.ts
export async function sendMessage(
  message: string, 
  sessionId?: string, 
  file?: File
): Promise<ApiResponse>
```

### Response Handling by Backend

| Backend | UI Elements |
|---------|-------------|
| `lf_assist` | Answer text + Topic tags as badges |
| `doc_assist` | Answer text only |
| `db_assist` | Answer text only |
| `viz_assist` | Answer + SQL (collapsible) + Chart/Table |
| `scope_guard` | Polite deflection message |

## Key Components

### ChatInterface.tsx
- Manages session state (captured from API response)
- Renders message history
- Handles file uploads

### BotMessage.tsx
- Color-coded backend badge
- Conditional rendering based on `backend` field
- Tags list for `lf_assist`
- Chart/Table toggle for `viz_assist`
- Collapsible SQL display

### ChatInput.tsx
- Text input with suggestions
- PDF file upload button
- File preview with remove option

### DataChart.tsx
- Uses `chart_analysis.auto_chart` config
- Supports bar, line, pie, scatter, area charts
- Uses Recharts library

## TypeScript Types

```typescript
// src/types/chat.ts
type BackendType = 
  | 'lf_assist' 
  | 'doc_assist' 
  | 'db_assist' 
  | 'viz_assist' 
  | 'scope_guard';

interface ApiResponse {
  backend: BackendType;
  answer: string;
  session_id: string;
  tags?: string[];
  data?: Record<string, any>[];
  sql_query?: string;
  chart_analysis?: {
    chartable: boolean;
    auto_chart?: {
      type: string;
      title: string;
      x_axis?: string;
      y_axis?: string;
    };
  };
  record_count?: number;
  error?: string;
}
```

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server |
| `npm run build` | Build for production |
| `npm run preview` | Preview production build |
| `npm run lint` | Run ESLint |

## Dependencies

### Runtime
- `react`, `react-dom` - UI framework
- `react-router-dom` - Routing
- `axios` - HTTP client
- `recharts` - Charts
- `chart.js`, `react-chartjs-2` - Alternative charts
- `react-syntax-highlighter` - Code highlighting
- `lucide-react` - Icons
- `@radix-ui/*` - UI primitives
- `tailwind-merge`, `clsx` - Class utilities
- `zod` - Schema validation
- `uuid` - ID generation

### Development
- `vite` - Build tool
- `typescript` - Type checking
- `tailwindcss` - Styling
- `eslint` - Linting
- `autoprefixer`, `postcss` - CSS processing

## Notes

- Session ID is automatically managed from API responses
- File uploads limited to PDF only
- Charts render only when `chart_analysis.chartable` is true
- Backend badge colors: lf=green, doc=blue, db=orange, viz=purple, scope=gray

