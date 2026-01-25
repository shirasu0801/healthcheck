#!/usr/bin/env python3
"""動体検知アプリケーション メインエントリーポイント"""
import sys
import os
import logging
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication
from src.camera.camera_manager import CameraManager
from src.detection.motion_detector import MotionDetector
from src.detection.ai_detector import AIDetector
from src.recording.video_recorder import VideoRecorder
from src.storage.database import Database
from src.notification.email_notifier import EmailNotifier
from src.utils.config_loader import ConfigLoader
from src.gui.main_window import MainWindow


def setup_logging():
    """ロギングを設定"""
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / "motion_detector.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    """メイン関数"""
    # ロギング設定
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("動体検知アプリケーションを起動します")
    
    # 設定ファイルを読み込み
    config_path = project_root / "config.json"
    if not config_path.exists():
        logger.error(f"設定ファイルが見つかりません: {config_path}")
        logger.info("config.jsonファイルを作成してください")
        return 1
    
    config = ConfigLoader(str(config_path))
    
    # カメラ管理を初期化
    camera_config = config.get('camera', {})
    camera_manager = CameraManager(
        device_id=camera_config.get('device_id', 0),
        width=camera_config.get('width', 640),
        height=camera_config.get('height', 480),
        fps=camera_config.get('fps', 30),
        grayscale=camera_config.get('grayscale', True)
    )
    
    # 動体検知エンジンを初期化
    detection_config = config.get('detection', {})
    motion_detector = MotionDetector(
        method=detection_config.get('method', 'background_subtraction'),
        sensitivity=detection_config.get('sensitivity', 0.3),
        min_area=detection_config.get('min_area', 500),
        roi=detection_config.get('roi')
    )
    
    # AI検知を初期化（オプション）
    ai_detector = None
    if detection_config.get('enable_ai', True):
        try:
            ai_detector = AIDetector(
                confidence_threshold=detection_config.get('ai_confidence_threshold', 0.5),
                target_classes=['person', 'car', 'bicycle', 'motorcycle', 'bus', 'truck']
            )
            logger.info("AI検知モジュールを初期化しました")
        except Exception as e:
            logger.warning(f"AI検知モジュールの初期化に失敗しました: {e}")
            logger.info("AI検知なしで続行します")
    
    # 録画機能を初期化
    recording_config = config.get('recording', {})
    video_recorder = VideoRecorder(
        pre_seconds=recording_config.get('pre_seconds', 5),
        post_seconds=recording_config.get('post_seconds', 5),
        output_dir=str(project_root / recording_config.get('output_dir', 'recordings')),
        fps=camera_config.get('fps', 30),
        codec=recording_config.get('codec', 'mp4v')
    )
    
    # データベースを初期化
    database_config = config.get('database', {})
    database = Database(
        db_path=str(project_root / database_config.get('path', 'data/detections.db'))
    )
    
    # メール通知を初期化（オプション）
    email_notifier = None
    notification_config = config.get('notification', {})
    if notification_config.get('enabled', False):
        email_config = notification_config.get('email', {})
        try:
            email_notifier = EmailNotifier(
                smtp_server=email_config.get('smtp_server', 'smtp.gmail.com'),
                smtp_port=email_config.get('smtp_port', 587),
                username=email_config.get('username', ''),
                password=email_config.get('password', ''),
                to_email=email_config.get('to', '')
            )
            logger.info("メール通知機能を初期化しました")
        except Exception as e:
            logger.warning(f"メール通知機能の初期化に失敗しました: {e}")
            logger.info("メール通知なしで続行します")
    
    # GUIアプリケーションを作成
    app = QApplication(sys.argv)
    
    # メインウィンドウを作成
    window = MainWindow(
        camera_manager=camera_manager,
        motion_detector=motion_detector,
        ai_detector=ai_detector,
        video_recorder=video_recorder,
        database=database,
        email_notifier=email_notifier,
        config=config.config
    )
    
    window.show()
    
    logger.info("GUIアプリケーションを起動しました")
    
    # イベントループを開始
    try:
        exit_code = app.exec()
        logger.info("アプリケーションを終了します")
        return exit_code
    except KeyboardInterrupt:
        logger.info("ユーザーによって中断されました")
        return 0
    except Exception as e:
        logger.error(f"アプリケーション実行中にエラーが発生しました: {e}", exc_info=True)
        return 1
    finally:
        # クリーンアップ
        camera_manager.release()


if __name__ == "__main__":
    sys.exit(main())
