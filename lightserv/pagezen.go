package main

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"os"
	"time"

	"github.com/PuerkitoBio/goquery"
	"github.com/go-shiori/go-readability"
)

type ExtractRequest struct {
	URL     string `json:"url"`
	Timeout int    `json:"timeout"`
}

type ExtractResponse struct {
	Title         string    `json:"title"`
	Content       string    `json:"content"`
	Excerpt       string    `json:"excerpt"`
	Byline        string    `json:"byline"`
	SiteName      string    `json:"siteName"`
	Length        int       `json:"length"`
	PublishedTime string    `json:"publishedTime"`
	Metadata      struct {
		ExtractionMethod string `json:"extractionMethod"`
		ExtractionTime   string `json:"extractionTime"`
	} `json:"metadata"`
}

func extractContent(targetURL string, timeout int) (*ExtractResponse, error) {
	client := &http.Client{
		Timeout: time.Duration(timeout) * time.Millisecond,
	}

	resp, err := client.Get(targetURL)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch URL: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("non-200 status code: %d", resp.StatusCode)
	}

	doc, err := goquery.NewDocumentFromReader(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to parse HTML: %v", err)
	}

	parsedURL, err := url.Parse(targetURL)
	if err != nil {
		return nil, fmt.Errorf("failed to parse URL: %v", err)
	}

	article, err := readability.FromDocument(doc.First().Nodes[0], parsedURL)
	if err != nil {
		return nil, fmt.Errorf("failed to extract readability: %v", err)
	}

	pubTime := ""
	if article.PublishedTime != nil {
		pubTime = article.PublishedTime.Format(time.RFC3339)
	}

	response := &ExtractResponse{
		Title:         article.Title,
		Content:       article.TextContent,
		Excerpt:       article.Excerpt,
		Byline:        article.Byline,
		SiteName:      article.SiteName,
		Length:        len(article.TextContent),
		PublishedTime: pubTime,
		Metadata: struct {
			ExtractionMethod string `json:"extractionMethod"`
			ExtractionTime   string `json:"extractionTime"`
		}{
			ExtractionMethod: "pagezen",
			ExtractionTime:   time.Now().UTC().Format(time.RFC3339),
		},
	}

	return response, nil
}

func extractHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	body, err := io.ReadAll(r.Body)
	if err != nil {
		http.Error(w, "Failed to read request body", http.StatusBadRequest)
		return
	}

	var req ExtractRequest
	if err := json.Unmarshal(body, &req); err != nil {
		http.Error(w, "Invalid request format", http.StatusBadRequest)
		return
	}

	if req.URL == "" {
		http.Error(w, "URL is required", http.StatusBadRequest)
		return
	}

	if req.Timeout == 0 {
		req.Timeout = 30000 // 30 seconds default
	}

	response, err := extractContent(req.URL, req.Timeout)
	if err != nil {
		http.Error(w, fmt.Sprintf("Extraction failed: %v", err), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(response)
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]string{"status": "healthy"})
}

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	http.HandleFunc("/extract", extractHandler)
	http.HandleFunc("/health", healthHandler)

	log.Printf("Starting Page Zen service on port %s", port)
	log.Fatal(http.ListenAndServe(":"+port, nil))
}
