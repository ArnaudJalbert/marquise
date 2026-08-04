import { cn } from "../../lib/utils";
import { formatTime, isPassed } from "./format";
import type { CinemaShowtime, CinemaShowtimeGroup } from "./cinema";

export function groupByCinema(
  showtimes: readonly CinemaShowtime[],
): CinemaShowtimeGroup[] {
  const groups: CinemaShowtimeGroup[] = [];
  const byId = new Map<string, CinemaShowtimeGroup>();
  for (const showtime of showtimes) {
    let group = byId.get(showtime.cinema.id);
    if (group === undefined) {
      group = { cinema: showtime.cinema, showtimes: [] };
      byId.set(showtime.cinema.id, group);
      groups.push(group);
    }
    group.showtimes.push(showtime);
  }
  return groups;
}

export const showtimeLinkClasses =
  "-mx-0.5 cursor-pointer px-0.5 hover:bg-foreground hover:text-background hover:underline underline-offset-4 focus-visible:bg-foreground focus-visible:text-background focus-visible:outline-none";

/** All showtimes grouped by cinema, shared by the hover popover and inline widget. */
export function CinemaShowtimeGroups({
  groups,
  currentTime,
}: {
  groups: readonly CinemaShowtimeGroup[];
  currentTime?: string;
}) {
  return (
    <ul className="flex flex-col gap-3">
      {groups.map((group) => (
        <li
          key={group.cinema.id}
          className="flex flex-col gap-1.5 border-t border-border pt-2 first:border-t-0 first:pt-0"
        >
          <a
            href={group.cinema.link}
            target="_blank"
            rel="noreferrer"
            className="text-xs font-medium hover:underline underline-offset-4"
          >
            {group.cinema.name}
          </a>
          <div className="flex flex-wrap gap-x-3 gap-y-1">
            {group.showtimes.map((showtime, index) => (
              <a
                key={`${showtime.startsAt}-${index}`}
                href={showtime.ticketUrl}
                target="_blank"
                rel="noreferrer"
                className={cn(
                  "font-mono text-sm tabular-nums",
                  showtimeLinkClasses,
                  isPassed(showtime.startsAt, currentTime) &&
                    "text-muted-foreground line-through",
                )}
              >
                {formatTime(showtime.startsAt)}
              </a>
            ))}
          </div>
        </li>
      ))}
    </ul>
  );
}
