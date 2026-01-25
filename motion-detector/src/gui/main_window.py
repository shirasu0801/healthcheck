"""PySideメインウィンドウモジュール"""
import sys
import cv2
import numpy as np
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLabel, QPushButton, QSlider, QComboBox,
                               QCheckBox, QTextEdit, QGroupBox, QSpinBox, QDoubleSpinBox)
from PySide6.QtCore import Qt, QTimer, Signal, QThread, QRect
from PySide6.QtGui import QImage, QPixmap, QPainter, QPen, QColor
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class VideoThread(QThread):
    """ビデオ処理スレッド"""
    frame_ready = Signal(np.ndarray)
    detection_occurred = Signal(object, list, np.ndarray)  # method, bboxes, result_img
    
    def __init__(self, camera_manager, motion_detector, ai_detector, config):
        super().__init__()
        self.camera_manager = camera_manager
        self.motion_detector = motion_detector
        self.ai_detector = ai_detector
        self.config = config
        self.running = False
        self.enable_ai = config.get('detection.enable_ai', True)
    
    def run(self):
        """スレッド実行"""
        self.running = True
        while self.running:
            frame = self.camera_manager.read()
            if frame is None:
                continue
            
            # 動体検知
            detected, bboxes, result_img = self.motion_detector.detect(frame)
            
            if detected:
                detection_method = self.motion_detector.method
                detected_objects = []
                
                # AI検知が有効な場合
                if self.enable_ai and self.ai_detector is not None:
                    ai_bboxes, ai_classes, ai_scores = self.ai_detector.detect(frame)
                    if ai_bboxes:
                        detected_objects = ai_classes
                        # AI検知結果を結果画像に描画
                        for (x, y, w, h), cls, score in zip(ai_bboxes, ai_classes, ai_scores):
                            if len(result_img.shape) == 2:
                                result_img = cv2.cvtColor(result_img, cv2.COLOR_GRAY2BGR)
                            cv2.rectangle(result_img, (x, y), (x + w, y + h), (255, 0, 0), 2)
                            cv2.putText(result_img, f"{cls}: {score:.2f}", (x, y - 10),
                                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                        detection_method = "ai"
                
                self.detection_occurred.emit(detection_method, detected_objects, result_img)
            
            # フレームを送信
            self.frame_ready.emit(result_img if detected else frame)
    
    def stop(self):
        """スレッド停止"""
        self.running = False


class MainWindow(QMainWindow):
    """メインウィンドウクラス"""
    
    def __init__(self, camera_manager, motion_detector, ai_detector, 
                 video_recorder, database, email_notifier, config):
        super().__init__()
        
        self.camera_manager = camera_manager
        self.motion_detector = motion_detector
        self.ai_detector = ai_detector
        self.video_recorder = video_recorder
        self.database = database
        self.email_notifier = email_notifier
        self.config = config
        
        self.is_running = False
        self.video_thread: Optional[VideoThread] = None
        self.roi_start: Optional[Tuple[int, int]] = None
        self.roi_end: Optional[Tuple[int, int]] = None
        self.drawing_roi = False
        
        self.init_ui()
        self.setup_timers()
    
    def init_ui(self):
        """UIを初期化"""
        self.setWindowTitle("動体検知システム")
        self.setGeometry(100, 100, 1200, 800)
        
        # 中央ウィジェット
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # メインレイアウト
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 左側: 映像表示エリア
        left_layout = QVBoxLayout()
        
        # 映像表示ラベル
        self.video_label = QLabel()
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setText("カメラ映像")
        self.video_label.setStyleSheet("border: 2px solid gray; background-color: black;")
        self.video_label.mousePressEvent = self.on_video_label_clicked
        self.video_label.mouseMoveEvent = self.on_video_label_move
        self.video_label.mouseReleaseEvent = self.on_video_label_release
        left_layout.addWidget(self.video_label)
        
        # コントロールボタン
        control_layout = QHBoxLayout()
        self.start_button = QPushButton("開始")
        self.start_button.clicked.connect(self.toggle_detection)
        control_layout.addWidget(self.start_button)
        
        self.reset_bg_button = QPushButton("背景リセット")
        self.reset_bg_button.clicked.connect(self.reset_background)
        control_layout.addWidget(self.reset_bg_button)
        
        left_layout.addLayout(control_layout)
        main_layout.addLayout(left_layout)
        
        # 右側: 設定パネル
        right_layout = QVBoxLayout()
        
        # 検知設定
        detection_group = QGroupBox("検知設定")
        detection_layout = QVBoxLayout()
        
        # 検知方法
        detection_layout.addWidget(QLabel("検知方法:"))
        self.method_combo = QComboBox()
        self.method_combo.addItems(["frame_diff", "background_subtraction"])
        self.method_combo.currentTextChanged.connect(self.on_method_changed)
        detection_layout.addWidget(self.method_combo)
        
        # 感度調整
        detection_layout.addWidget(QLabel("感度:"))
        self.sensitivity_slider = QSlider(Qt.Horizontal)
        self.sensitivity_slider.setMinimum(0)
        self.sensitivity_slider.setMaximum(100)
        self.sensitivity_slider.setValue(int(self.config.get('detection.sensitivity', 0.3) * 100))
        self.sensitivity_slider.valueChanged.connect(self.on_sensitivity_changed)
        detection_layout.addWidget(self.sensitivity_slider)
        
        # AI検知有効/無効
        self.ai_checkbox = QCheckBox("AI検知を有効化")
        self.ai_checkbox.setChecked(self.config.get('detection.enable_ai', True))
        self.ai_checkbox.stateChanged.connect(self.on_ai_toggled)
        detection_layout.addWidget(self.ai_checkbox)
        
        detection_group.setLayout(detection_layout)
        right_layout.addWidget(detection_group)
        
        # 録画設定
        recording_group = QGroupBox("録画設定")
        recording_layout = QVBoxLayout()
        
        self.recording_checkbox = QCheckBox("録画を有効化")
        self.recording_checkbox.setChecked(self.config.get('recording.enabled', True))
        recording_layout.addWidget(self.recording_checkbox)
        
        recording_group.setLayout(recording_layout)
        right_layout.addWidget(recording_group)
        
        # 通知設定
        notification_group = QGroupBox("通知設定")
        notification_layout = QVBoxLayout()
        
        self.notification_checkbox = QCheckBox("メール通知を有効化")
        self.notification_checkbox.setChecked(self.config.get('notification.enabled', True))
        notification_layout.addWidget(self.notification_checkbox)
        
        notification_group.setLayout(notification_layout)
        right_layout.addWidget(notification_group)
        
        # 統計情報
        stats_group = QGroupBox("統計情報")
        stats_layout = QVBoxLayout()
        
        self.stats_label = QLabel("検知回数: 0\n最新検知: なし")
        stats_layout.addWidget(self.stats_label)
        
        stats_group.setLayout(stats_layout)
        right_layout.addWidget(stats_group)
        
        # ログ表示
        log_group = QGroupBox("検知ログ")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        log_layout.addWidget(self.log_text)
        
        log_group.setLayout(log_layout)
        right_layout.addWidget(log_group)
        
        right_layout.addStretch()
        main_layout.addLayout(right_layout)
    
    def setup_timers(self):
        """タイマーを設定"""
        # 統計情報更新タイマー
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_statistics)
        self.stats_timer.start(5000)  # 5秒ごとに更新
    
    def on_video_label_clicked(self, event):
        """映像ラベルのクリックイベント（ROI設定開始）"""
        if not self.is_running:
            return
        
        x = event.position().x()
        y = event.position().y()
        self.roi_start = (int(x), int(y))
        self.drawing_roi = True
    
    def on_video_label_move(self, event):
        """映像ラベルのマウス移動イベント（ROI描画中）"""
        if not self.drawing_roi or self.roi_start is None:
            return
        
        x = int(event.position().x())
        y = int(event.position().y())
        self.roi_end = (x, y)
        # 再描画をトリガー（実際の実装では別の方法を使用）
    
    def on_video_label_release(self, event):
        """映像ラベルのリリースイベント（ROI設定完了）"""
        if not self.drawing_roi or self.roi_start is None:
            return
        
        x = int(event.position().x())
        y = int(event.position().y())
        self.roi_end = (x, y)
        
        # ROIを設定
        x1, y1 = self.roi_start
        x2, y2 = self.roi_end
        x_min, x_max = min(x1, x2), max(x1, x2)
        y_min, y_max = min(y1, y2), max(y1, y2)
        
        roi = (x_min, y_min, x_max - x_min, y_max - y_min)
        self.motion_detector.set_roi(roi)
        self.log_text.append(f"ROIを設定しました: {roi}")
        
        self.drawing_roi = False
        self.roi_start = None
        self.roi_end = None
    
    def toggle_detection(self):
        """検知の開始/停止"""
        if not self.is_running:
            # 開始
            if not self.camera_manager.is_available():
                if not self.camera_manager.open():
                    self.log_text.append("エラー: カメラを開けませんでした")
                    return
            
            self.video_thread = VideoThread(
                self.camera_manager, self.motion_detector, 
                self.ai_detector, self.config
            )
            self.video_thread.frame_ready.connect(self.update_frame)
            self.video_thread.detection_occurred.connect(self.on_detection)
            self.video_thread.start()
            
            self.is_running = True
            self.start_button.setText("停止")
            self.log_text.append("検知を開始しました")
        else:
            # 停止
            if self.video_thread:
                self.video_thread.stop()
                self.video_thread.wait()
            
            self.camera_manager.release()
            self.is_running = False
            self.start_button.setText("開始")
            self.log_text.append("検知を停止しました")
    
    def update_frame(self, frame: np.ndarray):
        """フレームを更新"""
        if len(frame.shape) == 2:
            # グレースケール
            height, width = frame.shape
            q_image = QImage(frame.data, width, height, QImage.Format.Format_Grayscale8)
        else:
            # BGR
            height, width, channel = frame.shape
            bytes_per_line = 3 * width
            q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format.Format_BGR888)
        
        pixmap = QPixmap.fromImage(q_image)
        scaled_pixmap = pixmap.scaled(
            self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.video_label.setPixmap(scaled_pixmap)
    
    def on_detection(self, method: str, detected_objects: list, result_img: np.ndarray):
        """検知イベントハンドラ"""
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] 検知: {method}"
        
        if detected_objects:
            log_msg += f" - {', '.join(detected_objects)}"
        
        self.log_text.append(log_msg)
        
        # データベースに記録
        self.database.add_detection(
            detection_method=method,
            detected_objects=detected_objects if detected_objects else None,
            bbox_count=len(detected_objects) if detected_objects else 0
        )
        
        # 録画
        video_path = None
        if self.recording_checkbox.isChecked() and self.video_recorder:
            video_path = self.video_recorder.save_detection(result_img)
            if video_path:
                self.database.add_detection(
                    detection_method=method,
                    detected_objects=detected_objects if detected_objects else None,
                    video_path=video_path
                )
        
        # メール通知
        if self.notification_checkbox.isChecked() and self.email_notifier:
            self.email_notifier.send_detection_notification(
                detection_method=method,
                detected_objects=detected_objects if detected_objects else None,
                video_path=video_path
            )
    
    def on_method_changed(self, method: str):
        """検知方法変更"""
        self.motion_detector.method = method
        if method == "background_subtraction":
            self.motion_detector.background_subtractor = cv2.createBackgroundSubtractorMOG2(
                history=500, varThreshold=50, detectShadows=True
            )
        self.log_text.append(f"検知方法を変更しました: {method}")
    
    def on_sensitivity_changed(self, value: int):
        """感度変更"""
        sensitivity = value / 100.0
        self.motion_detector.set_sensitivity(sensitivity)
    
    def on_ai_toggled(self, checked: bool):
        """AI検知有効/無効"""
        if self.video_thread:
            self.video_thread.enable_ai = checked
        self.log_text.append(f"AI検知を{'有効' if checked else '無効'}にしました")
    
    def reset_background(self):
        """背景をリセット"""
        self.motion_detector.reset_background()
        self.log_text.append("背景モデルをリセットしました")
    
    def update_statistics(self):
        """統計情報を更新"""
        stats = self.database.get_statistics()
        stats_text = f"検知回数: {stats['total']}\n"
        if stats['latest_detection']:
            stats_text += f"最新検知: {stats['latest_detection']}"
        else:
            stats_text += "最新検知: なし"
        self.stats_label.setText(stats_text)
    
    def closeEvent(self, event):
        """ウィンドウ閉鎖イベント"""
        if self.is_running:
            self.toggle_detection()
        self.camera_manager.release()
        event.accept()
