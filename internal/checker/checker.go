package checker

import (
	"context"
	"crypto/tls"
	"fmt"
	"net"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"

	"healthcheck/internal/config"
)

// Checker HTTPチェックを実行する構造体
type Checker struct {
	config     *config.Config
	httpClient *http.Client
	domainRate map[string]*rateLimiter
	globalRate *rateLimiter
	rateMutex  sync.Mutex
}

// rateLimiter レート制限を管理する構造体
type rateLimiter struct {
	ticker *time.Ticker
	limit  int
	count  int
	mutex  sync.Mutex
}

// NewChecker 新しいCheckerインスタンスを作成
func NewChecker(cfg *config.Config) *Checker {
	transport := &http.Transport{
		DialContext: (&net.Dialer{
			Timeout: 5 * time.Second,
		}).DialContext,
		TLSHandshakeTimeout: 10 * time.Second,
		MaxIdleConns:        100,
		IdleConnTimeout:     90 * time.Second,
	}

	// TLS設定
	if cfg.Insecure {
		transport.TLSClientConfig = &tls.Config{
			InsecureSkipVerify: true,
		}
	}

	client := &http.Client{
		Transport: transport,
		Timeout:   cfg.Timeout,
		CheckRedirect: func(req *http.Request, via []*http.Request) error {
			if len(via) >= 3 {
				return fmt.Errorf("stopped after 3 redirects")
			}
			return nil
		},
	}

	return &Checker{
		config:     cfg,
		httpClient: client,
		domainRate: make(map[string]*rateLimiter),
		globalRate: newRateLimiter(cfg.GlobalRate),
	}
}

// newRateLimiter 新しいレート制限器を作成
func newRateLimiter(limit int) *rateLimiter {
	rl := &rateLimiter{
		ticker: time.NewTicker(time.Second),
		limit:  limit,
		count:  0,
	}
	go rl.resetCounter()
	return rl
}

// resetCounter カウンターをリセット
func (rl *rateLimiter) resetCounter() {
	for range rl.ticker.C {
		rl.mutex.Lock()
		rl.count = 0
		rl.mutex.Unlock()
	}
}

// allow リクエストが許可されるかチェック
func (rl *rateLimiter) allow() bool {
	rl.mutex.Lock()
	defer rl.mutex.Unlock()
	if rl.count < rl.limit {
		rl.count++
		return true
	}
	return false
}

// waitForRateLimit レート制限を待機
func (rl *rateLimiter) waitForRateLimit() {
	for !rl.allow() {
		time.Sleep(100 * time.Millisecond)
	}
}

// getDomainRateLimiter ドメインごとのレート制限器を取得
func (c *Checker) getDomainRateLimiter(domain string) *rateLimiter {
	c.rateMutex.Lock()
	defer c.rateMutex.Unlock()

	if rl, exists := c.domainRate[domain]; exists {
		return rl
	}

	rl := newRateLimiter(c.config.DomainRate)
	c.domainRate[domain] = rl
	return rl
}

