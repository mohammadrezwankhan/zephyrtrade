import type { BrowserEngine, OfferingInput, OfferingResult, Statistics } from './engine.js';

/** Schema produced by the checked, bundled research snapshot builder. */
export interface ZephyrModel {
  id: string;
  name: string;
  family: string;
  offers: number[];
  forecasts?: number[];
}

export interface ZephyrSnapshot {
  schema_version: number;
  app_version: string;
  data_kind: string;
  farm_id: string;
  farm_name: string;
  capacity_mw: number;
  market_area: string;
  currency: string;
  timezone: string;
  interval_hours: number;
  source_generated_at: string;
  timestamps: [string, ...string[]];
  actual: number[];
  day_ahead: number[];
  up: number[];
  down: number[];
  models: [ZephyrModel, ...ZephyrModel[]];
  farms: {
    farm_id: string;
    display_name: string;
    latitude: number;
    longitude: number;
    capacity_mw: number;
    site_type: string;
  }[];
  quality: {
    rows: number;
    expected_hours_between_endpoints: number;
    excluded_hours_between_endpoints: number;
    source_negative_price_rows_removed: number;
    revenue_values_checked: number;
    maximum_revenue_error_dkk: number;
  };
  sources: { path: string; sha256: string }[];
}

export interface LabInput extends OfferingInput {
  hours: number;
  probabilities: number[];
}

export interface ViewState {
  page: string;
  model: string;
  period: string;
  from: string;
  to: string;
}

declare global {
  interface Window {
    ZEPHYR_DATA: ZephyrSnapshot;
    ZephyrEngine: BrowserEngine;
    ZephyrApp?: {
      getState: () => ViewState;
      getLab: () => { input: unknown; result: OfferingResult | null };
      getVisibleMetrics: () => Statistics;
    };
  }
}
