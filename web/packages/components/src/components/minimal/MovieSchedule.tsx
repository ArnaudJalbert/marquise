import { Fragment, useEffect, useState, type CSSProperties } from "react";
import type {
  CatalogueMovie,
  CatalogueCinema,
  CatalogueScreening,
  MinimalCatalogueProps,
} from "./catalogue-types";
import { addDays, formatDate, formatRangeDate } from "./catalogue-format";
import { Showtime } from "./Showtime";

type MovieScheduleProps = Pick<
  MinimalCatalogueProps,
  "cinemas" | "screeningLanguages" | "today" | "onLoadWeek"
> & { movie: CatalogueMovie };

// Narrow enough for four days on desktop, wide enough that cinema names
// wrap by word on a phone. Below this the day row scrolls sideways.
const SCHEDULE_COLUMN_MIN_WIDTH = 150;
const SCHEDULE_COLUMN_GAP = 64;
// shortcut: one bounded load stands in for a dates endpoint; widen or add one if schedules outgrow it.
const SCHEDULE_PAST_DAYS = 30;
const SCHEDULE_FUTURE_DAYS = 90;

function dayGap(previous: string | undefined, date: string): number | null {
  if (!previous) return null;
  const days = (Date.parse(date) - Date.parse(previous)) / 86_400_000;
  return days > 1 ? days : null;
}

