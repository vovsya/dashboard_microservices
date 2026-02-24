package main

import (
	"context"
	"net/http"
	"os"
	"time"

	"github.com/jackc/pgx/v5/stdlib"
	"github.com/jmoiron/sqlx"
	"github.com/redis/go-redis/v9"

	"sitewatch/internal/app"
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

	// group создаём тут
	_ = queue.EnsureGroup(ctx, rdb, cfg.RedisStream, cfg.RedisGroup)

	a := app.App{
		Store: store.Store{DB: db},

		RDB:      rdb,
		Stream:   cfg.RedisStream,
		Group:    cfg.RedisGroup,
		Consumer: cfg.WorkerName,
		Events: events.Publisher{
			RDB:    rdb,
			Stream: cfg.DashboardEventStream,
		},

		HTTPClientTimeout: time.Duration(cfg.HTTPTimeoutSec) * time.Second,
		MaxBody:           cfg.MaxBodyBytes,
		MaxText:           cfg.MaxTextChars,
		MaxDiff:           cfg.MaxDiffChars,
	}

	// http client заранее (необязательно)
	_ = http.Client{Timeout: a.HTTPClientTimeout}

	_ = a.RunWorker(ctx)
}
