import type { CatalogueScreening } from "./catalogue-types";

export function Showtime({
  screening,
  countdown,
}: {
  screening: CatalogueScreening;
  countdown?: string;
}) {
  return (
    <span className="minimal-time">
      {screening.bookingUrl ? (
        <a
          href={screening.bookingUrl}
          target="_blank"
          rel="noopener noreferrer"
        >
          {screening.time}
        </a>
      ) : (
        <span>{screening.time}</span>
      )}{" "}
      {countdown && <><span className="minimal-countdown">{countdown}</span>{" "}</>}
      {screening.language && <small>{screening.language}</small>}
    </span>
  );
}
