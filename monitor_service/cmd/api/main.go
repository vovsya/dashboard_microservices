package main

import (
	"context"
	"os"
	"time"

	"github.com/jackc/pgx/v5/stdlib"
	"github.com/jmoiron/sqlx"
	"github.com/redis/go-redis/v9"

	"sitewatch/internal/app"
	"sitewatch/internal/config"
	"sitewatch/internal/llm"
	"sitewatch/internal/queue"
	"sitewatch/internal/store"
)

func main() {
	cfg := config.Load(os.Getenv)
	ctx := context.Background()

	_ = stdlib.GetDefaultDriver()
	db := sqlx.MustConnect("pgx", cfg.DBURL)

	rdb := redis.NewClient(&redis.Options{Addr: cfg.RedisAddr})

	a := app.App{
		Store: store.Store{DB: db},
		Queue: queue.Queue{RDB: rdb, Stream: cfg.RedisStream},
		Oll: llm.Ollama{
			BaseURL: cfg.LLMURL,
			Model:   cfg.LLMModel,
			Timeout: 25 * time.Second,
		},
		LLMEnabled: cfg.LLMEnabled,

		SchedTick:  time.Duration(cfg.SchedTickSec) * time.Second,
		SchedBatch: cfg.SchedBatch,
	}

	go a.RunScheduler(ctx)

	r := a.Router()
	_ = r.Run(cfg.HTTPAddr)
}
