"""SQLiteデータベース管理モジュール"""
import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class Database:
    """SQLiteデータベース管理クラス"""
    
    def __init__(self, db_path: str = "data/detections.db"):
        """
        初期化
        
        Args:
            db_path: データベースファイルのパス
        """
        self.db_path = db_path
        
        # ディレクトリを作成
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # データベースを初期化
        self._init_database()
        
        logger.info(f"データベースを初期化しました: {db_path}")
    
    def _init_database(self) -> None:
        """データベーステーブルを作成"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 検知イベントテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                detection_method TEXT NOT NULL,
                detected_objects TEXT,
                confidence REAL,
                bbox_count INTEGER,
                video_path TEXT,
                image_path TEXT
            )
        """)
        
        # インデックスを作成（検索高速化）
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON detections(timestamp)
        """)
        
        conn.commit()
        conn.close()
    
    def add_detection(self, detection_method: str, detected_objects: Optional[List[str]] = None,
                     confidence: Optional[float] = None, bbox_count: int = 0,
                     video_path: Optional[str] = None, image_path: Optional[str] = None) -> int:
        """
        検知イベントを記録
        
        Args:
            detection_method: 検知方法（"frame_diff", "background_subtraction", "ai"）
            detected_objects: 検知されたオブジェクトのリスト
            confidence: 信頼度（AI検知の場合）
            bbox_count: バウンディングボックスの数
            video_path: 録画ファイルのパス
            image_path: 画像ファイルのパス
            
        Returns:
            挿入されたレコードのID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        objects_str = ",".join(detected_objects) if detected_objects else None
        
        cursor.execute("""
            INSERT INTO detections 
            (timestamp, detection_method, detected_objects, confidence, bbox_count, video_path, image_path)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (timestamp, detection_method, objects_str, confidence, bbox_count, video_path, image_path))
        
        record_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.debug(f"検知イベントを記録しました: ID={record_id}, method={detection_method}")
        return record_id
    
    def get_detections(self, start_date: Optional[str] = None, 
                      end_date: Optional[str] = None,
                      limit: int = 100) -> List[Dict]:
        """
        検知イベントを取得
        
        Args:
            start_date: 開始日時（"YYYY-MM-DD HH:MM:SS"形式）
            end_date: 終了日時（"YYYY-MM-DD HH:MM:SS"形式）
            limit: 取得件数の上限
            
        Returns:
            検知イベントのリスト
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM detections WHERE 1=1"
        params = []
        
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # カラム名を取得
        columns = [description[0] for description in cursor.description]
        
        # 辞書のリストに変換
        detections = []
        for row in rows:
            detection = dict(zip(columns, row))
            # detected_objectsをリストに変換
            if detection['detected_objects']:
                detection['detected_objects'] = detection['detected_objects'].split(',')
            else:
                detection['detected_objects'] = []
            detections.append(detection)
        
        conn.close()
        return detections
    
    def get_statistics(self, start_date: Optional[str] = None,
                      end_date: Optional[str] = None) -> Dict:
        """
        統計情報を取得
        
        Args:
            start_date: 開始日時
            end_date: 終了日時
            
        Returns:
            統計情報の辞書
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT COUNT(*) as total FROM detections WHERE 1=1"
        params = []
        
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)
        
        cursor.execute(query, params)
        total = cursor.fetchone()[0]
        
        # 検知方法別の集計
        query_method = query.replace("COUNT(*) as total", 
                                     "detection_method, COUNT(*) as count")
        query_method += " GROUP BY detection_method"
        
        cursor.execute(query_method, params)
        method_counts = {row[0]: row[1] for row in cursor.fetchall()}
        
        # 最新の検知時刻
        query_latest = query.replace("COUNT(*) as total", "MAX(timestamp) as latest")
        cursor.execute(query_latest, params)
        latest = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total': total,
            'method_counts': method_counts,
            'latest_detection': latest
        }
    
    def delete_old_records(self, days: int = 30) -> int:
        """
        古いレコードを削除
        
        Args:
            days: 何日前より古いレコードを削除するか
            
        Returns:
            削除されたレコード数
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 日付を計算
        from datetime import timedelta
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("DELETE FROM detections WHERE timestamp < ?", (cutoff_date,))
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        logger.info(f"{deleted_count}件の古いレコードを削除しました（{days}日前より古い）")
        return deleted_count
