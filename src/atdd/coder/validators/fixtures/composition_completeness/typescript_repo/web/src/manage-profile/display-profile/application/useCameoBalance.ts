import { createCameoRepository } from "../integration/CameoRepository";

export function useCameoBalance() {
  return createCameoRepository();
}
