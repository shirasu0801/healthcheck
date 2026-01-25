package config

import "time"

// Config アプリケーションの設定を保持する構造体
type Config struct {
	Timeout      time.Duration // タイムアウト時間（デフォルト: 30秒）
	Concurrency  int           // 並列度（デフォルト: 10）
	Retries      int           // リトライ回数（デフォルト: 3）
	MaxLatency   time.Duration // 最大レイテンシ（30秒）
	DomainRate   int           // 同一ドメインごとのレート制限（リクエスト/秒）
	GlobalRate   int           // 全体的なレート制限（リクエスト/秒）
	NoColor      bool          // カラー出力を無効化
	Verbose      bool          // 詳細ログを出力
	Insecure     bool          // SSL証明書の検証をスキップ
}

// DefaultConfig デフォルト設定を返す
func DefaultConfig() *Config {
	return &Config{
		Timeout:     30 * time.Second,
		Concurrency: 10,
		Retries:     3,
		MaxLatency:  30 * time.Second,
		DomainRate:  5,  // 1秒間に最大5リクエスト
		GlobalRate:  50, // 1秒間に最大50リクエスト
		NoColor:     false,
		Verbose:     false,
		Insecure:    false,
	}
}
