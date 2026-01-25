# 動体検知アプリケーション

Raspberry Pi用のリアルタイム動体検知システムです。AIによるオブジェクト検知、自動録画、メール通知機能を備えています。

## 機能

- 📹 リアルタイム動体検知（フレーム差分法、背景差分法）
- 🤖 AI検知（TensorFlow + COCOモデル）
- 🎥 自動録画（検知前後5秒）
- 📧 メール通知
- 💾 SQLiteデータベースによるログ記録
- 🖥️ PySide6によるGUI

## 必要なハードウェア

- **Raspberry Pi**: Raspberry Pi 4 または 5
- **カメラ**: Raspberry Pi Camera Module v2/v3 または USBウェブカメラ
- **ストレージ**: microSDカード（32GB以上推奨）
- **電源**: 適切な電源アダプター
- **ネットワーク**: インターネット接続（初期セットアップ時）

## 必要なソフトウェア環境

### Raspberry Pi OSのセットアップ

1. Raspberry Pi OSをインストール（最新版推奨）

2. カメラを有効化:
   ```bash
   sudo raspi-config
   # → Interface Options → Camera → Enable
   ```

3. システムを更新:
   ```bash
   sudo apt update
   sudo apt upgrade -y
   ```

### Python環境の準備

```bash
# Python 3.8以上がインストールされているか確認
python3 --version

# 必要なパッケージをインストール
sudo apt install python3-pip python3-venv -y
```

## インストール手順

### ステップ1: プロジェクトの配置

プロジェクトファイルをRaspberry Piに配置します。

```bash
# 例: /home/pi/motion-detector に配置
cd /home/pi
# git clone またはファイル転送で配置
```

### ステップ2: 依存関係のインストール

```bash
cd /home/pi/motion-detector

# 仮想環境を作成（推奨）
python3 -m venv venv
source venv/bin/activate

# 依存関係をインストール
pip install -r requirements.txt
```

**注意事項:**
- TensorFlowのインストールには時間がかかります
- Raspberry Pi 4の場合、1時間以上かかる場合があります
- メモリ不足エラーが発生する場合は、スワップファイルを増やしてください

### ステップ3: カメラの確認

#### USBカメラの場合
```bash
# カメラが認識されているか確認
lsusb
```

#### Raspberry Pi Camera Moduleの場合
```bash
# カメラをテスト
libcamera-hello --list-cameras
# または
raspistill -o test.jpg
```

## 設定ファイルの編集

`config.json` を編集して、環境に合わせた設定を行います。

```bash
nano config.json
```

### 必須設定項目

#### カメラ設定
```json
{
  "camera": {
    "device_id": 0,        // USBカメラの場合は0、Raspberry Pi Cameraは通常0
    "width": 640,          // 解像度（パフォーマンスに影響）
    "height": 480,
    "fps": 30,             // フレームレート
    "grayscale": true      // グレースケール推奨（高速化）
  }
}
```

#### 検知設定
```json
{
  "detection": {
    "method": "background_subtraction",  // "frame_diff" または "background_subtraction"
    "sensitivity": 0.3,                  // 0.0-1.0（低いほど敏感）
    "min_area": 500,                     // 検知する最小面積（ピクセル）
    "enable_ai": true,                   // AI検知を有効化
    "ai_confidence_threshold": 0.5       // AI検知の信頼度しきい値
  }
}
```

#### メール通知設定（使用する場合）

**Gmailを使用する場合:**
1. Googleアカウントで2段階認証を有効化
2. アプリパスワードを生成: https://myaccount.google.com/apppasswords
3. 生成されたパスワードを `config.json` に設定

```json
{
  "notification": {
    "enabled": true,
    "email": {
      "smtp_server": "smtp.gmail.com",
      "smtp_port": 587,
      "username": "your_email@gmail.com",
      "password": "your_app_password",  // Gmailの場合はアプリパスワード
      "to": "recipient@example.com"
    }
  }
}
```

