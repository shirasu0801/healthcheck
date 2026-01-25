#!/bin/bash
# systemdサービスをインストールするスクリプト

# プロジェクトディレクトリを取得
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_FILE="$PROJECT_DIR/motion-detector.service"
SYSTEMD_DIR="/etc/systemd/system"

# サービスファイル内のパスを更新
sed -i "s|/home/pi/motion-detector|$PROJECT_DIR|g" "$SERVICE_FILE"

# サービスファイルをコピー
sudo cp "$SERVICE_FILE" "$SYSTEMD_DIR/"

# systemdをリロード
sudo systemctl daemon-reload

# サービスを有効化
sudo systemctl enable motion-detector.service

echo "サービスをインストールしました"
echo "起動するには: sudo systemctl start motion-detector"
echo "状態確認: sudo systemctl status motion-detector"
echo "ログ確認: sudo journalctl -u motion-detector -f"
