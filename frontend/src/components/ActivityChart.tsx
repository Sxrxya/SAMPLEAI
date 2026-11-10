import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type ActivityPoint = { week: string; applicants: number; interviews: number };

export default function ActivityChart({ data }: { data: ActivityPoint[] }) {
  return (
    <div className="chart-wrap">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={data}
          margin={{ top: 10, right: 6, left: -20, bottom: 0 }}
        >
          <defs>
            <linearGradient id="applicantFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#2c765f" stopOpacity={0.17} />
              <stop offset="100%" stopColor="#2c765f" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid
            vertical={false}
            stroke="#e9ede8"
            strokeDasharray="3 4"
          />
          <XAxis
            dataKey="week"
            axisLine={false}
            tickLine={false}
            tick={{ fill: "#8b928b", fontSize: 11 }}
            dy={10}
          />
          <YAxis
            axisLine={false}
            tickLine={false}
            tick={{ fill: "#8b928b", fontSize: 11 }}
          />
          <Tooltip
            contentStyle={{
              borderRadius: 8,
              border: "1px solid #e6eae4",
              boxShadow: "0 8px 24px #17231b12",
              fontSize: 12,
            }}
          />
          <Area
            type="monotone"
            dataKey="applicants"
            stroke="#2c765f"
            strokeWidth={2.5}
            fill="url(#applicantFill)"
          />
          <Area
            type="monotone"
            dataKey="interviews"
            stroke="#ed9678"
            strokeWidth={2}
            fill="transparent"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
