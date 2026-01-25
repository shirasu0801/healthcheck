package web

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"

	"healthcheck/internal/checker"
	"healthcheck/internal/config"
	"healthcheck/internal/dashboard"
	"healthcheck/internal/stats"
	"healthcheck/internal/storage"
)

// Server Webサーバー
type Server struct {
	checker *checker.Checker
	config  *config.Config
}

// NewServer 新しいWebサーバーを作成
func NewServer(cfg *config.Config) *Server {
	return &Server{
		checker: checker.NewChecker(cfg),
		config:  cfg,
	}
}

// Start サーバーを起動
func (s *Server) Start(port string) error {
	http.HandleFunc("/", s.handleIndex)
	http.HandleFunc("/check", s.handleCheck)
	http.HandleFunc("/api/check", s.handleAPICheck)
	http.HandleFunc("/dashboard", s.handleDashboard)

	addr := ":" + port
	fmt.Printf("Health Check Server started on http://localhost%s\n", addr)
	fmt.Printf("Open your browser and navigate to http://localhost%s\n", addr)
	return http.ListenAndServe(addr, nil)
}

// handleIndex インデックスページ
func (s *Server) handleIndex(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	html := `<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Health Check Tool</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            padding: 40px;
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 2em;
        }
        .subtitle {
            color: #666;
            margin-bottom: 30px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 500;
        }
        textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 5px;
            font-size: 14px;
            font-family: monospace;
            resize: vertical;
            min-height: 150px;
        }
        textarea:focus {
            outline: none;
            border-color: #667eea;
        }
        .help-text {
            font-size: 12px;
            color: #999;
            margin-top: 5px;
        }
        .options {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .option-group {
            display: flex;
            flex-direction: column;
        }
        .option-group label {
            font-size: 14px;
        }
        input[type="number"] {
            padding: 8px;
            border: 2px solid #e0e0e0;
            border-radius: 5px;
            font-size: 14px;
        }
        input[type="number"]:focus {
            outline: none;
            border-color: #667eea;
        }
        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 5px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            width: 100%;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        button:active {
            transform: translateY(0);
        }
        button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        #loading {
            display: none;
            text-align: center;
            margin-top: 20px;
            color: #667eea;
        }
        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 10px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 Health Check Tool</h1>
        <p class="subtitle">複数のURLの生存確認を並列で実行します</p>
        
        <form id="checkForm">
            <div class="form-group">
                <label for="urls">URLリスト（1行に1つのURL）:</label>
                <textarea id="urls" name="urls" placeholder="https://example.com&#10;https://api.example.com&#10;https://www.google.com" required></textarea>
                <div class="help-text">コメント行（#で始まる行）と空行は無視されます</div>
            </div>
            
            <div class="options">
                <div class="option-group">
                    <label for="concurrency">並列度:</label>
                    <input type="number" id="concurrency" name="concurrency" value="10" min="1" max="100">
                </div>
                <div class="option-group">
                    <label for="timeout">タイムアウト（秒）:</label>
                    <input type="number" id="timeout" name="timeout" value="30" min="1" max="300">
                </div>
                <div class="option-group">
                    <label for="retries">リトライ回数:</label>
                    <input type="number" id="retries" name="retries" value="3" min="0" max="10">
                </div>
            </div>
            
            <button type="submit">ヘルスチェック実行</button>
        </form>
        
        <div id="loading">
            <div class="spinner"></div>
            <p>チェック中...</p>
        </div>
    </div>
    
    <script>
        document.getElementById('checkForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const form = e.target;
            const button = form.querySelector('button');
            const loading = document.getElementById('loading');
            const urls = document.getElementById('urls').value;
            
            button.disabled = true;
            loading.style.display = 'block';
            
            const formData = new FormData(form);
            formData.append('urls', urls);
            
            try {
                const response = await fetch('/api/check', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    throw new Error('チェックに失敗しました');
                }
                
                const data = await response.json();
                
                // 結果ページにリダイレクト
                window.location.href = '/dashboard?results=' + encodeURIComponent(JSON.stringify(data));
            } catch (error) {
                alert('エラー: ' + error.message);
            } finally {
                button.disabled = false;
                loading.style.display = 'none';
            }
        });
    </script>
</body>
</html>`

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.WriteHeader(http.StatusOK)
	fmt.Fprint(w, html)
}

// handleCheck チェック実行（POST）
func (s *Server) handleCheck(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	urlsText := r.FormValue("urls")
	urls := parseURLs(urlsText)

	if len(urls) == 0 {
		http.Error(w, "URLが指定されていません", http.StatusBadRequest)
		return
	}

	// 設定の更新
	if concurrency := r.FormValue("concurrency"); concurrency != "" {
		var c int
		fmt.Sscanf(concurrency, "%d", &c)
		if c > 0 {
			s.config.Concurrency = c
		}
	}
	if timeout := r.FormValue("timeout"); timeout != "" {
		var t int
		fmt.Sscanf(timeout, "%d", &t)
		if t > 0 {
			s.config.Timeout = time.Duration(t) * time.Second
			s.config.MaxLatency = s.config.Timeout
		}
	}
	if retries := r.FormValue("retries"); retries != "" {
		var r int
		fmt.Sscanf(retries, "%d", &r)
		if r >= 0 {
			s.config.Retries = r
		}
	}

	// チェッカーを再作成（設定を反映）
	s.checker = checker.NewChecker(s.config)

	// ヘルスチェック実行
	ctx := context.Background()
	resultChan := make(chan *checker.CheckResult, len(urls))
	progressChan := make(chan int, len(urls))

	startTime := time.Now()
	go s.checker.CheckURLs(ctx, urls, resultChan, progressChan)

	var results []*checker.CheckResult
	for result := range resultChan {
		results = append(results, result)
	}
	totalDuration := time.Since(startTime)

	// 統計情報の計算
	statistics := stats.CalculateStatistics(results, totalDuration)

	// 結果を保存
	historyPath, _ := storage.SaveHistory(results, statistics)

	// ダッシュボードを生成
	dashboardHTML := dashboard.GenerateDashboard(results, statistics, historyPath)

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.WriteHeader(http.StatusOK)
	fmt.Fprint(w, dashboardHTML)
}

