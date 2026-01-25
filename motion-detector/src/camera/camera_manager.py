"""カメラ入力管理モジュール"""
import cv2
import numpy as np
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class CameraManager:
    """カメラ入力を管理するクラス"""
    
    def __init__(self, device_id: int = 0, width: int = 640, height: int = 480, 
                 fps: int = 30, grayscale: bool = True):
        """
        初期化
        
        Args:
            device_id: カメラデバイスID（0がデフォルト）
            width: 画像幅
            height: 画像高さ
            fps: フレームレート
            grayscale: グレースケール変換を行うか
        """
        self.device_id = device_id
        self.width = width
        self.height = height
        self.fps = fps
        self.grayscale = grayscale
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_opened = False
    
    def open(self) -> bool:
        """
        カメラを開く
        
        Returns:
            成功した場合True
        """
        try:
            self.cap = cv2.VideoCapture(self.device_id)
            
            if not self.cap.isOpened():
                logger.error(f"カメラデバイス {self.device_id} を開けませんでした")
                return False
            
            # カメラ設定
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            
            # Raspberry Pi Camera Module用の設定
            if self.device_id == 0:
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # バッファを最小化
            
            self.is_opened = True
            logger.info(f"カメラを開きました: {self.width}x{self.height}@{self.fps}fps")
            return True
            
        except Exception as e:
            logger.error(f"カメラを開く際にエラーが発生しました: {e}")
            return False
    
    def read(self) -> Optional[np.ndarray]:
        """
        フレームを読み込む
        
        Returns:
            フレーム（BGRまたはグレースケール）、失敗時はNone
        """
        if not self.is_opened or self.cap is None:
            return None
        
        ret, frame = self.cap.read()
        
        if not ret:
            logger.warning("フレームの読み込みに失敗しました")
            return None
        
        # リサイズ
        if frame.shape[1] != self.width or frame.shape[0] != self.height:
            frame = cv2.resize(frame, (self.width, self.height))
        
        # グレースケール変換
        if self.grayscale:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        return frame
    
    def release(self) -> None:
        """カメラを解放する"""
        if self.cap is not None:
            self.cap.release()
            self.is_opened = False
            logger.info("カメラを解放しました")
    
    def __enter__(self):
        """コンテキストマネージャー: 開始"""
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャー: 終了"""
        self.release()
    
    def get_frame_size(self) -> Tuple[int, int]:
        """
        フレームサイズを取得
        
        Returns:
            (幅, 高さ)のタプル
        """
        return (self.width, self.height)
    
    def is_available(self) -> bool:
        """
        カメラが利用可能かチェック
        
        Returns:
            利用可能な場合True
        """
        return self.is_opened and self.cap is not None and self.cap.isOpened()
