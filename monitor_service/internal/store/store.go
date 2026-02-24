package store

import (
	"context"
	"database/sql"
	"time"

	"github.com/google/uuid"
	"github.com/jmoiron/sqlx"
)

type Store struct{ DB *sqlx.DB }

type Monitor struct {
	ID              uuid.UUID `db:"id" json:"id"`
	URL             string    `db:"url" json:"url"`
	IntervalMinutes int       `db:"interval_minutes" json:"interval_minutes"`
	CreatedAt       time.Time `db:"created_at" json:"created_at"`
	NextCheckAt     time.Time `db:"next_check_at" json:"next_check_at"`
}

type Change struct {
	ID        int64     `db:"id" json:"id"`
	CheckedAt time.Time `db:"checked_at" json:"checked_at"`
	Diff      string    `db:"diff" json:"diff"`
	Summary   *string   `db:"summary" json:"summary,omitempty"`
}

type MonitorState struct {
	ID       uuid.UUID `db:"id"`
	URL      string    `db:"url"`
	LastHash *string   `db:"last_text_hash"`
	LastText *string   `db:"last_text"`
}

type DueJob struct {
	MonitorID uuid.UUID
	URL       string
}

func (s Store) CreateOrUpdateMonitor(ctx context.Context, url string, intervalMin int) (Monitor, error) {
	var m Monitor
	q := `
INSERT INTO monitors(url, interval_minutes, next_check_at)
VALUES ($1,$2, now())
ON CONFLICT (url) DO UPDATE
  SET interval_minutes=EXCLUDED.interval_minutes,
      next_check_at=now()
RETURNING id, url, interval_minutes, created_at, next_check_at;
`
	err := s.DB.GetContext(ctx, &m, q, url, intervalMin)
	return m, err
}

func (s Store) GetChanges(ctx context.Context, monitorID uuid.UUID, limit int) ([]Change, error) {
	var items []Change
	err := s.DB.SelectContext(ctx, &items, `
SELECT id, checked_at, diff, summary
FROM changes
WHERE monitor_id=$1
ORDER BY checked_at DESC
LIMIT $2;
`, monitorID, limit)
	return items, err
}

func (s Store) UpdateChangeSummary(ctx context.Context, changeID int64, summary string) error {
	_, err := s.DB.ExecContext(ctx, `
UPDATE changes SET summary=$2
WHERE id=$1 AND (summary IS NULL OR summary='');
`, changeID, summary)
	return err
}

func (s Store) TakeDueAndBump(ctx context.Context, batch int) ([]DueJob, error) {
	tx, err := s.DB.BeginTxx(ctx, &sql.TxOptions{})
	if err != nil {
		return nil, err
	}
	defer func() { _ = tx.Rollback() }()

	type row struct {
		ID  uuid.UUID `db:"id"`
		URL string    `db:"url"`
	}

	q := `
WITH due AS (
  SELECT id, url
  FROM monitors
  WHERE next_check_at <= now()
  ORDER BY next_check_at
  LIMIT $1
  FOR UPDATE SKIP LOCKED
)
UPDATE monitors m
SET next_check_at = now() + (m.interval_minutes || ' minutes')::interval
FROM due
WHERE m.id = due.id
RETURNING due.id, due.url;
`
	var rows []row
	if err := tx.Select(&rows, q, batch); err != nil {
		return nil, err
	}
	if err := tx.Commit(); err != nil {
		return nil, err
	}

	out := make([]DueJob, 0, len(rows))
	for _, r := range rows {
		out = append(out, DueJob{MonitorID: r.ID, URL: r.URL})
	}
	return out, nil
}

func (s Store) GetMonitorState(ctx context.Context, id uuid.UUID) (MonitorState, error) {
	var st MonitorState
	err := s.DB.GetContext(ctx, &st, `
SELECT id, url, last_text_hash, last_text
FROM monitors
WHERE id=$1;
`, id)
	return st, err
}

func (s Store) TouchCheckedAt(ctx context.Context, id uuid.UUID, checkedAt time.Time) error {
	_, err := s.DB.ExecContext(ctx, `UPDATE monitors SET last_checked_at=$2 WHERE id=$1`, id, checkedAt)
	return err
}

func (s Store) SaveBaseline(ctx context.Context, id uuid.UUID, checkedAt time.Time, hash string, text string) error {
	_, err := s.DB.ExecContext(ctx, `
UPDATE monitors SET
  last_checked_at=$2,
  last_text_hash=$3,
  last_text=$4
WHERE id=$1;
`, id, checkedAt, hash, text)
	return err
}

func (s Store) InsertChange(ctx context.Context, id uuid.UUID, checkedAt time.Time, diff string) error {
	_, err := s.DB.ExecContext(ctx, `
INSERT INTO changes(monitor_id, checked_at, diff, summary)
VALUES ($1,$2,$3,NULL);
`, id, checkedAt, diff)
	return err
}
