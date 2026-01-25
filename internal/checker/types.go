package checker

import "time"

// CheckResult 単一URLのチェック結果
type CheckResult struct {
	URL          string        `json:"url"`
	StatusCode   int           `json:"status_code"`
	ResponseTime time.Duration `json:"response_time_ms"`
	Latency      time.Duration `json:"latency_ms"` // DNS解決から応答までの時間
	Error        string        `json:"error,omitempty"`
	ErrorMessage string        `json:"error_message,omitempty"`
	Timestamp    time.Time     `json:"timestamp"`
	Success      bool          `json:"success"`
}

// ResponseTimeMs 応答時間をミリ秒で返す
func (r *CheckResult) ResponseTimeMs() float64 {
	return float64(r.ResponseTime.Nanoseconds()) / 1e6
}

// LatencyMs レイテンシをミリ秒で返す
func (r *CheckResult) LatencyMs() float64 {
	return float64(r.Latency.Nanoseconds()) / 1e6
}