**その他のメールプロバイダー:**
- Outlook/Hotmail: `smtp-mail.outlook.com`, ポート 587
- Yahoo: `smtp.mail.yahoo.com`, ポート 587
- カスタムSMTPサーバー: プロバイダーの設定を参照

## アプリケーションの起動

### 方法1: 手動起動（テスト用）

```bash
cd /home/pi/motion-detector
source venv/bin/activate  # 仮想環境を使用している場合
python3 main.py
```

GUIウィンドウが表示され、アプリケーションが起動します。

### 方法2: 自動起動設定（本番環境）

```bash
cd /home/pi/motion-detector

# スクリプトに実行権限を付与
chmod +x install_service.sh
chmod +x start.sh

# サービスをインストール
./install_service.sh

# サービスを起動
sudo systemctl start motion-detector

# 状態確認
sudo systemctl status motion-detector

# ログ確認（リアルタイム）
sudo journalctl -u motion-detector -f
```

**サービス管理コマンド:**
```bash
# サービスを開始
sudo systemctl start motion-detector

# サービスを停止
sudo systemctl stop motion-detector

# サービスを再起動
sudo systemctl restart motion-detector

# サービスの状態確認
sudo systemctl status motion-detector

# 自動起動を有効化
sudo systemctl enable motion-detector

# 自動起動を無効化
sudo systemctl disable motion-detector
```

## GUIアプリケーションの使用方法

### 基本操作

1. **検知の開始**
   - 「開始」ボタンをクリック
   - カメラ映像が表示されます

2. **検知方法の選択**
   - ドロップダウンから選択:
     - `frame_diff`: フレーム差分法（高速、ノイズに弱い）
     - `background_subtraction`: 背景差分法（推奨、照明変化に強い）

3. **感度の調整**
   - スライダーで調整（0-100）
   - 値が低いほど敏感に反応します

4. **AI検知の有効/無効**
   - チェックボックスで切り替え
   - 有効にすると、人や車などのオブジェクトを識別します

5. **ROI（監視領域）の設定**
   - 映像表示エリアでマウスドラッグして矩形を選択
   - 選択した領域のみを監視対象にします
   - 全体を監視する場合は、設定をリセット

6. **背景のリセット**
   - カメラ位置や照明が変わった場合
   - 「背景リセット」ボタンをクリック
   - 新しい背景モデルが構築されます

7. **録画の有効/無効**
   - チェックボックスで切り替え
   - 有効にすると、検知時に自動録画されます

8. **メール通知の有効/無効**
   - チェックボックスで切り替え
   - 有効にすると、検知時にメール通知が送信されます

9. **検知ログの確認**
   - 右側の「検知ログ」エリアで検知履歴を確認
   - 統計情報で検知回数などを確認

## ファイルの確認

### 録画ファイル
```bash
# 録画ファイル一覧
ls -lh recordings/

# ファイルサイズの合計
du -sh recordings/

# 古いファイルを削除（30日以上前）
find recordings/ -name "*.mp4" -mtime +30 -delete
```

### データベース
```bash
# SQLiteデータベースを確認（オプション）
sqlite3 data/detections.db

# テーブル一覧
.tables

# 最新10件の検知履歴を表示
SELECT * FROM detections ORDER BY timestamp DESC LIMIT 10;

# 検知方法別の集計
SELECT detection_method, COUNT(*) FROM detections GROUP BY detection_method;

# 終了
.quit
```

### ログファイル
```bash
# 最新のログを確認
tail -n 50 logs/motion_detector.log

# エラーのみ確認
grep ERROR logs/motion_detector.log

# リアルタイムでログを監視
tail -f logs/motion_detector.log
```

## トラブルシューティング

### カメラが開けない

```bash
# カメラが使用中でないか確認
sudo lsof | grep video

# カメラデバイスを確認
ls -l /dev/video*

# config.jsonのdevice_idを変更してみる
# USBカメラが複数接続されている場合、device_idを1, 2...と変更
```

