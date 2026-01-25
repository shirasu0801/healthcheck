package stats

import "time"

// Statistics 統計情報
type Statistics struct {
	TotalRequests   int           `json:"total_requests"`
	SuccessCount    int           `json:"success_count"`
	FailureCount    int           `json:"failure_count"`
	SuccessRate     float64       `json:"success_rate"`
	AvgResponseTime time.Duration `json:"avg_response_time_ms"`
	MinResponseTime time.Duration `json:"min_response_time_ms"`
	MaxResponseTime time.Duration `json:"max_response_time_ms"`
	AvgLatency      time.Duration `json:"avg_latency_ms"`
	MinLatency      time.Duration `json:"min_latency_ms"`
	MaxLatency      time.Duration `json:"max_latency_ms"`
	TotalDuration   time.Duration `json:"total_duration_ms"`
}

// AvgResponseTimeMs 平均応答時間をミリ秒で返す
func (s *Statistics) AvgResponseTimeMs() float64 {
	return float64(s.AvgResponseTime.Nanoseconds()) / 1e6
}

// AvgLatencyMs 平均レイテンシをミリ秒で返す
func (s *Statistics) AvgLatencyMs() float64 {
	return float64(s.AvgLatency.Nanoseconds()) / 1e6
}
