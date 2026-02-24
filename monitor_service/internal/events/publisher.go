package events

import (
	"context"
	"time"

	"github.com/redis/go-redis/v9"
)

type Publisher struct {
	RDB    *redis.Client
	Stream string
}

func (p Publisher) Publish(ctx context.Context, values map[string]any) error {
	if p.RDB == nil || p.Stream == "" {
		return nil
	}
	if _, ok := values["ts"]; !ok {
		values["ts"] = time.Now().UTC().Format(time.RFC3339Nano)
	}
	_, err := p.RDB.XAdd(ctx, &redis.XAddArgs{
		Stream: p.Stream,
		Values: values,
	}).Result()
	return err
}
