# Frontend (React + Vite + Tailwind)

This frontend provides the chat experience for the SQL assistant. It sends natural-language questions to the backend, displays generated SQL, renders results as tables, and shows recommended charts.

## Stack

- React 18 + TypeScript
- Vite
- Tailwind CSS / shadcn-ui components
- Recharts and Chart.js wrappers for visualizations
- Axios for API calls

## Getting Started

```bash
cd frontend
npm install
npm run dev
# or
bun install
bun dev
```

The app expects the backend running at `http://localhost:8000` (see `src/services/api.ts`).

## Key Files

- `src/App.tsx` – App shell
- `src/components/ChatInterface.tsx` – Main chat container
- `src/components/ChatInput.tsx` – Input and suggestions
- `src/components/BotMessage.tsx` – Renders SQL, charts, and tables
- `src/components/DataChart.tsx` – Chart rendering
- `src/components/DataTable.tsx` – Tabular view

## Build

```bash
npm run build
npm run preview
```

## Notes

- Environment-specific settings (API base URL) are hardcoded in `src/services/api.ts`; adjust if you deploy the backend elsewhere.
- UI/UX is intentionally unchanged; updates here remove prior third-party branding without altering layout or components.
