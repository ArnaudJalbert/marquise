import type { CatalogueScreening } from "./catalogue-types";

export function Showtime({ screening }: { screening: CatalogueScreening }) {
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
      {screening.language && <small>{screening.language}</small>}
    </span>
  );
}
