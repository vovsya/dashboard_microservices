package llm

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"strings"
	"time"
)

type Ollama struct {
	BaseURL string
	Model   string
	Timeout time.Duration
}

type req struct {
	Model    string         `json:"model"`
	Stream   bool           `json:"stream"`
	Messages []message      `json:"messages"`
	Options  map[string]any `json:"options,omitempty"`
}
type message struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}
type resp struct {
	Message message `json:"message"`
}

func (o Ollama) SummarizeDiff(ctx context.Context, diff string) (string, error) {
	diff = strings.TrimSpace(diff)
	if diff == "" {
		return "", errors.New("empty diff")
	}

	prompt := "Суммируй изменения по diff в 3–6 коротких пунктах. Не выдумывай.\n\nDIFF:\n" + diff
	body := req{
		Model:  o.Model,
		Stream: false,
		Messages: []message{
			{Role: "user", Content: prompt},
		},
		Options: map[string]any{"temperature": 0.2},
	}

	b, _ := json.Marshal(body)
	httpReq, _ := http.NewRequestWithContext(ctx, "POST", o.BaseURL+"/api/chat", bytes.NewReader(b))
	httpReq.Header.Set("Content-Type", "application/json")

	cl := &http.Client{Timeout: o.Timeout}
	httpResp, err := cl.Do(httpReq)
	if err != nil {
		return "", err
	}
	defer httpResp.Body.Close()

	if httpResp.StatusCode >= 300 {
		return "", errors.New("ollama bad status")
	}

	var out resp
	if err := json.NewDecoder(httpResp.Body).Decode(&out); err != nil {
		return "", err
	}
	return out.Message.Content, nil
}