export function MovieSchedule({
  movie,
  cinemas,
  screeningLanguages,
  today,
  onLoadWeek,
}: MovieScheduleProps) {
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [visibleDays, setVisibleDays] = useState(4);
  const [scheduleGrouping, setScheduleGrouping] = useState<"date" | "cinema">(
    "date",
  );
  const [weekDirection, setWeekDirection] = useState<
    "next" | "previous" | null
  >(null);
  const [weekData, setWeekData] = useState<{
    screenings: CatalogueScreening[];
    cinemas: CatalogueCinema[];
  } | null>(null);
  const [weekLoading, setWeekLoading] = useState(false);
  const [retryAttempt, setRetryAttempt] = useState(0);
  const [weekError, setWeekError] = useState(false);
  const [scheduleCinemas, setScheduleCinemas] = useState<string[]>([]);
  const [scheduleLanguages, setScheduleLanguages] = useState<string[]>([]);
  const scheduleCinemaOptions = [
    ...new Map(
      [...cinemas, ...(weekData?.cinemas ?? [])].map((item) => [
        item.id,
        item,
      ]),
    ).values(),
  ];
  const loadingSchedule =
    weekLoading || Boolean(onLoadWeek && !weekData && !weekError);
  const matchingScreenings = (
    weekData?.screenings ?? (onLoadWeek ? [] : movie.screenings)
  ).filter(
    (screening) =>
      (!scheduleCinemas.length ||
        scheduleCinemas.includes(screening.cinemaId)) &&
      (!scheduleLanguages.length ||
        (screening.language !== undefined &&
          scheduleLanguages.includes(screening.language))),
  );
  const matchingDates = [
    ...new Set(matchingScreenings.map((screening) => screening.date)),
  ].sort();
  const nextDate =
    matchingDates.find((date) => date >= today) ?? matchingDates.at(-1);
  const hasUpcoming = nextDate !== undefined && nextDate >= today;
  const currentDate =
    selectedDate && matchingDates.includes(selectedDate)
      ? selectedDate
      : nextDate;
  const currentIndex = currentDate ? matchingDates.indexOf(currentDate) : -1;
  const scheduleDates =
    currentIndex < 0
      ? []
      : matchingDates.slice(currentIndex, currentIndex + visibleDays);
  const scheduleScreenings = matchingScreenings.filter((screening) =>
    scheduleDates.includes(screening.date),
  );
  const filtersActive = scheduleCinemas.length + scheduleLanguages.length > 0;
  const clearFilters = () => {
    setScheduleCinemas([]);
    setScheduleLanguages([]);
    setSelectedDate(null);
  };
  useEffect(() => {
    if (!weekDirection) return;
    const timer = window.setTimeout(() => setWeekDirection(null), 240);
    return () => window.clearTimeout(timer);
  }, [weekDirection]);
  useEffect(() => {
    if (!onLoadWeek) return;
    const controller = new AbortController();
    let current = true;
    setWeekData(null);
    setWeekError(false);
    setWeekLoading(true);
    void onLoadWeek(
      movie,
      addDays(today, -SCHEDULE_PAST_DAYS),
      addDays(today, SCHEDULE_FUTURE_DAYS),
      controller.signal,
    )
      .then((data) => {
        if (current) setWeekData(data);
      })
      .catch(() => {
        if (current) setWeekError(true);
      })
      .finally(() => {
        if (current) setWeekLoading(false);
      });
    return () => {
      current = false;
      controller.abort();
    };
  }, [movie, onLoadWeek, today, retryAttempt]);
  const moveWeek = (offset: number) => {
    const date = matchingDates[currentIndex + offset];
    if (!date) return;
    setWeekDirection(offset > 0 ? "next" : "previous");
    setSelectedDate(date);
  };
  const goToNext = () => {
    if (!currentDate || !nextDate) return;
    setWeekDirection(nextDate > currentDate ? "next" : "previous");
    setSelectedDate(null);
  };
  const scheduledCinemas = scheduleCinemaOptions.filter((item) =>
    scheduleScreenings.some((screening) => screening.cinemaId === item.id),
  );
  return (
    <>
      <h2>Upcoming screenings</h2>
      <p>Montréal local time.</p>
      <div className="minimal-week-nav">
        <button
          aria-label="Previous dates"
          onClick={() => moveWeek(-1)}
          disabled={currentIndex <= 0}
        >
          ←
        </button>
        <strong>
          {scheduleDates[0] && (
            <span>{formatRangeDate(scheduleDates[0])}</span>
          )}
          {scheduleDates.length > 1 && (
            <>
              {" "}
              to <span>{formatRangeDate(scheduleDates.at(-1)!)}</span>
            </>
          )}
        </strong>
        <button
          aria-label="Next dates"
          onClick={() => moveWeek(1)}
          disabled={currentIndex < 0 || currentIndex >= matchingDates.length - 1}
        >
          →
        </button>
      </div>
      <div className="minimal-schedule-toolbar">
        <details className="minimal-other-filters minimal-schedule-filters">
          <summary>
            Filters
            {filtersActive ? " •" : ""}
          </summary>
          <div className="minimal-filter-panels">
            <fieldset>
              <legend>Cinemas</legend>
              {scheduleCinemaOptions.map((item) => (
                <label key={item.id}>
                  <input
                    type="checkbox"
                    checked={scheduleCinemas.includes(item.id)}
                    onChange={() => {
                      setSelectedDate(null);
                      setScheduleCinemas((current) =>
                        current.includes(item.id)
                          ? current.filter((id) => id !== item.id)
                          : [...current, item.id],
                      );
                    }}
                  />
                  {item.name}
                </label>
              ))}
            </fieldset>
            <fieldset>
              <legend>Language</legend>
              {screeningLanguages.map((language) => (
                <label key={language}>
                  <input
                    type="checkbox"
                    checked={scheduleLanguages.includes(language)}
                    onChange={() => {
                      setSelectedDate(null);
                      setScheduleLanguages((current) =>
                        current.includes(language)
                          ? current.filter((item) => item !== language)
                          : [...current, language],
                      );
                    }}
                  />
                  {language}
                </label>
              ))}
            </fieldset>
            <div className="minimal-filter-actions">
              <button onClick={clearFilters}>Clear filters</button>
            </div>
          </div>
        </details>
        <div className="minimal-schedule-options">
          <label className="minimal-days-control">
            Group by
            <select
              aria-label="Group schedule by"
              value={scheduleGrouping}
              onChange={(event) =>
                setScheduleGrouping(event.target.value as "date" | "cinema")
              }
            >
              <option value="date">By date</option>
              <option value="cinema">By cinema</option>
            </select>
          </label>
          <button onClick={goToNext} disabled={currentDate === nextDate}>
            Today
          </button>
          <label className="minimal-days-control">
            Days
            <select
              aria-label="Days to show"
              value={visibleDays}
              onChange={(event) => setVisibleDays(Number(event.target.value))}
            >
              {[1, 2, 3, 4].map((days) => (
                <option key={days} value={days}>
                  {days}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>
      {loadingSchedule && <p role="status">Loading showtimes…</p>}
      {weekError && (
        <div role="alert">
          <p>
            Could not load showtimes.
            {movie.screenings.length
              ? " Showing sample data where available."
              : ""}
          </p>
          <button
            onClick={() => {
              setWeekError(false);
              setWeekLoading(true);
              setRetryAttempt((attempt) => attempt + 1);
            }}
          >
            Retry showtimes
          </button>
        </div>
      )}
      {!loadingSchedule && !weekError && !hasUpcoming && (
        <div role="status">
          <p>
            {filtersActive
              ? "No upcoming screenings match these filters."
              : "No upcoming screenings."}
            {scheduleDates.length ? " Showing the latest past date." : ""}
          </p>
          {filtersActive && (
            <button onClick={clearFilters}>Clear filters</button>
          )}
        </div>
      )}
      <div key={`${currentDate}-${visibleDays}-${scheduleGrouping}`}>
        {scheduleGrouping === "date" ? (
          <div
            className={`minimal-schedule-by-date${weekDirection ? ` slide-${weekDirection}` : ""}`}
            style={
              {
                gridTemplateColumns: `repeat(${visibleDays}, minmax(${SCHEDULE_COLUMN_MIN_WIDTH}px, 1fr))`,
                columnGap: `${SCHEDULE_COLUMN_GAP}px`,
                "--date-step": `calc(max(${SCHEDULE_COLUMN_MIN_WIDTH}px, 100% / ${visibleDays}) + ${SCHEDULE_COLUMN_GAP}px)`,
              } as CSSProperties
            }
          >
            {scheduleDates.map((date, index) => {
              const screenings = scheduleScreenings.filter(
                (s) => s.date === date,
              );
              const gap = dayGap(matchingDates[currentIndex + index - 1], date);
              return (
                <section className="minimal-schedule-column" key={date}>
                  <h3>{formatDate(date)}</h3>
                  {gap && (
                    <small
                      className="minimal-schedule-gap"
                      aria-label={`${gap} days between screenings`}
                    >
                      +{gap} days
                    </small>
                  )}
                  {[...new Set(screenings.map((s) => s.cinemaId))].map(
                    (cinemaId) => (
                      <div className="minimal-cinema-showtimes" key={cinemaId}>
                        <h4>
                          {screenings.find((s) => s.cinemaId === cinemaId)
                            ?.cinemaName ??
                            scheduleCinemaOptions.find((c) => c.id === cinemaId)
                              ?.name ??
                            "Cinema"}
                        </h4>
                        {screenings
                          .filter((s) => s.cinemaId === cinemaId)
                          .map((s, i) => (
                            <Showtime key={i} screening={s} />
                          ))}
                      </div>
                    ),
                  )}
                </section>
              );
            })}
          </div>
        ) : (
          <div className="minimal-cinema-table-wrap">
            <table
              className={`minimal-cinema-table${weekDirection ? ` slide-${weekDirection}` : ""}`}
            >
              <thead>
                <tr>
                  <th scope="col">Cinema</th>
                  {scheduleDates.map((date, index) => {
                    const gap = dayGap(matchingDates[currentIndex + index - 1], date);
                    return (
                      <Fragment key={date}>
                        {gap && (
                          <th
                            scope="col"
                            className="minimal-schedule-gap-column"
                            aria-hidden="true"
                          />
                        )}
                        <th scope="col">{formatDate(date)}</th>
                      </Fragment>
                    );
                  })}
                </tr>
              </thead>
              <tbody>
                {scheduledCinemas.map((item, cinemaIndex) => (
                  <tr key={item.id}>
                    <th scope="row">{item.name}</th>
                    {scheduleDates.map((date, index) => {
                      const gap = dayGap(
                        matchingDates[currentIndex + index - 1],
                        date,
                      );
                      return (
                        <Fragment key={date}>
                          {gap && cinemaIndex === 0 ? (
                            <td
                              className="minimal-schedule-gap-column"
                              rowSpan={scheduledCinemas.length}
                            >
                              +{gap} days
                            </td>
                          ) : null}
                          <td>
                            {scheduleScreenings
                              .filter(
                                (s) => s.cinemaId === item.id && s.date === date,
                              )
                              .map((s, i) => (
                                <Showtime key={i} screening={s} />
                              ))}
                          </td>
                        </Fragment>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
