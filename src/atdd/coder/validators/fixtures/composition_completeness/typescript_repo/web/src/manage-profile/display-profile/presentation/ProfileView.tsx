import { FinalsRewardCard } from "./FinalsRewardCard";

type Props = {
  rank: string;
  rewardKey: string;
};

export function ProfileView(props: Props) {
  return <FinalsRewardCard label={`${props.rank}:${props.rewardKey}`} />;
}
