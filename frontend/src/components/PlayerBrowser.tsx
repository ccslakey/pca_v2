import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useLeaderboard } from "../hooks";
import type { LeaderboardFilters, LeaderboardPlayer } from "../types";
import { PLAYER_COLORS, MAX_PLAYERS } from "../constants";
import { posLabel } from "../utils/format";
import "./PlayerBrowser.scss";

// ---- constants ----

const ERA_PRESETS = [
  { label: "All eras", era_start: undefined, era_end: undefined },
  { label: "Pre-1920", era_start: undefined, era_end: 1919 },
  { label: "1920–60", era_start: 1920, era_end: 1960 },
  { label: "1961–93", era_start: 1961, era_end: 1993 },
  { label: "1994–09", era_start: 1994, era_end: 2009 },
  { label: "2010+", era_start: 2010, era_end: undefined },
];

const WAR_PRESETS = [
  { label: "Any", value: 0 },
  { label: "20+", value: 20 },
  { label: "40+", value: 40 },
  { label: "60+", value: 60 },
];

const POS_OPTIONS: { label: string; value: string }[] = [
  { label: "All", value: "" },
  { label: "P", value: "P" },
  { label: "C", value: "C" },
  { label: "1B", value: "1B" },
  { label: "2B", value: "2B" },
  { label: "3B", value: "3B" },
  { label: "SS", value: "SS" },
  { label: "LF", value: "LF" },
  { label: "CF", value: "CF" },
  { label: "RF", value: "RF" },
  { label: "DH", value: "DH" },
  { label: "B", value: "B" },
];

const SORT_COLS = [
  { key: "career_war", label: "Career WAR" },
  { key: "peak_war", label: "Peak WAR" },
  { key: "career_hr", label: "HR / ERA" },
  { key: "asg_count", label: "Awards" },
];

const EMBEDDED_PAGE_SIZES = [5, 15, 25];
const STANDALONE_PAGE_SIZES = [25, 50, 100, 250];

// ---- helpers ----

function playerColor(bbrefId: string): string {
  let hash = 0;
  for (const ch of bbrefId) hash = (hash * 31 + ch.charCodeAt(0)) & 0xffffffff;
  return PLAYER_COLORS[Math.abs(hash) % PLAYER_COLORS.length];
}

function initials(p: LeaderboardPlayer) {
  return `${p.first_name[0] ?? ""}${p.last_name[0] ?? ""}`.toUpperCase();
}

function years(p: LeaderboardPlayer) {
  const debut = p.debut ? new Date(p.debut).getUTCFullYear() : null;
  const final = p.final_game ? new Date(p.final_game).getUTCFullYear() : null;
  if (debut && final) return `${debut}–${final}`;
  return debut ? `${debut}–` : "—";
}

// ---- sub-components ----

function AwardBadges({ p }: { p: LeaderboardPlayer }) {
  const badges: JSX.Element[] = [];
  if (p.mvp_count > 0)
    badges.push(
      <span
        key="mvp"
        className="award-badge badge-mvp"
        title={`${p.mvp_count}× Most Valuable Player`}
      >
        ★{p.mvp_count > 1 ? `×${p.mvp_count}` : ""}
      </span>,
    );
  if (p.cy_count > 0)
    badges.push(
      <span
        key="cy"
        className="award-badge badge-cy"
        title={`${p.cy_count}× Cy Young Award`}
      >
        CY{p.cy_count > 1 ? `×${p.cy_count}` : ""}
      </span>,
    );
  if (p.gg_count > 0)
    badges.push(
      <span
        key="gg"
        className="award-badge badge-gg"
        title={`${p.gg_count}× Gold Glove`}
      >
        ◇{p.gg_count > 1 ? `×${p.gg_count}` : ""}
      </span>,
    );
  if (p.asg_count > 0)
    badges.push(
      <span
        key="asg"
        className="award-badge badge-asg"
        title={`${p.asg_count}× All-Star selection`}
      >
        {p.asg_count}AS
      </span>,
    );
  return <div className="award-badges">{badges}</div>;
}

