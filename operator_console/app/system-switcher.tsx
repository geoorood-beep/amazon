import Link from "next/link";

export default function SystemSwitcher({ replenishmentHref }: { replenishmentHref: string }) {
  return (
    <nav className="system-switcher" aria-label="业务系统切换">
      <Link className="active" href="/">
        <span>AD</span>广告系统
      </Link>
      <a href={replenishmentHref}>
        <span>RP</span>智能补货
      </a>
    </nav>
  );
}
