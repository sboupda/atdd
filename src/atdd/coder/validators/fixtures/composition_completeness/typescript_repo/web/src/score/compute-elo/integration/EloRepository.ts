import { ELO_FACTOR } from "../domain/elo";

export function createEloRepository() {
  return { factor: ELO_FACTOR };
}
