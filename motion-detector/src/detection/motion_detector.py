"""動体検知エンジンモジュール"""
import cv2
import numpy as np
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class MotionDetector:
    """動体検知エンジンクラス"""
    
    def __init__(self, method: str = "background_subtraction", 
                 sensitivity: float = 0.3, min_area: int = 500,
                 roi: Optional[Tuple[int, int, int, int]] = None):
        """
        初期化
        
        Args:
            method: 検知方法 ("frame_diff" または "background_subtraction")
            sensitivity: 感度（0.0-1.0）
            min_area: 検知する最小面積（ピクセル）
            roi: 監視領域 (x, y, width, height)、Noneの場合は全体
        """
        self.method = method
        self.sensitivity = sensitivity
        self.min_area = min_area
        self.roi = roi
        
        # フレーム差分用
        self.prev_frame: Optional[np.ndarray] = None
        
        # 背景差分用
        self.background_subtractor = None
        if method == "background_subtraction":
            # MOG2アルゴリズムを使用（適応的背景減算）
            self.background_subtractor = cv2.createBackgroundSubtractorMOG2(
                history=500, varThreshold=50, detectShadows=True
            )
        
        logger.info(f"動体検知エンジンを初期化しました: method={method}, sensitivity={sensitivity}")
    
    def detect(self, frame: np.ndarray) -> Tuple[bool, List[Tuple[int, int, int, int]], np.ndarray]:
        """
        動体を検知する
        
        Args:
            frame: 入力フレーム（グレースケールまたはBGR）
            
        Returns:
            (検知有無, バウンディングボックスリスト, 検知結果画像)のタプル
        """
        if frame is None:
            return False, [], np.zeros((100, 100), dtype=np.uint8)
        
        # ROI適用
        if self.roi is not None:
            x, y, w, h = self.roi
            roi_frame = frame[y:y+h, x:x+w]
        else:
            roi_frame = frame
            x, y = 0, 0
        
        # 検知方法に応じて処理
        if self.method == "frame_diff":
            detected, bboxes, result_img = self._detect_frame_diff(roi_frame)
        elif self.method == "background_subtraction":
            detected, bboxes, result_img = self._detect_background_subtraction(roi_frame)
        else:
            logger.warning(f"未知の検知方法: {self.method}")
            return False, [], frame
        
        # ROI座標を全体座標に変換
        if self.roi is not None:
            bboxes = [(bx + x, by + y, bw, bh) for bx, by, bw, bh in bboxes]
        
        return detected, bboxes, result_img
    
    def _detect_frame_diff(self, frame: np.ndarray) -> Tuple[bool, List[Tuple[int, int, int, int]], np.ndarray]:
        """
        フレーム差分法で検知
        
        Args:
            frame: 入力フレーム
            
        Returns:
            (検知有無, バウンディングボックスリスト, 検知結果画像)
        """
        if self.prev_frame is None:
            self.prev_frame = frame.copy()
            return False, [], frame
        
        # フレーム差分
        diff = cv2.absdiff(frame, self.prev_frame)
        
        # しきい値処理
        threshold = int(255 * self.sensitivity)
        _, thresh = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)
        
        # ノイズ除去
        thresh = self._remove_noise(thresh)
        
        # 輪郭検出
        bboxes = self._find_contours(thresh)
        
        # 結果画像（デバッグ用）
        result_img = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR) if len(frame.shape) == 2 else frame.copy()
        for bx, by, bw, bh in bboxes:
            cv2.rectangle(result_img, (bx, by), (bx + bw, by + bh), (0, 255, 0), 2)
        
        # 前フレームを更新
        self.prev_frame = frame.copy()
        
        detected = len(bboxes) > 0
        return detected, bboxes, result_img
    
    def _detect_background_subtraction(self, frame: np.ndarray) -> Tuple[bool, List[Tuple[int, int, int, int]], np.ndarray]:
        """
        背景差分法で検知
        
        Args:
            frame: 入力フレーム
            
        Returns:
            (検知有無, バウンディングボックスリスト, 検知結果画像)
        """
        if self.background_subtractor is None:
            return False, [], frame
        
        # 背景減算
        fg_mask = self.background_subtractor.apply(frame)
        
        # しきい値調整（感度に応じて）
        threshold = int(255 * (1.0 - self.sensitivity))
        _, fg_mask = cv2.threshold(fg_mask, threshold, 255, cv2.THRESH_BINARY)
        
        # ノイズ除去
        fg_mask = self._remove_noise(fg_mask)
        
        # 輪郭検出
        bboxes = self._find_contours(fg_mask)
        
        # 結果画像（デバッグ用）
        result_img = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR) if len(frame.shape) == 2 else frame.copy()
        for bx, by, bw, bh in bboxes:
            cv2.rectangle(result_img, (bx, by), (bx + bw, by + bh), (0, 255, 0), 2)
        
        detected = len(bboxes) > 0
        return detected, bboxes, result_img
    
    def _remove_noise(self, binary_img: np.ndarray) -> np.ndarray:
        """
        ノイズを除去する
        
        Args:
            binary_img: 2値画像
            
        Returns:
            ノイズ除去後の2値画像
        """
        # ガウシアンブラー
        blurred = cv2.GaussianBlur(binary_img, (5, 5), 0)
        
        # モルフォロジー演算（クロージング）
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        closed = cv2.morphologyEx(blurred, cv2.MORPH_CLOSE, kernel)
        
        # オープニング（小さなノイズを除去）
        opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel)
        
        return opened
    
    def _find_contours(self, binary_img: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        輪郭を検出してバウンディングボックスを取得
        
        Args:
            binary_img: 2値画像
            
        Returns:
            バウンディングボックスリスト [(x, y, width, height), ...]
        """
        contours, _ = cv2.findContours(binary_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        bboxes = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area >= self.min_area:
                x, y, w, h = cv2.boundingRect(contour)
                bboxes.append((x, y, w, h))
        
        return bboxes
    
    def set_roi(self, roi: Optional[Tuple[int, int, int, int]]) -> None:
        """
        ROIを設定する
        
        Args:
            roi: 監視領域 (x, y, width, height)、Noneの場合は全体
        """
        self.roi = roi
        logger.info(f"ROIを設定しました: {roi}")
    
    def set_sensitivity(self, sensitivity: float) -> None:
        """
        感度を設定する
        
        Args:
            sensitivity: 感度（0.0-1.0）
        """
        self.sensitivity = max(0.0, min(1.0, sensitivity))
        logger.info(f"感度を設定しました: {self.sensitivity}")
    
    def reset_background(self) -> None:
        """背景モデルをリセット（背景差分法の場合）"""
        if self.method == "background_subtraction" and self.background_subtractor is not None:
            # 新しい背景減算器を作成
            self.background_subtractor = cv2.createBackgroundSubtractorMOG2(
                history=500, varThreshold=50, detectShadows=True
            )
            logger.info("背景モデルをリセットしました")
