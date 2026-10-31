import { useEffect, useState, type CSSProperties } from "react";
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

export function MovieSchedule({
  movie,
  cinemas,
  screeningLanguages,
  today,
  onLoadWeek,
}: MovieScheduleProps) {
  const [weekStart, setWeekStart] = useState(today);
  const [visibleDays, setVisibleDays] = useState(4);
  const [scheduleGrouping, setScheduleGrouping] = useState<"date" | "cinema">(
    "date",
  );
  const [weekDirection, setWeekDirection] = useState<
    "next" | "previous" | null
  >(null);
  const [weekData, setWeekData] = useState<{
    start: string;
    end: string;
    screenings: CatalogueScreening[];
    cinemas: CatalogueCinema[];
  } | null>(null);
  const [weekLoading, setWeekLoading] = useState(false);
  const [rangeRequested, setRangeRequested] = useState(true);
  const [retryAttempt, setRetryAttempt] = useState(0);
  const [weekError, setWeekError] = useState(false);
  const [scheduleCinemas, setScheduleCinemas] = useState<string[]>([]);
  const [scheduleLanguages, setScheduleLanguages] = useState<string[]>([]);
  const scheduleCinemaOptions = [
    ...new Map(
      [
        ...cinemas,
        ...(weekData?.start === weekStart &&
        weekData.end === addDays(weekStart, visibleDays - 1)
          ? weekData.cinemas
          : []),
      ].map((item) => [item.id, item]),
    ).values(),
  ];
  const scheduleDates = Array.from({ length: visibleDays }, (_, index) =>
    addDays(weekStart, index),
  );
  const currentWeekData =
    weekData?.start === weekStart &&
    weekData.end === addDays(weekStart, visibleDays - 1)
      ? weekData
      : undefined;
  const loadingSchedule =
    weekLoading ||
    Boolean(onLoadWeek && rangeRequested && !currentWeekData && !weekError);
  const scheduleScreenings = (
    currentWeekData?.screenings ??
    (onLoadWeek && rangeRequested ? [] : movie.screenings)
  ).filter(
    (screening) =>
      scheduleDates.includes(screening.date) &&
      (!scheduleCinemas.length ||
        scheduleCinemas.includes(screening.cinemaId)) &&
      (!scheduleLanguages.length ||
        (screening.language !== undefined &&
          scheduleLanguages.includes(screening.language))),
  );
  useEffect(() => {
    if (!weekDirection) return;
    const timer = window.setTimeout(() => setWeekDirection(null), 240);
    return () => window.clearTimeout(timer);
  }, [weekDirection]);
  useEffect(() => {
    if (!onLoadWeek || (!rangeRequested && movie.screenings.length > 0)) return;
    const controller = new AbortController();
    let current = true;
    setWeekData(null);
    setWeekError(false);
    setWeekLoading(true);
    void onLoadWeek(
      movie,
      weekStart,
      addDays(weekStart, visibleDays - 1),
      controller.signal,
    )
      .then((data) => {
        if (current)
          setWeekData({
            start: weekStart,
            end: addDays(weekStart, visibleDays - 1),
            ...data,
          });
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
  }, [movie, onLoadWeek, rangeRequested, weekStart, visibleDays, retryAttempt]);
  const moveWeek = (offset: number) => {
    const start = addDays(weekStart, offset);
    setWeekDirection(offset > 0 ? "next" : "previous");
    setWeekStart(start);
    setWeekData(null);
    setWeekError(false);
    setRangeRequested(true);
  };
  const goToToday = () => {
    setWeekDirection(today > weekStart ? "next" : "previous");
    setWeekStart(today);
    setWeekData(null);
    setWeekError(false);
    setRangeRequested(true);
  };
  return (
    <>
      <h2>Upcoming screenings</h2>
      <p>Montréal local time.</p>
      <div className="minimal-week-nav">
        <button
          aria-label="Previous dates"
          onClick={() => moveWeek(-1)}
        >
          ←
        </button>
        <strong>
          <span>{formatRangeDate(weekStart)}</span>
          {visibleDays > 1 && (
            <>
              {" "}
              to{" "}
              <span>
                {formatRangeDate(addDays(weekStart, visibleDays - 1))}
              </span>
            </>
          )}
        </strong>
        <button
          aria-label="Next dates"
          onClick={() => moveWeek(1)}
        >
          →
        </button>
      </div>
      <div className="minimal-schedule-toolbar">
        <details className="minimal-other-filters minimal-schedule-filters">
          <summary>
            Filters
            {scheduleCinemas.length + scheduleLanguages.length ? " •" : ""}
          </summary>
          <div className="minimal-filter-panels">
            <fieldset>
              <legend>Cinemas</legend>
              {scheduleCinemaOptions.map((item) => (
                <label key={item.id}>
                  <input
                    type="checkbox"
                    checked={scheduleCinemas.includes(item.id)}
                    onChange={() =>
                      setScheduleCinemas((current) =>
                        current.includes(item.id)
                          ? current.filter((id) => id !== item.id)
                          : [...current, item.id],
                      )
                    }
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
                    onChange={() =>
                      setScheduleLanguages((current) =>
                        current.includes(language)
                          ? current.filter((item) => item !== language)
                          : [...current, language],
                      )
                    }
                  />
                  {language}
                </label>
              ))}
            </fieldset>
            <div className="minimal-filter-actions">
              <button
                onClick={() => {
                  setScheduleCinemas([]);
                  setScheduleLanguages([]);
                }}
              >
                Clear filters
              </button>
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
          <button
            onClick={goToToday}
            disabled={weekStart === today}
          >
            Today
          </button>
          <label className="minimal-days-control">
            Days
            <select
              aria-label="Days to show"
              value={visibleDays}
              onChange={(event) => {
                const days = Number(event.target.value);
                setVisibleDays(days);
                setWeekData(null);
                setWeekError(false);
                setRangeRequested(true);
              }}
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
      {!loadingSchedule && !weekError && !scheduleScreenings.length && (
        <p role="status">
          No screenings in these dates. Try another date or clear the filters.
        </p>
      )}
      <div key={`${weekStart}-${visibleDays}-${scheduleGrouping}`}>
        {scheduleGrouping === "date" ? (
          <div
            className={`minimal-schedule-by-date${weekDirection ? ` slide-${weekDirection}` : ""}`}
            style={
              {
                gridTemplateColumns: `repeat(${visibleDays}, minmax(0, 1fr))`,
                "--date-step": `calc(100% / ${visibleDays})`,
              } as CSSProperties
            }
          >
            {scheduleDates.map((date) => {
              const screenings = scheduleScreenings.filter(
                (s) => s.date === date,
              );
              return (
                <section className="minimal-schedule-column" key={date}>
                  <h3>{formatDate(date)}</h3>
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
                  {scheduleDates.map((date) => (
                    <th scope="col" key={date}>
                      {formatDate(date)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {scheduleCinemaOptions
                  .filter((item) =>
                    scheduleScreenings.some((s) => s.cinemaId === item.id),
                  )
                  .map((item) => (
                    <tr key={item.id}>
                      <th scope="row">{item.name}</th>
                      {scheduleDates.map((date) => (
                        <td key={date}>
                          {scheduleScreenings
                            .filter(
                              (s) => s.cinemaId === item.id && s.date === date,
                            )
                            .map((s, i) => (
                              <Showtime key={i} screening={s} />
                            ))}
                        </td>
                      ))}
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
