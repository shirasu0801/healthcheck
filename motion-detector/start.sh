#!/bin/bash
# 動体検知アプリケーション起動スクリプト

# プロジェクトディレクトリに移動
cd "$(dirname "$0")"

# Python仮想環境をアクティベート（使用している場合）
# source venv/bin/activate

# アプリケーションを起動
python3 main.py
