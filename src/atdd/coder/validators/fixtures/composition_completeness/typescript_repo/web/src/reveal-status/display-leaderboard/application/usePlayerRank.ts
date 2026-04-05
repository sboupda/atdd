import { createLeaderboardRepository } from "../integration/LeaderboardRepository";

export function usePlayerRank() {
  return createLeaderboardRepository();
}