// handleAPICheck APIエンドポイント（JSON形式で結果を返す）
func (s *Server) handleAPICheck(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	urlsText := r.FormValue("urls")
	urls := parseURLs(urlsText)

	if len(urls) == 0 {
		http.Error(w, "URLが指定されていません", http.StatusBadRequest)
		return
	}

	// 設定の更新
	if concurrency := r.FormValue("concurrency"); concurrency != "" {
		var c int
		fmt.Sscanf(concurrency, "%d", &c)
		if c > 0 {
			s.config.Concurrency = c
		}
	}
	if timeout := r.FormValue("timeout"); timeout != "" {
		var t int
		fmt.Sscanf(timeout, "%d", &t)
		if t > 0 {
			s.config.Timeout = time.Duration(t) * time.Second
			s.config.MaxLatency = s.config.Timeout
		}
	}
	if retries := r.FormValue("retries"); retries != "" {
		var r int
		fmt.Sscanf(retries, "%d", &r)
		if r >= 0 {
			s.config.Retries = r
		}
	}

	// チェッカーを再作成
	s.checker = checker.NewChecker(s.config)

	// ヘルスチェック実行
	ctx := context.Background()
	resultChan := make(chan *checker.CheckResult, len(urls))
	progressChan := make(chan int, len(urls))

	startTime := time.Now()
	go s.checker.CheckURLs(ctx, urls, resultChan, progressChan)

	var results []*checker.CheckResult
	for result := range resultChan {
		results = append(results, result)
	}
	totalDuration := time.Since(startTime)

	// 統計情報の計算
	statistics := stats.CalculateStatistics(results, totalDuration)

	// 結果を保存
	historyPath, _ := storage.SaveHistory(results, statistics)

	// JSON形式で返す
	response := map[string]interface{}{
		"results":     results,
		"statistics":  statistics,
		"historyPath": historyPath,
	}

	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	json.NewEncoder(w).Encode(response)
}

// handleDashboard ダッシュボード表示
func (s *Server) handleDashboard(w http.ResponseWriter, r *http.Request) {
	resultsParam := r.URL.Query().Get("results")
	
	var results []*checker.CheckResult
	var statistics *stats.Statistics
	
	if resultsParam != "" {
		var data map[string]interface{}
		if err := json.Unmarshal([]byte(resultsParam), &data); err == nil {
			// 結果をパース
			if resultsData, ok := data["results"].([]interface{}); ok {
				for _, item := range resultsData {
					if itemMap, ok := item.(map[string]interface{}); ok {
						result := &checker.CheckResult{}
						if url, ok := itemMap["url"].(string); ok {
							result.URL = url
						}
						if sc, ok := itemMap["status_code"].(float64); ok {
							result.StatusCode = int(sc)
						}
						if success, ok := itemMap["success"].(bool); ok {
							result.Success = success
						}
						if rt, ok := itemMap["response_time_ms"].(float64); ok {
							result.ResponseTime = time.Duration(rt) * time.Millisecond
						}
						if lat, ok := itemMap["latency_ms"].(float64); ok {
							result.Latency = time.Duration(lat) * time.Millisecond
						}
						if err, ok := itemMap["error"].(string); ok {
							result.Error = err
						}
						if errMsg, ok := itemMap["error_message"].(string); ok {
							result.ErrorMessage = errMsg
						}
						results = append(results, result)
					}
				}
			}
			// 統計情報をパース
			if statsData, ok := data["statistics"].(map[string]interface{}); ok {
				statistics = &stats.Statistics{}
				if total, ok := statsData["total_requests"].(float64); ok {
					statistics.TotalRequests = int(total)
				}
				if success, ok := statsData["success_count"].(float64); ok {
					statistics.SuccessCount = int(success)
				}
				if failure, ok := statsData["failure_count"].(float64); ok {
					statistics.FailureCount = int(failure)
				}
				if rate, ok := statsData["success_rate"].(float64); ok {
					statistics.SuccessRate = rate
				}
			}
		}
	}
	
	historyPath := ""
	if len(results) > 0 {
		historyPath, _ = storage.SaveHistory(results, statistics)
	}
	
	dashboardHTML := dashboard.GenerateDashboard(results, statistics, historyPath)
	
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.WriteHeader(http.StatusOK)
	fmt.Fprint(w, dashboardHTML)
}

// parseURLs URLテキストをパース
func parseURLs(text string) []string {
	lines := strings.Split(text, "\n")
	var urls []string
	
	for _, line := range lines {
		line = strings.TrimSpace(line)
		// 空行とコメント行をスキップ
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		// URLのバリデーション（簡単なチェック）
		if strings.HasPrefix(line, "http://") || strings.HasPrefix(line, "https://") {
			urls = append(urls, line)
		}
	}
	
	return urls
}
