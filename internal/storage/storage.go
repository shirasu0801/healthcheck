package storage

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"time"

	"healthcheck/internal/checker"
	"healthcheck/internal/stats"
)

// SaveResultsJSON JSON形式で結果を保存
func SaveResultsJSON(results []*checker.CheckResult, statistics *stats.Statistics, outputPath string) error {
	data := map[string]interface{}{
		"timestamp":  time.Now().Format(time.RFC3339),
		"results":    results,
		"statistics": statistics,
	}

	jsonData, err := json.MarshalIndent(data, "", "  ")
	if err != nil {
		return fmt.Errorf("failed to marshal JSON: %w", err)
	}

	// ディレクトリが存在しない場合は作成
	dir := filepath.Dir(outputPath)
	if dir != "." && dir != "" {
		if err := os.MkdirAll(dir, 0755); err != nil {
			return fmt.Errorf("failed to create directory: %w", err)
		}
	}

	if err := os.WriteFile(outputPath, jsonData, 0644); err != nil {
		return fmt.Errorf("failed to write file: %w", err)
	}

	return nil
}

// SaveResultsCSV CSV形式で結果を保存
func SaveResultsCSV(results []*checker.CheckResult, outputPath string) error {
	// ディレクトリが存在しない場合は作成
	dir := filepath.Dir(outputPath)
	if dir != "." && dir != "" {
		if err := os.MkdirAll(dir, 0755); err != nil {
			return fmt.Errorf("failed to create directory: %w", err)
		}
	}

	file, err := os.Create(outputPath)
	if err != nil {
		return fmt.Errorf("failed to create file: %w", err)
	}
	defer file.Close()

	writer := csv.NewWriter(file)
	defer writer.Flush()

	// ヘッダーを書き込み
	headers := []string{"URL", "Status Code", "Success", "Response Time (ms)", "Latency (ms)", "Error", "Error Message", "Timestamp"}
	if err := writer.Write(headers); err != nil {
		return fmt.Errorf("failed to write header: %w", err)
	}

	// データを書き込み
	for _, result := range results {
		row := []string{
			result.URL,
			fmt.Sprintf("%d", result.StatusCode),
			fmt.Sprintf("%t", result.Success),
			fmt.Sprintf("%.2f", result.ResponseTimeMs()),
			fmt.Sprintf("%.2f", result.LatencyMs()),
			result.Error,
			result.ErrorMessage,
			result.Timestamp.Format(time.RFC3339),
		}
		if err := writer.Write(row); err != nil {
			return fmt.Errorf("failed to write row: %w", err)
		}
	}

	return nil
}

// SaveHistory 履歴を保存（タイムスタンプ付きファイル名）
func SaveHistory(results []*checker.CheckResult, statistics *stats.Statistics) (string, error) {
	resultsDir := "results"
	if err := os.MkdirAll(resultsDir, 0755); err != nil {
		return "", fmt.Errorf("failed to create results directory: %w", err)
	}

	timestamp := time.Now().Format("20060102_150405")
	filename := fmt.Sprintf("results_%s.json", timestamp)
	filepath := filepath.Join(resultsDir, filename)

	if err := SaveResultsJSON(results, statistics, filepath); err != nil {
		return "", err
	}

	// 最新10件のみ保持
	if err := cleanupOldResults(resultsDir, 10); err != nil {
		// エラーは無視（ログに記録するだけ）
		fmt.Printf("Warning: failed to cleanup old results: %v\n", err)
	}

	return filepath, nil
}

// cleanupOldResults 古い結果ファイルを削除（最新N件のみ保持）
func cleanupOldResults(resultsDir string, keepCount int) error {
	files, err := os.ReadDir(resultsDir)
	if err != nil {
		return err
	}

	// ファイルを更新日時でソート
	type fileInfo struct {
		name    string
		modTime time.Time
	}

	var fileInfos []fileInfo
	for _, file := range files {
		if file.IsDir() {
			continue
		}
		info, err := file.Info()
		if err != nil {
			continue
		}
		fileInfos = append(fileInfos, fileInfo{
			name:    file.Name(),
			modTime: info.ModTime(),
		})
	}

	// 更新日時でソート（新しい順）
	for i := 0; i < len(fileInfos)-1; i++ {
		for j := i + 1; j < len(fileInfos); j++ {
			if fileInfos[i].modTime.Before(fileInfos[j].modTime) {
				fileInfos[i], fileInfos[j] = fileInfos[j], fileInfos[i]
			}
		}
	}

	// 古いファイルを削除
	if len(fileInfos) > keepCount {
		for i := keepCount; i < len(fileInfos); i++ {
			filepath := filepath.Join(resultsDir, fileInfos[i].name)
			if err := os.Remove(filepath); err != nil {
				return err
			}
		}
	}

	return nil
}

// LoadHistory 過去の結果を読み込み
func LoadHistory(resultsDir string) ([]map[string]interface{}, error) {
	files, err := os.ReadDir(resultsDir)
	if err != nil {
		if os.IsNotExist(err) {
			return []map[string]interface{}{}, nil
		}
		return nil, err
	}

	var history []map[string]interface{}

	for _, file := range files {
		if file.IsDir() {
			continue
		}
		if filepath.Ext(file.Name()) != ".json" {
			continue
		}

		filepath := filepath.Join(resultsDir, file.Name())
		data, err := os.ReadFile(filepath)
		if err != nil {
			continue
		}

		var result map[string]interface{}
		if err := json.Unmarshal(data, &result); err != nil {
			continue
		}

		history = append(history, result)
	}

	return history, nil
}