// CheckURL 単一URLのチェックを実行
func (c *Checker) CheckURL(ctx context.Context, targetURL string) *CheckResult {
	result := &CheckResult{
		URL:       targetURL,
		Timestamp: time.Now(),
		Success:   false,
	}

	// URLのパース
	parsedURL, err := url.Parse(targetURL)
	if err != nil {
		result.Error = "invalid_url"
		result.ErrorMessage = fmt.Sprintf("URL parse error: %v", err)
		return result
	}

	domain := parsedURL.Hostname()

	// レート制限のチェック
	c.globalRate.waitForRateLimit()
	domainRL := c.getDomainRateLimiter(domain)
	domainRL.waitForRateLimit()

	// DNS解決時間の計測
	dnsStart := time.Now()
	_, err = net.LookupHost(domain)
	dnsDuration := time.Since(dnsStart)

	// HTTPリクエストの開始時間
	startTime := time.Now()

	// タイムアウト付きコンテキスト
	reqCtx, cancel := context.WithTimeout(ctx, c.config.MaxLatency)
	defer cancel()

	// HTTPリクエストの作成
	req, err := http.NewRequestWithContext(reqCtx, "GET", targetURL, nil)
	if err != nil {
		result.Error = "request_error"
		result.ErrorMessage = fmt.Sprintf("Request creation error: %v", err)
		return result
	}

	req.Header.Set("User-Agent", "HealthCheck/1.0")

	// HTTPリクエストの実行
	resp, err := c.httpClient.Do(req)
	responseTime := time.Since(startTime)

	// レイテンシの計算（DNS解決 + 応答時間）
	result.Latency = dnsDuration + responseTime

	// エラーチェック
	if err != nil {
		result.Error = "request_failed"
		result.ErrorMessage = err.Error()
		if responseTime >= c.config.MaxLatency {
			result.Error = "timeout"
			result.ErrorMessage = fmt.Sprintf("Response time exceeded %v: %v", c.config.MaxLatency, err)
		}
		return result
	}
	defer resp.Body.Close()

	// 応答時間が30秒を超えた場合
	if responseTime > c.config.MaxLatency {
		result.StatusCode = resp.StatusCode
		result.ResponseTime = responseTime
		result.Error = "timeout"
		result.ErrorMessage = fmt.Sprintf("Response time %v exceeded maximum %v", responseTime, c.config.MaxLatency)
		return result
	}

	// ステータスコードのチェック
	result.StatusCode = resp.StatusCode
	result.ResponseTime = responseTime
	result.Success = resp.StatusCode >= 200 && resp.StatusCode < 300

	if !result.Success {
		result.Error = "http_error"
		result.ErrorMessage = fmt.Sprintf("HTTP %d: %s", resp.StatusCode, resp.Status)
	}

	return result
}

// CheckURLWithRetry リトライ機能付きでURLをチェック
func (c *Checker) CheckURLWithRetry(ctx context.Context, targetURL string) *CheckResult {
	var result *CheckResult
	backoff := 1 * time.Second

	for attempt := 0; attempt <= c.config.Retries; attempt++ {
		if attempt > 0 {
			// 指数バックオフ
			time.Sleep(backoff)
			backoff *= 2
		}

		result = c.CheckURL(ctx, targetURL)

		// 成功した場合、またはリトライ不可能なエラーの場合は終了
		if result.Success || (result.Error != "timeout" && result.Error != "request_failed") {
			break
		}
	}

	return result
}

// CheckURLs 複数のURLを並列でチェック
func (c *Checker) CheckURLs(ctx context.Context, urls []string, resultChan chan<- *CheckResult, progressChan chan<- int) {
	var wg sync.WaitGroup
	semaphore := make(chan struct{}, c.config.Concurrency)
	completed := 0
	var completedMutex sync.Mutex

	for _, targetURL := range urls {
		wg.Add(1)
		go func(url string) {
			defer wg.Done()

			// セマフォで並列度を制御
			semaphore <- struct{}{}
			defer func() { <-semaphore }()

			// URLチェックの実行
			result := c.CheckURLWithRetry(ctx, url)

			// 結果を送信
			resultChan <- result

			// 進捗を更新
			completedMutex.Lock()
			completed++
			if progressChan != nil {
				progressChan <- completed
			}
			completedMutex.Unlock()
		}(targetURL)
	}

	wg.Wait()
	close(resultChan)
	if progressChan != nil {
		close(progressChan)
	}
}

// ExtractDomain URLからドメインを抽出
func ExtractDomain(targetURL string) string {
	parsedURL, err := url.Parse(targetURL)
	if err != nil {
		return ""
	}
	host := parsedURL.Hostname()
	if idx := strings.Index(host, ":"); idx != -1 {
		host = host[:idx]
	}
	return host
}
