export type BackendType = 'lf_assist' | 'doc_assist' | 'db_assist' | 'viz_assist' | 'scope_guard';

export interface ChartAnalysis {
  chartable: boolean;
  reasoning?: string;
  auto_chart?: {
    type: 'bar' | 'line' | 'pie' | 'scatter' | 'doughnut';
    title: string;
    x_axis?: string;
    y_axis?: string;
  };
}

export interface ApiResponse {
  backend: BackendType;
  answer: string;
  session_id: string;
  tags?: string[];
  data?: Record<string, unknown>[];
  sql_query?: string;
  chart_analysis?: ChartAnalysis;
  record_count?: number;
  error?: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  response?: ApiResponse;
  isLoading?: boolean;
  file?: File;
}
