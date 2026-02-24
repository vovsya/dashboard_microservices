package queue

import (
	"context"
	"strings"

	"github.com/redis/go-redis/v9"
)

type Queue struct {
	RDB    *redis.Client
	Stream string
}

func EnsureGroup(ctx context.Context, rdb *redis.Client, stream, group string) error {
	err := rdb.XGroupCreateMkStream(ctx, stream, group, "0").Err()
	if err != nil && !strings.Contains(err.Error(), "BUSYGROUP") {
		return err
	}
	return nil
}

func (q Queue) Enqueue(ctx context.Context, monitorID, url string) error {
	_, err := q.RDB.XAdd(ctx, &redis.XAddArgs{
		Stream: q.Stream,
		Values: map[string]any{
			"monitor_id": monitorID,
			"url":        url,
		},
	}).Result()
	return err
}
