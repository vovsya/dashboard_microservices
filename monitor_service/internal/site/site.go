package site

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"io"
	"net/http"
	"strings"

	"github.com/PuerkitoBio/goquery"
	"github.com/sergi/go-diff/diffmatchpatch"
)

func FetchText(client *http.Client, url string, maxBody int64, maxText int) (string, error) {
	req, _ := http.NewRequest("GET", url, nil)
	req.Header.Set("User-Agent", "sitewatch/0.1")
	req.Header.Set("Accept", "text/html,*/*")

	resp, err := client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	body, err := readLimited(resp.Body, maxBody)
	if err != nil {
		return "", err
	}

	txt, err := extractText(body)
	if err != nil {
		return "", err
	}

	if maxText > 0 && len(txt) > maxText {
		txt = txt[:maxText] + "…(truncated)"
	}
	return txt, nil
}

func Hash(s string) string {
	sum := sha256.Sum256([]byte(s))
	return hex.EncodeToString(sum[:])
}

func DiffPlusMinus(oldText, newText string, maxChars int) string {
	dmp := diffmatchpatch.New()
	diffs := dmp.DiffMain(oldText, newText, false)
	dmp.DiffCleanupSemantic(diffs)

	var b strings.Builder
	for _, d := range diffs {
		t := strings.TrimSpace(d.Text)
		if t == "" {
			continue
		}
		if len(t) > 400 {
			t = t[:400] + "…"
		}
		switch d.Type {
		case diffmatchpatch.DiffInsert:
			b.WriteString("+ ")
			b.WriteString(t)
			b.WriteString("\n")
		case diffmatchpatch.DiffDelete:
			b.WriteString("- ")
			b.WriteString(t)
			b.WriteString("\n")
		}
		if maxChars > 0 && b.Len() > maxChars {
			break
		}
	}
	out := b.String()
	if maxChars > 0 && len(out) > maxChars {
		out = out[:maxChars] + "…(truncated)"
	}
	return out
}

func readLimited(r io.Reader, max int64) ([]byte, error) {
	lr := io.LimitReader(r, max+1)
	b, err := io.ReadAll(lr)
	if err != nil {
		return nil, err
	}
	if int64(len(b)) > max {
		return nil, errors.New("body too large")
	}
	return b, nil
}

func extractText(html []byte) (string, error) {
	doc, err := goquery.NewDocumentFromReader(bytes.NewReader(html))
	if err != nil {
		return "", err
	}
	doc.Find("script,style,noscript").Remove()
	txt := strings.TrimSpace(doc.Text())
	txt = strings.Join(strings.Fields(txt), " ")
	return txt, nil
}
