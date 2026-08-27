import React from "react";
import {
  Utensils,
  Bus,
  Book,
  ShoppingBag,
  Film,
  Receipt,
  Heart,
  MoreHorizontal,
  Wallet,
  GraduationCap,
} from "lucide-react";

const MAP: Record<string, React.ComponentType<any>> = {
  utensils: Utensils,
  bus: Bus,
  book: Book,
  bag: ShoppingBag,
  film: Film,
  receipt: Receipt,
  heart: Heart,
  dots: MoreHorizontal,
  wallet: Wallet,
  education: GraduationCap,
};

export function CategoryIcon({ icon, size = 16, className = "" }: { icon: string; size?: number; className?: string }) {
  const Icon = MAP[icon] || Wallet;
  return <Icon size={size} className={className} />;
}
