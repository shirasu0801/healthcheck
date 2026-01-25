"""メール通知機能モジュール"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
import os
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class EmailNotifier:
    """メール通知クラス"""
    
    def __init__(self, smtp_server: str, smtp_port: int, 
                 username: str, password: str, to_email: str):
        """
        初期化
        
        Args:
            smtp_server: SMTPサーバーアドレス
            smtp_port: SMTPポート番号
            username: SMTP認証ユーザー名
            password: SMTP認証パスワード
            to_email: 送信先メールアドレス
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.to_email = to_email
        
        logger.info(f"メール通知機能を初期化しました: {smtp_server}:{smtp_port}")
    
    def send_notification(self, subject: str, body: str, 
                         image_path: Optional[str] = None,
                         video_path: Optional[str] = None) -> bool:
        """
        通知メールを送信
        
        Args:
            subject: 件名
            body: 本文
            image_path: 添付する画像ファイルのパス（オプション）
            video_path: 添付する動画ファイルのパス（オプション）
            
        Returns:
            送信成功時True
        """
        try:
            # メールメッセージを作成
            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['To'] = self.to_email
            msg['Subject'] = subject
            
            # 本文を追加
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # 画像を添付
            if image_path and os.path.exists(image_path):
                with open(image_path, 'rb') as f:
                    img_data = f.read()
                    image = MIMEImage(img_data)
                    image.add_header('Content-Disposition', 
                                   f'attachment; filename={os.path.basename(image_path)}')
                    msg.attach(image)
            
            # 動画を添付（ファイルサイズが大きい場合は注意）
            if video_path and os.path.exists(video_path):
                file_size = os.path.getsize(video_path)
                # 10MB以下の場合のみ添付
                if file_size <= 10 * 1024 * 1024:
                    with open(video_path, 'rb') as f:
                        video_data = f.read()
                        video = MIMEBase('application', 'octet-stream')
                        video.set_payload(video_data)
                        encoders.encode_base64(video)
                        video.add_header('Content-Disposition',
                                       f'attachment; filename={os.path.basename(video_path)}')
                        msg.attach(video)
                else:
                    logger.warning(f"動画ファイルが大きすぎます（{file_size} bytes）。添付をスキップします。")
            
            # SMTPサーバーに接続して送信
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()  # TLS暗号化
            server.login(self.username, self.password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"通知メールを送信しました: {self.to_email}")
            return True
            
        except Exception as e:
            logger.error(f"メール送信に失敗しました: {e}")
            return False
    
    def send_detection_notification(self, detection_method: str,
                                   detected_objects: Optional[List[str]] = None,
                                   confidence: Optional[float] = None,
                                   image_path: Optional[str] = None,
                                   video_path: Optional[str] = None) -> bool:
        """
        検知通知メールを送信
        
        Args:
            detection_method: 検知方法
            detected_objects: 検知されたオブジェクトのリスト
            confidence: 信頼度
            image_path: 検知画像のパス
            video_path: 録画ファイルのパス
            
        Returns:
            送信成功時True
        """
        from datetime import datetime
        
        # 件名
        subject = f"【動体検知】検知イベント - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # 本文
        body = f"""動体検知システムで検知イベントが発生しました。

検知時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
検知方法: {detection_method}
"""
        
        if detected_objects:
            body += f"検知オブジェクト: {', '.join(detected_objects)}\n"
        
        if confidence is not None:
            body += f"信頼度: {confidence:.2%}\n"
        
        if video_path:
            body += f"\n録画ファイル: {video_path}\n"
        
        return self.send_notification(subject, body, image_path, video_path)