**解決方法:**
- 他のアプリケーションがカメラを使用していないか確認
- カメラケーブルの接続を確認
- `device_id` を変更して試す

### AI検知が動作しない

```bash
# TensorFlowが正しくインストールされているか確認
python3 -c "import tensorflow as tf; print(tf.__version__)"

# インターネット接続を確認（モデルダウンロードに必要）
ping google.com
```

**解決方法:**
- TensorFlowがインストールされているか確認
- インターネット接続を確認（初回起動時にモデルをダウンロード）
- ログファイルでエラーを確認

### メール通知が送信されない

```bash
# SMTP接続をテスト
python3 -c "
import smtplib
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('your_email@gmail.com', 'your_password')
print('接続成功')
"
```

**解決方法:**
- SMTP設定が正しいか確認
- Gmailの場合はアプリパスワードを使用
- ファイアウォールでSMTPポートがブロックされていないか確認
- ログファイルでエラーメッセージを確認

### パフォーマンスが低い

**解決方法:**
- `config.json` で解像度を下げる（640x480 → 320x240）
- `grayscale: true` を確認
- AI検知を無効化（`enable_ai: false`）
- 不要なプロセスを停止
- スワップファイルを増やす

```bash
# スワップファイルを増やす
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# CONF_SWAPSIZE=100 を CONF_SWAPSIZE=2048 に変更
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

### メモリ不足エラー

```bash
# メモリ使用状況を確認
free -h

# スワップファイルを確認
swapon --show
```

**解決方法:**
- スワップファイルを増やす（上記参照）
- 解像度を下げる
- AI検知を無効化

## 日常的な運用

### 自動起動の確認

```bash
# サービスが有効になっているか確認
sudo systemctl is-enabled motion-detector

# 起動時に自動開始されるように設定
sudo systemctl enable motion-detector
```

### ログの定期確認

```bash
# 最新のログを確認
tail -n 50 logs/motion_detector.log

# エラーのみ確認
grep ERROR logs/motion_detector.log

# 検知イベントの確認
grep "検知" logs/motion_detector.log
```

### ディスク容量の管理

```bash
# 録画ファイルの容量を確認
du -sh recordings/

# 古いファイルを削除（30日以上前）
find recordings/ -name "*.mp4" -mtime +30 -delete

# データベースの古いレコードを削除（アプリケーション内で実装）
# または手動で:
sqlite3 data/detections.db "DELETE FROM detections WHERE timestamp < datetime('now', '-30 days');"
```

### 定期メンテナンス

1. **週次:**
   - ログファイルの確認
   - ディスク容量の確認

2. **月次:**
   - 古い録画ファイルの削除
   - データベースのクリーンアップ
   - システム更新の確認

## セキュリティの注意事項

1. **設定ファイルの保護**
   ```bash
   # config.jsonの権限を制限
   chmod 600 config.json
   ```

2. **メールパスワード**
   - `config.json` にメールパスワードが含まれます
   - ファイルの権限を適切に設定してください
   - 必要に応じて暗号化を検討してください

3. **ネットワーク**
   - 必要に応じてファイアウォールを設定
   - SSH接続は鍵認証を使用

## クイックスタートガイド

```bash
# 1. 依存関係インストール
pip install -r requirements.txt

# 2. 設定ファイル編集
nano config.json

# 3. テスト実行
python3 main.py

# 4. 自動起動設定（問題なければ）
./install_service.sh
sudo systemctl start motion-detector
```

## サポート

問題が発生した場合は、以下の情報を含めてお問い合わせください：

- Raspberry PiのモデルとOSバージョン
- カメラの種類
- エラーメッセージ（ログファイルから）
- 設定ファイルの内容（パスワードは除く）

## ライセンス

MIT License

## 参考資料

詳細な要件定義については `requirements.md` を参照してください。
