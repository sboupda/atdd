import { createForecastGateway } from "../integration/ForecastGateway";

export type ForecastState = {
  source: string;
};

export function useForecast(): ForecastState {
  return createForecastGateway();
}
