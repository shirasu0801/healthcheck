"""設定ファイル読み込みモジュール"""
import json
import os
from typing import Dict, Any, Optional


class ConfigLoader:
    """設定ファイルを読み込むクラス"""
    
    def __init__(self, config_path: str = "config.json"):
        """
        初期化
        
        Args:
            config_path: 設定ファイルのパス
        """
        self.config_path = config_path
        self.config: Optional[Dict[str, Any]] = None
        self.load()
    
    def load(self) -> Dict[str, Any]:
        """
        設定ファイルを読み込む
        
        Returns:
            設定辞書
            
        Raises:
            FileNotFoundError: 設定ファイルが見つからない場合
            json.JSONDecodeError: JSONの解析に失敗した場合
        """
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"設定ファイルが見つかりません: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        return self.config
    
    def save(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        設定をファイルに保存する
        
        Args:
            config: 保存する設定辞書（Noneの場合は現在の設定を保存）
        """
        if config is None:
            config = self.config
        
        if config is None:
            raise ValueError("保存する設定がありません")
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        self.config = config
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        設定値を取得する（ドット記法対応）
        
        Args:
            key: 設定キー（例: "camera.width"）
            default: デフォルト値
            
        Returns:
            設定値
        """
        if self.config is None:
            return default
        
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        設定値を設定する（ドット記法対応）
        
        Args:
            key: 設定キー（例: "camera.width"）
            value: 設定値
        """
        if self.config is None:
            self.config = {}
        
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
