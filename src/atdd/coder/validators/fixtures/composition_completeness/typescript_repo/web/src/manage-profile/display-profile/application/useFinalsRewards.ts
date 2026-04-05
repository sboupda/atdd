import { createFinalsRewardsRepository } from "../integration/FinalsRewardsRepository";

export function useFinalsRewards() {
  return createFinalsRewardsRepository();
}
