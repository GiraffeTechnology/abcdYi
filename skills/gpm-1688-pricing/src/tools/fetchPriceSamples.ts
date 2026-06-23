export interface FetchPriceSamplesInput {
  keyword: string;
  target_quantity?: number;
  target_unit?: string;
  max_samples?: number;
  source_platform?: string;
}

export interface InvalidReasonCounts {
  missing_supplier_id?: number;
  missing_moq?: number;
  missing_observed_time?: number;
  missing_price?: number;
  [reason: string]: number | undefined;
}

export interface FetchPriceSamplesOutput {
  raw_response_id: string;
  sample_count: number;
  valid_sample_count: number;
  invalid_sample_count: number;
  invalid_reasons: InvalidReasonCounts;
  sample_ids: string[];
}

/**
 * Session A skeleton — TypeScript-to-Python backend wiring is deferred to a future integration PR.
 * This skill does not scrape websites, place orders, make payments, or call external LLM APIs.
 */
export async function fetchPriceSamples(
  _input: FetchPriceSamplesInput
): Promise<FetchPriceSamplesOutput> {
  throw new Error(
    "fetch_price_samples: GPM backend not yet connected. " +
    "Backend wiring is deferred to a future integration PR."
  );
}