interface SortHeaderProps {
  col: string;
  label: string;
  sort: string;
  order: "asc" | "desc";
  onSort: (col: string) => void;
}
function SortHeader({ col, label, sort, order, onSort }: SortHeaderProps) {
  const active = sort === col;
  return (
    <th
      className={`sortable ${active ? "is-active" : ""}`}
      onClick={() => onSort(col)}
    >
      {label}
      <span className="sort-arrow">
        {active ? (order === "desc" ? " ↓" : " ↑") : " ↕"}
      </span>
    </th>
  );
}

// ---- main component ----

interface PlayerBrowserProps {
  selectedIds?: string[];
  onSelect?: (id: string) => void;
  standalone?: boolean;
}

export function PlayerBrowser({
  selectedIds = [],
  onSelect,
  standalone = false,
}: PlayerBrowserProps) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const pageSizes = standalone ? STANDALONE_PAGE_SIZES : EMBEDDED_PAGE_SIZES;

  const [pos, setPos] = useState("");
  const [eraIdx, setEraIdx] = useState(0);
  const [minWar, setMinWar] = useState(0);
  const [sort, setSort] = useState("career_war");
  const [order, setOrder] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(pageSizes[0]);

  const era = ERA_PRESETS[eraIdx];

  const filters: LeaderboardFilters = {
    pos: pos || undefined,
    min_war: minWar || undefined,
    era_start: era.era_start,
    era_end: era.era_end,
    sort,
    order,
    page,
    page_size: pageSize,
  };

  const { data, isFetching } = useLeaderboard(filters);

  function handleSort(col: string) {
    if (sort === col) {
      setOrder((o) => (o === "desc" ? "asc" : "desc"));
    } else {
      setSort(col);
      setOrder("desc");
    }
    setPage(1);
  }

  function handleFilter<T>(setter: (v: T) => void, value: T) {
    setter(value);
    setPage(1);
  }

  function handleAdd(p: LeaderboardPlayer) {
    if (onSelect) {
      onSelect(p.bbref_id);
    } else {
      const existing = (searchParams.get("compare") ?? "")
        .split(",")
        .filter(Boolean);
      if (!existing.includes(p.bbref_id)) {
        navigate(`/?compare=${[...existing, p.bbref_id].join(",")}`);
      } else {
        navigate("/");
      }
    }
  }

  const isAtMax = selectedIds.length >= MAX_PLAYERS;
  const players = data?.results ?? [];
  const total = data?.count ?? 0;
  const totalPages = data?.total_pages ?? 1;
  const isInitialLoad = isFetching && !data;
  const isRefetching = isFetching && !!data;

  return (
    <div className="player-browser">
      {/* header */}
      <div className="browser-header">
        <div className="browser-title">
          Leaderboard
          <span className="browser-count">
            {isFetching ? "…" : `${total.toLocaleString()} players`}
          </span>
        </div>
        <div className="browser-page-sizes">
          <span>Rows per page: </span>
          {pageSizes.map((n) => (
            <button
              key={n}
              className={`page-size-btn ${pageSize === n ? "is-active" : ""}`}
              onClick={() => {
                setPageSize(n);
                setPage(1);
              }}
            >
              {n}
            </button>
          ))}
        </div>
      </div>

      {/* filters */}
      <div className="browser-filters">
        Position: &nbsp;
        <div className="filter-group">
          {POS_OPTIONS.map((o) => (
            <button
              key={o.value}
              className={`filter-chip ${pos === o.value ? "is-active" : ""}`}
              onClick={() => handleFilter(setPos, o.value)}
            >
              {o.label}
            </button>
          ))}
        </div>
        <select
          className="era-select"
          value={eraIdx}
          onChange={(e) => handleFilter(setEraIdx, Number(e.target.value))}
        >
          {ERA_PRESETS.map((ep, i) => (
            <option key={i} value={i}>
              {ep.label}
            </option>
          ))}
        </select>
        <div className="filter-group">
          Career WAR Minimum: &nbsp;
          {WAR_PRESETS.map((w) => (
            <button
              key={w.value}
              className={`filter-chip ${minWar === w.value ? "is-active" : ""}`}
              onClick={() => handleFilter(setMinWar, w.value)}
            >
              {w.label}
            </button>
          ))}
        </div>
      </div>

      {/* table */}
      <div
        className={`browser-table-wrap ${isRefetching ? "is-refetching" : ""}`}
      >
        <table className="browser-table">
          <thead>
            <tr>
              <th className="col-name">Name</th>
              <th className="col-pos">Pos</th>
              <th className="col-years">Years</th>
              {SORT_COLS.map((c) => (
                <SortHeader
                  key={c.key}
                  col={c.key}
                  label={c.label}
                  sort={sort}
                  order={order}
                  onSort={handleSort}
                />
              ))}
              <th className="col-action" />
            </tr>
          </thead>
          <tbody>
            {isInitialLoad &&
              Array.from({ length: pageSize > 15 ? 15 : pageSize }).map(
                (_, i) => (
                  <tr key={`skel-${i}`} className="skeleton-row">
                    <td>
                      <div className="skel skel-name" />
                    </td>
                    <td>
                      <div className="skel skel-short" />
                    </td>
                    <td>
                      <div className="skel skel-short" />
                    </td>
                    <td>
                      <div className="skel skel-num" />
                    </td>
                    <td>
                      <div className="skel skel-num" />
                    </td>
                    <td>
                      <div className="skel skel-num" />
                    </td>
                    <td>
                      <div className="skel skel-badges" />
                    </td>
                    <td />
                  </tr>
                ),
              )}
            {!isInitialLoad &&
              players.map((p) => {
                const color = playerColor(p.bbref_id);
                const isSelected = selectedIds.includes(p.bbref_id);
                const canAdd = !isSelected && !isAtMax;
                return (
                  <tr
                    key={p.bbref_id}
                    className={isSelected ? "is-selected" : ""}
                  >
                    <td className="col-name">
                      <div className="player-row-name">
                        <span
                          className="player-avatar"
                          style={{ background: color }}
                        >
                          {initials(p)}
                        </span>
                        <Link
                          to={`/player/${p.bbref_id}`}
                          className="player-name-link"
                        >
                          {p.first_name} {p.last_name}
                        </Link>
                      </div>
                    </td>
                    <td className="col-pos">
                      <span className="pos-tag">
                        {posLabel(p.primary_position, p.throws, p.is_pitcher)}
                      </span>
                    </td>
                    <td className="col-years">{years(p)}</td>
                    <td className="col-num">{p.career_war.toFixed(1)}</td>
                    <td className="col-num">{p.peak_war.toFixed(1)}</td>
                    <td className="col-num">
                      {p.is_pitcher ? (
                        p.career_era != null ? (
                          <>
                            {p.career_era.toFixed(2)}{" "}
                            <span className="stat-label">ERA</span>
                          </>
                        ) : (
                          "—"
                        )
                      ) : p.career_hr != null ? (
                        <>
                          {p.career_hr} <span className="stat-label">HR</span>
                        </>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="col-awards">
                      <AwardBadges p={p} />
                    </td>
                    <td className="col-action">
                      {isSelected ? (
                        <button className="add-btn is-added" disabled>
                          ✓
                        </button>
                      ) : (
                        <button
                          className="add-btn"
                          onClick={() => handleAdd(p)}
                          disabled={!canAdd && !!onSelect}
                          title={
                            isAtMax && onSelect
                              ? "Maximum players reached"
                              : undefined
                          }
                        >
                          {standalone ? "→" : "+"}
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            {!isInitialLoad && players.length === 0 && !isFetching && (
              <tr>
                <td colSpan={8} className="empty-row">
                  No players match these filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* pagination — always shown on standalone, hidden when single page on embedded */}
      {(standalone || totalPages > 1) && (
        <div className="browser-pagination">
          <button
            className="page-btn"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
          >
            ← Prev
          </button>
          <span className="page-info">
            Page {page} of {totalPages}
          </span>
          <button
            className="page-btn"
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
