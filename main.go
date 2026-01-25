package main

import (
	"flag"
	"fmt"
	"os"

	"healthcheck/internal/config"
	"healthcheck/internal/web"
)

func main() {
	var port string
	flag.StringVar(&port, "port", "8080", "サーバーのポート番号")
	flag.StringVar(&port, "p", "8080", "サーバーのポート番号（短縮形）")
	flag.Parse()

	cfg := config.DefaultConfig()
	server := web.NewServer(cfg)

	fmt.Println("=== Health Check Tool ===")
	fmt.Println("ブラウザで http://localhost:" + port + " を開いてください")
	fmt.Println()

	if err := server.Start(port); err != nil {
		fmt.Fprintf(os.Stderr, "サーバー起動エラー: %v\n", err)
		os.Exit(1)
	}
}
