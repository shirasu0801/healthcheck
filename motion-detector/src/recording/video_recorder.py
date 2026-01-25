"""録画機能モジュール"""
import cv2
import numpy as np
from typing import List, Optional, Tuple
from datetime import datetime
import os
import logging
from collections import deque

logger = logging.getLogger(__name__)


class VideoRecorder:
    """録画機能クラス"""
    
    def __init__(self, pre_seconds: int = 5, post_seconds: int = 5,
                 output_dir: str = "recordings", fps: int = 30,
                 codec: str = "mp4v"):
        """
        初期化
        
        Args:
            pre_seconds: 検知前の録画秒数
            post_seconds: 検知後の録画秒数
            output_dir: 出力ディレクトリ
            fps: フレームレート
            codec: コーデック（"mp4v" または "XVID"）
        """
        self.pre_seconds = pre_seconds
        self.post_seconds = post_seconds
        self.output_dir = output_dir
        self.fps = fps
        self.codec = codec
        
        # リングバッファ（フレームとタイムスタンプを保存）
        self.frame_buffer: deque = deque(maxlen=pre_seconds * fps)
        self.timestamp_buffer: deque = deque(maxlen=pre_seconds * fps)
        
        # 録画状態
        self.is_recording = False
        self.recording_frames: List[Tuple[np.ndarray, float]] = []
        self.recording_start_time: Optional[float] = None
        
        # 出力ディレクトリを作成
        os.makedirs(output_dir, exist_ok=True)
        
        logger.info(f"録画機能を初期化しました: pre={pre_seconds}s, post={post_seconds}s")
    
    def add_frame(self, frame: np.ndarray) -> None:
        """
        フレームをバッファに追加
        
        Args:
            frame: フレーム（BGRまたはグレースケール）
        """
        import time
        timestamp = time.time()
        
        # バッファに追加（最大サイズを超えると古いフレームが自動削除）
        self.frame_buffer.append(frame.copy())
        self.timestamp_buffer.append(timestamp)
        
        # 録画中の場合はフレームを記録
        if self.is_recording:
            self.recording_frames.append((frame.copy(), timestamp))
    
    def start_recording(self) -> None:
        """録画を開始"""
        import time
        
        if self.is_recording:
            logger.warning("既に録画中です")
            return
        
        self.is_recording = True
        self.recording_frames = []
        self.recording_start_time = time.time()
        
        # バッファ内のフレームを録画フレームに追加
        for frame, timestamp in zip(self.frame_buffer, self.timestamp_buffer):
            self.recording_frames.append((frame.copy(), timestamp))
        
        logger.info("録画を開始しました")
    
    def stop_and_save(self) -> Optional[str]:
        """
        録画を停止してファイルに保存
        
        Returns:
            保存されたファイルパス、失敗時はNone
        """
        if not self.is_recording:
            logger.warning("録画中ではありません")
            return None
        
        import time
        
        # 録画を継続（post_seconds分）
        end_time = time.time()
        target_end_time = self.recording_start_time + self.post_seconds
        
        # 録画フレームが不足している場合は待機（実際の実装では別スレッドで処理）
        # ここでは簡易実装として、現在のフレームを追加
        
        # ファイル名を生成
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"detection_{timestamp_str}.mp4"
        filepath = os.path.join(self.output_dir, filename)
        
        # ビデオライターを作成
        if len(self.recording_frames) == 0:
            logger.warning("録画フレームがありません")
            self.is_recording = False
            return None
        
        # フレームサイズを取得
        first_frame = self.recording_frames[0][0]
        if len(first_frame.shape) == 2:
            height, width = first_frame.shape
            is_color = False
        else:
            height, width = first_frame.shape[:2]
            is_color = True
        
        # コーデックを設定
        fourcc = cv2.VideoWriter_fourcc(*self.codec)
        out = cv2.VideoWriter(filepath, fourcc, self.fps, (width, height), is_color)
        
        if not out.isOpened():
            logger.error(f"ビデオライターを開けませんでした: {filepath}")
            self.is_recording = False
            return None
        
        # フレームを書き込み
        for frame, _ in self.recording_frames:
            # グレースケールの場合はBGRに変換
            if len(frame.shape) == 2:
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            out.write(frame)
        
        out.release()
        self.is_recording = False
        self.recording_frames = []
        
        logger.info(f"録画を保存しました: {filepath}")
        return filepath
    
    def save_detection(self, frame: np.ndarray) -> Optional[str]:
        """
        検知時に録画を開始して保存（簡易版）
        
        Args:
            frame: 検知時のフレーム
            
        Returns:
            保存されたファイルパス、失敗時はNone
        """
        # バッファ内のフレームと現在のフレームを結合
        frames_to_save = []
        
        # バッファ内のフレーム
        for buffered_frame in self.frame_buffer:
            frames_to_save.append(buffered_frame.copy())
        
        # 現在のフレーム
        frames_to_save.append(frame.copy())
        
        # ファイル名を生成
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"detection_{timestamp_str}.mp4"
        filepath = os.path.join(self.output_dir, filename)
        
        if len(frames_to_save) == 0:
            return None
        
        # フレームサイズを取得
        first_frame = frames_to_save[0]
        if len(first_frame.shape) == 2:
            height, width = first_frame.shape
            is_color = False
        else:
            height, width = first_frame.shape[:2]
            is_color = True
        
        # ビデオライターを作成
        fourcc = cv2.VideoWriter_fourcc(*self.codec)
        out = cv2.VideoWriter(filepath, fourcc, self.fps, (width, height), is_color)
        
        if not out.isOpened():
            logger.error(f"ビデオライターを開けませんでした: {filepath}")
            return None
        
        # フレームを書き込み
        for frame_to_save in frames_to_save:
            if len(frame_to_save.shape) == 2:
                frame_to_save = cv2.cvtColor(frame_to_save, cv2.COLOR_GRAY2BGR)
            out.write(frame_to_save)
        
        out.release()
        logger.info(f"検知録画を保存しました: {filepath}")
        return filepath
