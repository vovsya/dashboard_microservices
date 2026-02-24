package main

import (
	"context"
	"errors"
	"net/url"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/jackc/pgx/v5/stdlib"
	"github.com/jmoiron/sqlx"
	"github.com/redis/go-redis/v9"

	"sitewatch/internal/config"
	"sitewatch/internal/events"
	"sitewatch/internal/queue"
	"sitewatch/internal/store"
)

func main() {
	cfg := config.Load(os.Getenv)
	ctx := context.Background()

	_ = stdlib.GetDefaultDriver()
	db := sqlx.MustConnect("pgx", cfg.DBURL)
	rdb := redis.NewClient(&redis.Options{Addr: cfg.RedisAddr})

	_ = queue.EnsureGroup(ctx, rdb, cfg.DashboardCmdStream, cfg.DashboardCmdGroup)

	st := store.Store{DB: db}
	jobs := queue.Queue{RDB: rdb, Stream: cfg.RedisStream}
	pub := events.Publisher{RDB: rdb, Stream: cfg.DashboardEventStream}

	for {
		res, err := rdb.XReadGroup(ctx, &redis.XReadGroupArgs{
			Group:    cfg.DashboardCmdGroup,
			Consumer: cfg.DashboardConsumer,
			Streams:  []string{cfg.DashboardCmdStream, ">"},
			Count:    50,
			Block:    5 * time.Second,
		}).Result()
		if err != nil {
			if err == redis.Nil {
				continue
			}
			time.Sleep(time.Second)
			continue
		}

		for _, s := range res {
			for _, msg := range s.Messages {
				if handleCommand(ctx, st, jobs, pub, msg) == nil {
					_ = rdb.XAck(ctx, cfg.DashboardCmdStream, cfg.DashboardCmdGroup, msg.ID).Err()
				}
			}
		}
	}
}

func handleCommand(ctx context.Context, st store.Store, jobs queue.Queue, pub events.Publisher, msg redis.XMessage) error {
	typ := getStr(msg.Values, "type")
	if typ != "register_monitor" {
		return nil
	}

	userID := getStr(msg.Values, "user_id")
	rawURL := getStr(msg.Values, "url")
	intervalStr := getStr(msg.Values, "interval_minutes")
	if rawURL == "" || userID == "" {
		return errors.New("missing user_id/url")
	}
	if err := validateURL(rawURL); err != nil {
		_ = pub.Publish(ctx, map[string]any{
			"type":    "monitor_registered",
			"user_id": userID,
			"url":     rawURL,
			"status":  "error",
			"error":   err.Error(),
		})
		return nil
	}
	interval := 5
	if intervalStr != "" {
		if n, err := strconv.Atoi(intervalStr); err == nil && n >= 1 && n <= 1440 {
			interval = n
		}
	}

	m, err := st.CreateOrUpdateMonitor(ctx, rawURL, interval)
	if err != nil {
		return err
	}
	_ = jobs.Enqueue(ctx, m.ID.String(), m.URL)
	_ = pub.Publish(ctx, map[string]any{
		"type":             "monitor_registered",
		"status":           "ok",
		"user_id":          userID,
		"url":              m.URL,
		"monitor_id":       m.ID.String(),
		"interval_minutes": strconv.Itoa(m.IntervalMinutes),
	})
	return nil
}

func getStr(m map[string]any, key string) string {
	v, ok := m[key]
	if !ok || v == nil {
		return ""
	}
	switch t := v.(type) {
	case string:
		return strings.TrimSpace(t)
	case []byte:
		return strings.TrimSpace(string(t))
	default:
		return ""
	}
}

func validateURL(raw string) error {
	u, err := url.Parse(strings.TrimSpace(raw))
	if err != nil {
		return err
	}
	if u.Scheme != "http" && u.Scheme != "https" {
		return errors.New("url scheme must be http/https")
	}
	if u.Host == "" {
		return errors.New("url host is empty")
	}
	return nil
}
