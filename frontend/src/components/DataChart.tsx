import { useMemo } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  ChartData,
  ChartOptions,
} from 'chart.js';
import { Bar, Line, Pie, Doughnut } from 'react-chartjs-2';
import { ChartAnalysis } from '@/types/chat';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

interface DataChartProps {
  data: Record<string, unknown>[];
  chartAnalysis: ChartAnalysis;
}

const CHART_COLORS = [
  'hsl(174, 72%, 46%)',   // Primary cyan
  'hsl(262, 72%, 56%)',   // Purple
  'hsl(330, 72%, 56%)',   // Pink
  'hsl(38, 92%, 56%)',    // Orange
  'hsl(142, 72%, 46%)',   // Green
  'hsl(199, 89%, 48%)',   // Blue
  'hsl(0, 72%, 56%)',     // Red
  'hsl(45, 93%, 47%)',    // Yellow
];

const CHART_COLORS_ALPHA = CHART_COLORS.map(color => 
  color.replace(')', ', 0.7)')
);

export function DataChart({ data, chartAnalysis }: DataChartProps) {
  const chartData = useMemo(() => {
    if (!chartAnalysis.auto_chart || data.length === 0) return null;

    const { x_axis, y_axis, type } = chartAnalysis.auto_chart;
    
    // Extract labels from x_axis
    const labels = data.map(row => String(row[x_axis] ?? ''));
    
    // Find numeric columns for datasets
    const numericColumns = Object.keys(data[0]).filter(key => {
      if (key === x_axis) return false;
      return typeof data[0][key] === 'number';
    });

    // If y_axis is specified, prioritize it
    const columnsToPlot = y_axis 
      ? [y_axis, ...numericColumns.filter(col => col !== y_axis)]
      : numericColumns;

    // For pie/doughnut, only use first numeric column
    const isPieType = type === 'pie' || type === 'doughnut';
    const finalColumns = isPieType ? columnsToPlot.slice(0, 1) : columnsToPlot;

    const datasets = finalColumns.map((column, index) => ({
      label: column.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
      data: data.map(row => Number(row[column]) || 0),
      backgroundColor: isPieType ? CHART_COLORS_ALPHA : CHART_COLORS_ALPHA[index % CHART_COLORS_ALPHA.length],
      borderColor: isPieType ? CHART_COLORS : CHART_COLORS[index % CHART_COLORS.length],
      borderWidth: isPieType ? 2 : 2,
      borderRadius: type === 'bar' ? 4 : 0,
      tension: type === 'line' ? 0.4 : 0,
      fill: type === 'line',
      pointBackgroundColor: CHART_COLORS[index % CHART_COLORS.length],
      pointBorderColor: 'hsl(222, 47%, 6%)',
      pointBorderWidth: 2,
      pointRadius: 4,
      pointHoverRadius: 6,
    }));

    return { labels, datasets } as ChartData<typeof type>;
  }, [data, chartAnalysis]);

  const options: ChartOptions<'bar' | 'line' | 'pie' | 'doughnut'> = useMemo(() => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
        labels: {
          color: 'hsl(215, 20%, 65%)',
          font: {
            family: 'Inter, system-ui, sans-serif',
            size: 12,
          },
          padding: 16,
          usePointStyle: true,
          pointStyle: 'circle',
        },
      },
      title: {
        display: true,
        text: chartAnalysis.auto_chart?.title || 'Chart',
        color: 'hsl(210, 40%, 98%)',
        font: {
          family: 'Inter, system-ui, sans-serif',
          size: 16,
          weight: 600,
        },
        padding: { bottom: 16 },
      },
      tooltip: {
        backgroundColor: 'hsl(222, 47%, 12%)',
        titleColor: 'hsl(210, 40%, 98%)',
        bodyColor: 'hsl(215, 20%, 65%)',
        borderColor: 'hsl(222, 47%, 18%)',
        borderWidth: 1,
        padding: 12,
        cornerRadius: 8,
        titleFont: {
          family: 'Inter, system-ui, sans-serif',
          size: 13,
          weight: 600,
        },
        bodyFont: {
          family: 'Inter, system-ui, sans-serif',
          size: 12,
        },
      },
    },
    scales: chartAnalysis.auto_chart?.type !== 'pie' && chartAnalysis.auto_chart?.type !== 'doughnut' ? {
      x: {
        grid: {
          color: 'hsl(222, 47%, 14%)',
          drawBorder: false,
        },
        ticks: {
          color: 'hsl(215, 20%, 55%)',
          font: {
            family: 'Inter, system-ui, sans-serif',
            size: 11,
          },
        },
      },
      y: {
        grid: {
          color: 'hsl(222, 47%, 14%)',
          drawBorder: false,
        },
        ticks: {
          color: 'hsl(215, 20%, 55%)',
          font: {
            family: 'Inter, system-ui, sans-serif',
            size: 11,
          },
        },
        beginAtZero: true,
      },
    } : undefined,
  }), [chartAnalysis]);

  if (!chartData || !chartAnalysis.auto_chart) return null;

  const ChartComponent = {
    bar: Bar,
    line: Line,
    pie: Pie,
    doughnut: Doughnut,
  }[chartAnalysis.auto_chart.type];

  return (
    <div className="w-full h-[350px] p-4">
      <ChartComponent data={chartData as any} options={options as any} />
    </div>
  );
}
