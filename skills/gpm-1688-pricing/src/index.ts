import { fetchPriceSamples } from "./tools/fetchPriceSamples";

export const tools = {
  fetch_price_samples: fetchPriceSamples,
};

export type { FetchPriceSamplesInput, FetchPriceSamplesOutput } from "./tools/fetchPriceSamples";
