package app

import (
	"context"
	"errors"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/redis/go-redis/v9"

	"sitewatch/internal/events"
	"sitewatch/internal/llm"
	"sitewatch/internal/queue"
	"sitewatch/internal/site"
	"sitewatch/internal/store"
)

type App struct {
	Store  store.Store
	Queue  queue.Queue
	Oll    llm.Ollama
	Events events.Publisher

	LLMEnabled bool

	SchedTick  time.Duration
	SchedBatch int

	RDB      *redis.Client
	Stream   string
	Group    string
	Consumer string

	HTTPClientTimeout time.Duration
	MaxBody           int64
	MaxText           int
	MaxDiff           int
}

func (a App) Router() *gin.Engine {
	r := gin.Default()

	r.POST("/monitors", a.createMonitor)
	r.GET("/monitors/:id/changes", a.getChanges)

	return r
}

func (a App) RunScheduler(ctx context.Context) {
	t := time.NewTicker(a.SchedTick)
	defer t.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-t.C:
			jobs, err := a.Store.TakeDueAndBump(ctx, a.SchedBatch)
			if err != nil {
				continue
			}
			for _, j := range jobs {
				_ = a.Queue.Enqueue(ctx, j.MonitorID.String(), j.URL)
			}
		}
	}
}

func (a App) RunWorker(ctx context.Context) error {
	if err := queue.EnsureGroup(ctx, a.RDB, a.Stream, a.Group); err != nil {
		return err
	}
	client := &httpClient{Timeout: a.HTTPClientTimeout}

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
		}

		res, err := a.RDB.XReadGroup(ctx, &redis.XReadGroupArgs{
			Group:    a.Group,
			Consumer: a.Consumer,
			Streams:  []string{a.Stream, ">"},
			Count:    10,
			Block:    5 * time.Second,
		}).Result()

		if err != nil {
			if err == redis.Nil {
				continue
			}
			continue
		}

		for _, s := range res {
			for _, msg := range s.Messages {
				if a.handleJob(ctx, client, msg) == nil {
					_ = a.RDB.XAck(ctx, a.Stream, a.Group, msg.ID).Err()
				}
			}
		}
	}
}

func (a App) handleJob(ctx context.Context, client *httpClient, msg redis.XMessage) error {
	monitorIDStr := getStr(msg.Values, "monitor_id")
	if monitorIDStr == "" {
		return errors.New("missing monitor_id")
	}
	monitorID, err := uuid.Parse(monitorIDStr)
	if err != nil {
		return err
	}

	st, err := a.Store.GetMonitorState(ctx, monitorID)
	if err != nil {
		return err
	}

	checkedAt := time.Now().UTC()
	newText, err := site.FetchText(client.Client, st.URL, a.MaxBody, a.MaxText)
	if err != nil {
		_ = a.Store.TouchCheckedAt(ctx, st.ID, checkedAt)
		_ = a.Events.Publish(ctx, map[string]any{
			"type":       "monitor_checked",
			"monitor_id": st.ID.String(),
			"url":        st.URL,
			"status":     "down",
			"changed":    "false",
			"checked_at": checkedAt.Format(time.RFC3339Nano),
			"error":      err.Error(),
		})
		return nil
	}

	newHash := site.Hash(newText)
	changed := (st.LastHash != nil && strings.TrimSpace(*st.LastHash) != "" && newHash != *st.LastHash)

	if changed && st.LastText != nil && strings.TrimSpace(*st.LastText) != "" {
		d := site.DiffPlusMinus(*st.LastText, newText, a.MaxDiff)
		if strings.TrimSpace(d) != "" {
			_ = a.Store.InsertChange(ctx, st.ID, checkedAt, d)
		}
	}

	if err := a.Store.SaveBaseline(ctx, st.ID, checkedAt, newHash, newText); err != nil {
		return err
	}

	_ = a.Events.Publish(ctx, map[string]any{
		"type":       "monitor_checked",
		"monitor_id": st.ID.String(),
		"url":        st.URL,
		"status":     "up",
		"changed":    strconv.FormatBool(changed),
		"checked_at": checkedAt.Format(time.RFC3339Nano),
	})
	return nil
}

func (a App) createMonitor(c *gin.Context) {
	var req struct {
		URL             string `json:"url" binding:"required"`
		IntervalMinutes int    `json:"interval_minutes" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(400, gin.H{"error": err.Error()})
		return
	}
	if err := validateURL(req.URL); err != nil {
		c.JSON(400, gin.H{"error": err.Error()})
		return
	}
	if req.IntervalMinutes <= 0 || req.IntervalMinutes > 1440 {
		c.JSON(400, gin.H{"error": "interval_minutes must be 1..1440"})
		return
	}

	m, err := a.Store.CreateOrUpdateMonitor(c.Request.Context(), req.URL, req.IntervalMinutes)
	if err != nil {
		c.JSON(500, gin.H{"error": err.Error()})
		return
	}

	_ = a.Queue.Enqueue(c.Request.Context(), m.ID.String(), m.URL) // best-effort
	c.JSON(201, m)
}

func (a App) getChanges(c *gin.Context) {
	monitorID, err := uuid.Parse(c.Param("id"))
	if err != nil {
		c.JSON(400, gin.H{"error": "bad id"})
		return
	}
	limit := 50
	if v := c.Query("limit"); v != "" {
		if n, err := strconv.Atoi(v); err == nil && n > 0 && n <= 500 {
			limit = n
		}
	}

	items, err := a.Store.GetChanges(c.Request.Context(), monitorID, limit)
	if err != nil {
		c.JSON(500, gin.H{"error": err.Error()})
		return
	}

	if a.LLMEnabled {
		for i := range items {
			if items[i].Summary != nil && strings.TrimSpace(*items[i].Summary) != "" {
				continue
			}
			s, err := a.Oll.SummarizeDiff(c.Request.Context(), items[i].Diff)
			if err != nil {
				continue
			}
			s = strings.TrimSpace(s)
			if s == "" {
				continue
			}
			_ = a.Store.UpdateChangeSummary(c.Request.Context(), items[i].ID, s)
			items[i].Summary = &s
		}
	}

	c.JSON(200, gin.H{"monitor_id": monitorID.String(), "items": items})
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

type httpClient struct {
	Client  *http.Client
	Timeout time.Duration
}

func (h *httpClient) init() {
	if h.Client == nil {
		h.Client = &http.Client{Timeout: h.Timeout}
	}
}

func (h *httpClient) Do(req *http.Request) (*http.Response, error) {
	h.init()
	return h.Client.Do(req)
}
