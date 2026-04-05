import { useFinalsRewards } from "../application/useFinalsRewards";
import { ProfileView } from "./ProfileView";
import { usePlayerRank } from "@reveal-status/display-leaderboard";

export function ProfilePage() {
  const rewards = useFinalsRewards();
  const rank = usePlayerRank();
  return <ProfileView rank={rank.rank} rewardKey={rewards.key} />;
}
