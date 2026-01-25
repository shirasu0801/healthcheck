package stats

import (
	"healthcheck/internal/checker"
	"time"
)

// CalculateStatistics チェック結果から統計情報を計算
func CalculateStatistics(results []*checker.CheckResult, totalDuration time.Duration) *Statistics {
	if len(results) == 0 {
		return &Statistics{}
	}

	stats := &Statistics{
		TotalRequests: len(results),
		TotalDuration: totalDuration,
	}

	var totalResponseTime time.Duration
	var totalLatency time.Duration
	var successResponseTimes []time.Duration
	var successLatencies []time.Duration

	for _, result := range results {
		if result.Success {
			stats.SuccessCount++
			successResponseTimes = append(successResponseTimes, result.ResponseTime)
			successLatencies = append(successLatencies, result.Latency)
			totalResponseTime += result.ResponseTime
			totalLatency += result.Latency
		} else {
			stats.FailureCount++
		}
	}

	// 成功率の計算
	if stats.TotalRequests > 0 {
		stats.SuccessRate = float64(stats.SuccessCount) / float64(stats.TotalRequests) * 100
	}

	// 応答時間の統計（成功したリクエストのみ）
	if len(successResponseTimes) > 0 {
		stats.AvgResponseTime = totalResponseTime / time.Duration(len(successResponseTimes))
		stats.MinResponseTime = successResponseTimes[0]
		stats.MaxResponseTime = successResponseTimes[0]

		for _, rt := range successResponseTimes {
			if rt < stats.MinResponseTime {
				stats.MinResponseTime = rt
			}
			if rt > stats.MaxResponseTime {
				stats.MaxResponseTime = rt
			}
		}
	}

	// レイテンシの統計（成功したリクエストのみ）
	if len(successLatencies) > 0 {
		stats.AvgLatency = totalLatency / time.Duration(len(successLatencies))
		stats.MinLatency = successLatencies[0]
		stats.MaxLatency = successLatencies[0]

		for _, lat := range successLatencies {
			if lat < stats.MinLatency {
				stats.MinLatency = lat
			}
			if lat > stats.MaxLatency {
				stats.MaxLatency = lat
			}
		}
	}

	return stats
}
