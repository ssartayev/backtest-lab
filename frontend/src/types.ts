export interface Performance {
  total_return: number;
  annual_return: number;
  sharpe: number;
  max_drawdown: number;
  trades: number;
  days: number;
}

export interface CurvePoint {
  day: string;
  strategy: number;
  benchmark: number;
}

export interface BacktestResult {
  symbol: string;
  parameters: { fast: number; slow: number };
  in_sample: Performance;
  out_of_sample: Performance;
  buy_and_hold: Performance;
  equity_curve: CurvePoint[];
}
