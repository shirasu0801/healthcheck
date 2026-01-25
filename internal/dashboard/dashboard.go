package dashboard

import (
	"encoding/json"
	"fmt"
	"html/template"
	"strings"
	"time"

	"healthcheck/internal/checker"
	"healthcheck/internal/stats"
)

// GenerateDashboard HTMLダッシュボードを生成
func GenerateDashboard(results []*checker.CheckResult, statistics *stats.Statistics, historyPath string) string {
	tmpl := `<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Health Check Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        .header h1 {
            font-size: 2em;
            margin-bottom: 10px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .stat-card h3 {
            color: #666;
            font-size: 14px;
            margin-bottom: 10px;
            text-transform: uppercase;
        }
        .stat-card .value {
            font-size: 2em;
            font-weight: bold;
            color: #333;
        }
        .stat-card.success .value { color: #10b981; }
        .stat-card.failure .value { color: #ef4444; }
        .stat-card.info .value { color: #3b82f6; }
        .results-section {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .results-section h2 {
            margin-bottom: 15px;
            color: #333;
        }
        .results-table {
            width: 100%;
            border-collapse: collapse;
        }
        .results-table th,
        .results-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e5e5e5;
        }
        .results-table th {
            background: #f9fafb;
            font-weight: 600;
            color: #666;
        }
        .results-table tr:hover {
            background: #f9fafb;
        }
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }
        .status-success { background: #d1fae5; color: #065f46; }
        .status-redirect { background: #fef3c7; color: #92400e; }
        .status-error { background: #fee2e2; color: #991b1b; }
        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .chart-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .chart-card h3 {
            margin-bottom: 15px;
            color: #333;
        }
        .actions {
            text-align: center;
            margin-top: 30px;
        }
        .btn {
            display: inline-block;
            padding: 12px 24px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-weight: 600;
            margin: 0 10px;
            transition: transform 0.2s;
        }
        .btn:hover {
            transform: translateY(-2px);
        }
        .error-message {
            color: #ef4444;
            font-size: 12px;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Health Check Dashboard</h1>
            <p>実行日時: {{.Timestamp}}</p>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <h3>総リクエスト数</h3>
                <div class="value">{{.Statistics.TotalRequests}}</div>
            </div>
            <div class="stat-card success">
                <h3>成功</h3>
                <div class="value">{{.Statistics.SuccessCount}}</div>
            </div>
            <div class="stat-card failure">
                <h3>失敗</h3>
                <div class="value">{{.Statistics.FailureCount}}</div>
            </div>
            <div class="stat-card info">
                <h3>成功率</h3>
                <div class="value">{{printf "%.1f" .Statistics.SuccessRate}}%</div>
            </div>
            <div class="stat-card">
                <h3>平均応答時間</h3>
                <div class="value">{{printf "%.0f" .Statistics.AvgResponseTimeMs}}ms</div>
            </div>
            <div class="stat-card">
                <h3>平均レイテンシ</h3>
                <div class="value">{{printf "%.0f" .Statistics.AvgLatencyMs}}ms</div>
            </div>
        </div>

        <div class="charts-grid">
            <div class="chart-card">
                <h3>ステータスコード分布</h3>
                <canvas id="statusChart"></canvas>
            </div>
            <div class="chart-card">
                <h3>応答時間分布</h3>
                <canvas id="responseTimeChart"></canvas>
            </div>
            <div class="chart-card">
                <h3>レイテンシ分布</h3>
                <canvas id="latencyChart"></canvas>
            </div>
        </div>

        <div class="results-section">
            <h2>詳細結果</h2>
            <table class="results-table">
                <thead>
                    <tr>
                        <th>URL</th>
                        <th>ステータス</th>
                        <th>ステータスコード</th>
                        <th>応答時間</th>
                        <th>レイテンシ</th>
                        <th>エラー</th>
                    </tr>
                </thead>
                <tbody>
                    {{range .Results}}
                    <tr>
                        <td>{{.URL}}</td>
                        <td>
                            {{if .Success}}
                                <span class="status-badge status-success">成功</span>
                            {{else if and (ge .StatusCode 300) (lt .StatusCode 400)}}
                                <span class="status-badge status-redirect">リダイレクト</span>
                            {{else}}
                                <span class="status-badge status-error">失敗</span>
                            {{end}}
                        </td>
                        <td>{{.StatusCode}}</td>
                        <td>{{printf "%.0f" .ResponseTimeMs}}ms</td>
                        <td>{{printf "%.0f" .LatencyMs}}ms</td>
                        <td>
                            {{if .Error}}
                                <div class="error-message">{{.Error}}</div>
                                {{if .ErrorMessage}}
                                    <div class="error-message">{{.ErrorMessage}}</div>
                                {{end}}
                            {{else}}
                                -
                            {{end}}
                        </td>
                    </tr>
                    {{end}}
                </tbody>
            </table>
        </div>

        <div class="actions">
            <a href="/" class="btn">新しいチェック</a>
        </div>
    </div>

    <script>
        const results = {{.ResultsJSON}};
        const statistics = {{.StatisticsJSON}};

        // ステータスコード分布
        const statusCounts = {};
        results.forEach(r => {
            const status = r.status_code || 0;
            statusCounts[status] = (statusCounts[status] || 0) + 1;
        });

        new Chart(document.getElementById('statusChart'), {
            type: 'doughnut',
            data: {
                labels: Object.keys(statusCounts).map(s => 'HTTP ' + s),
                datasets: [{
                    data: Object.values(statusCounts),
                    backgroundColor: [
                        '#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6'
                    ]
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });

        // 応答時間分布
        const responseTimes = results.filter(r => r.success).map(r => r.response_time_ms);
        if (responseTimes.length > 0) {
            const bins = 10;
            const min = Math.min(...responseTimes);
            const max = Math.max(...responseTimes);
            const binSize = (max - min) / bins;
            const histogram = new Array(bins).fill(0);
            
            responseTimes.forEach(rt => {
                const bin = Math.min(Math.floor((rt - min) / binSize), bins - 1);
                histogram[bin]++;
            });

            new Chart(document.getElementById('responseTimeChart'), {
                type: 'bar',
                data: {
                    labels: Array.from({length: bins}, (_, i) => 
                        Math.round(min + i * binSize) + 'ms'
                    ),
                    datasets: [{
                        label: '応答時間',
                        data: histogram,
                        backgroundColor: '#3b82f6'
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        }

        // レイテンシ分布
        const latencies = results.filter(r => r.success).map(r => r.latency_ms);
        if (latencies.length > 0) {
            const bins = 10;
            const min = Math.min(...latencies);
            const max = Math.max(...latencies);
            const binSize = (max - min) / bins;
            const histogram = new Array(bins).fill(0);
            
            latencies.forEach(lat => {
                const bin = Math.min(Math.floor((lat - min) / binSize), bins - 1);
                histogram[bin]++;
            });

            new Chart(document.getElementById('latencyChart'), {
                type: 'bar',
                data: {
                    labels: Array.from({length: bins}, (_, i) => 
                        Math.round(min + i * binSize) + 'ms'
                    ),
                    datasets: [{
                        label: 'レイテンシ',
                        data: histogram,
                        backgroundColor: '#10b981'
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        }
    </script>
</body>
</html>`

	data := struct {
		Timestamp     string
		Results       []*checker.CheckResult
		ResultsJSON   template.JS
		Statistics    *stats.Statistics
		StatisticsJSON template.JS
		HistoryPath   string
	}{
		Timestamp:  time.Now().Format("2006-01-02 15:04:05"),
		Results:    results,
		Statistics: statistics,
		HistoryPath: historyPath,
	}

	// JSON形式でデータを埋め込む（ミリ秒単位に変換）
	type ResultJSON struct {
		URL          string  `json:"url"`
		StatusCode   int     `json:"status_code"`
		Success      bool    `json:"success"`
		ResponseTime float64 `json:"response_time_ms"`
		Latency      float64 `json:"latency_ms"`
		Error        string  `json:"error,omitempty"`
		ErrorMessage string  `json:"error_message,omitempty"`
	}
	
	var resultsJSONData []ResultJSON
	for _, r := range results {
		resultsJSONData = append(resultsJSONData, ResultJSON{
			URL:          r.URL,
			StatusCode:   r.StatusCode,
			Success:      r.Success,
			ResponseTime: r.ResponseTimeMs(),
			Latency:      r.LatencyMs(),
			Error:        r.Error,
			ErrorMessage: r.ErrorMessage,
		})
	}
	
	type StatsJSON struct {
		TotalRequests   int     `json:"total_requests"`
		SuccessCount    int     `json:"success_count"`
		FailureCount    int     `json:"failure_count"`
		SuccessRate     float64 `json:"success_rate"`
		AvgResponseTime float64 `json:"avg_response_time_ms"`
		AvgLatency      float64 `json:"avg_latency_ms"`
	}
	
	statsJSONData := StatsJSON{
		TotalRequests:   statistics.TotalRequests,
		SuccessCount:    statistics.SuccessCount,
		FailureCount:    statistics.FailureCount,
		SuccessRate:     statistics.SuccessRate,
		AvgResponseTime: statistics.AvgResponseTimeMs(),
		AvgLatency:      statistics.AvgLatencyMs(),
	}
	
	resultsJSON, _ := json.Marshal(resultsJSONData)
	statsJSON, _ := json.Marshal(statsJSONData)
	data.ResultsJSON = template.JS(resultsJSON)
	data.StatisticsJSON = template.JS(statsJSON)

	t, err := template.New("dashboard").Parse(tmpl)
	if err != nil {
		return fmt.Sprintf("<html><body>Error: %v</body></html>", err)
	}

	var buf strings.Builder
	if err := t.Execute(&buf, data); err != nil {
		return fmt.Sprintf("<html><body>Error: %v</body></html>", err)
	}

	return buf.String()
}
