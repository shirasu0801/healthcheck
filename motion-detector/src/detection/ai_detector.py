"""AI検知モジュール（TensorFlow + COCO）"""
import cv2
import numpy as np
from typing import List, Tuple, Optional
import logging
import os

try:
    import tensorflow as tf
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    logging.warning("TensorFlowがインストールされていません。AI検知機能は使用できません。")

logger = logging.getLogger(__name__)

# COCOクラス名（80種類）
COCO_CLASSES = [
    'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck',
    'boat', 'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench',
    'bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra',
    'giraffe', 'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee',
    'skis', 'snowboard', 'sports ball', 'kite', 'baseball bat', 'baseball glove',
    'skateboard', 'surfboard', 'tennis racket', 'bottle', 'wine glass', 'cup',
    'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple', 'sandwich', 'orange',
    'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch',
    'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse',
    'remote', 'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink',
    'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear', 'hair drier',
    'toothbrush'
]


class AIDetector:
    """AI検知クラス（TensorFlow + COCO）"""
    
    def __init__(self, model_path: Optional[str] = None, 
                 confidence_threshold: float = 0.5,
                 target_classes: Optional[List[str]] = None):
        """
        初期化
        
        Args:
            model_path: モデルファイルのパス（Noneの場合はTensorFlow Hubからダウンロード）
            confidence_threshold: 信頼度のしきい値（0.0-1.0）
            target_classes: 検知対象のクラス名リスト（Noneの場合は全クラス）
        """
        if not TENSORFLOW_AVAILABLE:
            raise ImportError("TensorFlowがインストールされていません。pip install tensorflow でインストールしてください。")
        
        self.confidence_threshold = confidence_threshold
        self.target_classes = target_classes if target_classes else COCO_CLASSES
        
        # モデル読み込み
        self.model = None
        self.input_size = (640, 640)  # デフォルト入力サイズ
        
        if model_path and os.path.exists(model_path):
            self._load_model_from_file(model_path)
        else:
            logger.warning("モデルファイルが指定されていません。TensorFlow Hubモデルを使用します。")
            self._load_model_from_hub()
        
        logger.info(f"AI検知モジュールを初期化しました: threshold={confidence_threshold}")
    
    def _load_model_from_hub(self) -> None:
        """TensorFlow HubからCOCOモデルを読み込む"""
        try:
            import tensorflow_hub as hub
            # MobileNetV2ベースのSSDモデル（軽量でRaspberry Pi向き）
            model_url = "https://tfhub.dev/tensorflow/ssd_mobilenet_v2/2"
            self.model = hub.load(model_url)
            logger.info("TensorFlow Hubからモデルを読み込みました")
        except Exception as e:
            logger.error(f"モデルの読み込みに失敗しました: {e}")
            raise
    
    def _load_model_from_file(self, model_path: str) -> None:
        """ファイルからモデルを読み込む"""
        try:
            self.model = tf.saved_model.load(model_path)
            logger.info(f"モデルファイルを読み込みました: {model_path}")
        except Exception as e:
            logger.error(f"モデルファイルの読み込みに失敗しました: {e}")
            raise
    
    def detect(self, frame: np.ndarray) -> Tuple[List[Tuple[int, int, int, int]], List[str], List[float]]:
        """
        フレームからオブジェクトを検知する
        
        Args:
            frame: 入力フレーム（BGR形式）
            
        Returns:
            (バウンディングボックスリスト, クラス名リスト, 信頼度リスト)のタプル
        """
        if self.model is None:
            return [], [], []
        
        if len(frame.shape) == 2:
            # グレースケールの場合はBGRに変換
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        
        # フレームをリサイズ
        height, width = frame.shape[:2]
        input_frame = cv2.resize(frame, self.input_size)
        
        # RGBに変換（TensorFlowモデルはRGBを期待）
        input_frame_rgb = cv2.cvtColor(input_frame, cv2.COLOR_BGR2RGB)
        
        # バッチ次元を追加
        input_tensor = tf.convert_to_tensor(input_frame_rgb, dtype=tf.uint8)
        input_tensor = tf.expand_dims(input_tensor, 0)
        
        # 推論実行
        try:
            detections = self.model(input_tensor)
            
            # 結果を解析
            bboxes = []
            classes = []
            scores = []
            
            boxes = detections['detection_boxes'][0].numpy()
            class_ids = detections['detection_classes'][0].numpy().astype(int)
            detection_scores = detections['detection_scores'][0].numpy()
            
            for i in range(len(boxes)):
                score = detection_scores[i]
                if score < self.confidence_threshold:
                    continue
                
                class_id = class_ids[i]
                if class_id >= len(COCO_CLASSES):
                    continue
                
                class_name = COCO_CLASSES[class_id - 1]  # COCOクラスIDは1から始まる
                
                # 対象クラスのみ検知
                if class_name not in self.target_classes:
                    continue
                
                # バウンディングボックスを元のサイズに変換
                y_min, x_min, y_max, x_max = boxes[i]
                x_min = int(x_min * width)
                y_min = int(y_min * height)
                x_max = int(x_max * width)
                y_max = int(y_max * height)
                
                bboxes.append((x_min, y_min, x_max - x_min, y_max - y_min))
                classes.append(class_name)
                scores.append(float(score))
            
            return bboxes, classes, scores
            
        except Exception as e:
            logger.error(f"AI検知中にエラーが発生しました: {e}")
            return [], [], []
    
    def set_confidence_threshold(self, threshold: float) -> None:
        """
        信頼度のしきい値を設定する
        
        Args:
            threshold: 信頼度のしきい値（0.0-1.0）
        """
        self.confidence_threshold = max(0.0, min(1.0, threshold))
        logger.info(f"信頼度のしきい値を設定しました: {self.confidence_threshold}")
    
    def set_target_classes(self, classes: List[str]) -> None:
        """
        検知対象のクラスを設定する
        
        Args:
            classes: クラス名リスト
        """
        self.target_classes = classes
        logger.info(f"検知対象クラスを設定しました: {classes}")
