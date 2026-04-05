import { LEADERBOARD_KEY } from "../domain/rank";

export function createLeaderboardRepository() {
  return { rank: LEADERBOARD_KEY };
}
