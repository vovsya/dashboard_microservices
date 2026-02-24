package config

import (
	"strconv"
	"strings"
)

type Config struct {
	DBURL string

	RedisAddr   string
	RedisStream string
	RedisGroup  string
	WorkerName  string

	DashboardCmdStream   string
	DashboardCmdGroup    string
	DashboardEventStream string
	DashboardConsumer    string

	HTTPAddr string

	SchedTickSec int
	SchedBatch   int

	HTTPTimeoutSec int
	MaxBodyBytes   int64
	MaxTextChars   int
	MaxDiffChars   int

	LLMEnabled bool
	LLMURL     string
	LLMModel   string
}

func Load(get func(string) string) Config {
	return Config{
		DBURL: env(get, "DATABASE_URL", "postgres://postgres:postgres@localhost:5434/sitewatch?sslmode=disable"),

		RedisAddr:   env(get, "REDIS_ADDR", "localhost:6379"),
		RedisStream: env(get, "REDIS_STREAM", "site_jobs"),
		RedisGroup:  env(get, "REDIS_GROUP", "workers"),
		WorkerName:  env(get, "WORKER_NAME", "worker-1"),

		DashboardCmdStream:   env(get, "DASHBOARD_CMD_STREAM", "dashboard_monitor_cmd"),
		DashboardCmdGroup:    env(get, "DASHBOARD_CMD_GROUP", "dashboard_bridge"),
		DashboardEventStream: env(get, "DASHBOARD_EVENT_STREAM", "dashboard_monitor_events"),
		DashboardConsumer:    env(get, "DASHBOARD_CONSUMER", "dashboard-bridge-1"),

		HTTPAddr: env(get, "HTTP_ADDR", ":8000"),

		SchedTickSec: envInt(get, "SCHED_TICK_SEC", 10),
		SchedBatch:   envInt(get, "SCHED_BATCH", 50),

		HTTPTimeoutSec: envInt(get, "HTTP_TIMEOUT_SEC", 20),
		MaxBodyBytes:   envInt64(get, "MAX_BODY_BYTES", 2*1024*1024),
		MaxTextChars:   envInt(get, "MAX_TEXT_CHARS", 200000),
		MaxDiffChars:   envInt(get, "MAX_DIFF_CHARS", 12000),

		LLMEnabled: envBool(get, "LLM_ENABLED", true),
		LLMURL:     env(get, "LLM_URL", "http://localhost:11434"),
		LLMModel:   env(get, "LLM_MODEL", "qwen2.5:1.5b-instruct"),
	}
}

func env(get func(string) string, key, def string) string {
	v := strings.TrimSpace(get(key))
	if v == "" {
		return def
	}
	return v
}

func envInt(get func(string) string, key string, def int) int {
	v := strings.TrimSpace(get(key))
	if v == "" {
		return def
	}
	n, err := strconv.Atoi(v)
	if err != nil {
		return def
	}
	return n
}

func envInt64(get func(string) string, key string, def int64) int64 {
	v := strings.TrimSpace(get(key))
	if v == "" {
		return def
	}
	n, err := strconv.ParseInt(v, 10, 64)
	if err != nil {
		return def
	}
	return n
}

func envBool(get func(string) string, key string, def bool) bool {
	v := strings.ToLower(strings.TrimSpace(get(key)))
	if v == "" {
		return def
	}
	return v == "1" || v == "true" || v == "yes"
}
