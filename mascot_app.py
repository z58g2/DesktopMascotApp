# 必要なライブラリをインポート
import sys
import json
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QMenu, QAction, 
                            QFileDialog, QVBoxLayout, QSystemTrayIcon, QInputDialog,
                            QHBoxLayout, QSpinBox, QDialog, QCheckBox, QMessageBox)
from PyQt5.QtCore import Qt, QPoint, QSize
from PyQt5.QtGui import QPixmap, QCursor, QIcon, QMovie
import os
import uuid

# マスコットウィジェットクラス（個々のマスコットを管理）
class MascotWidget(QWidget):
    def __init__(self, parent=None, image_info=None):
        super().__init__(parent)
        
        # ウィンドウの設定
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # レイアウトとイメージラベルの設定
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.image_label = QLabel()
        layout.addWidget(self.image_label)
        self.setLayout(layout)
        
        # 画像情報
        self.image_info = image_info
        self.movie = None
        
        # マスコットID（一意の識別子）
        self.mascot_id = str(uuid.uuid4())
        
        # 画像をロード
        if image_info:
            self.load_image()
        else:
            self.set_default_image()
        
        # ドラッグ操作の変数
        self.dragging = False
        self.offset = QPoint()
        
        # ウィンドウを表示
        self.show()
    
    # デフォルト画像を設定するメソッド
    def set_default_image(self):
        # サンプル用に透明の画像を作成
        default_image = QPixmap(100, 100)
        default_image.fill(Qt.transparent)
        self.image_label.setPixmap(default_image)
        self.resize(default_image.size())
    
    # 画像を読み込むメソッド
    def load_image(self):
        if not self.image_info:
            return
        
        file_path = self.image_info["path"]
        
        # 現在のGIFがある場合は停止
        if self.movie is not None:
            self.movie.stop()
            self.movie = None
        
        # GIFの場合
        if self.image_info["is_gif"]:
            movie = QMovie(file_path)
            
            # GIFが正常に読み込めた場合
            if movie.isValid():
                movie.setCacheMode(QMovie.CacheAll)
                self.image_label.setMovie(movie)
                movie.start()
                self.movie = movie
                
                # GIFの最初のフレームサイズに合わせてウィンドウをリサイズ
                movie.jumpToFrame(0)
                self.resize(movie.currentPixmap().size())
        # 静止画の場合
        else:
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():  # 画像の読み込みに成功した場合
                self.image_label.setPixmap(pixmap)
                self.resize(pixmap.size())
    
    # 画像情報を設定するメソッド
    def set_image_info(self, image_info):
        self.image_info = image_info
        self.load_image()
    
    # 前面表示を設定するメソッド
    def set_topmost(self, topmost):
        flags = self.windowFlags()
        if topmost:
            self.setWindowFlags(flags | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags & ~Qt.WindowStaysOnTopHint)
        
        # ウィンドウフラグを変更した後に再表示する必要がある
        self.show()
        
        # GIFの場合は再生を再開する
        if self.movie:
            self.movie.start()
    
    # リソースを解放するメソッド（追加）
    def cleanup_resources(self):
        # GIFムービーの停止と解放
        if self.movie is not None:
            self.movie.stop()
            self.image_label.setMovie(None)
            self.movie = None
        # 静的画像の解放
        else:
            self.image_label.setPixmap(QPixmap())
    
    # マウスボタンが押されたときのイベント
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:  # 左クリックの場合
            self.dragging = True
            self.offset = event.pos()
        elif event.button() == Qt.RightButton:  # 右クリックの場合
            # 親（MascotApp）に右クリックイベントを通知
            if hasattr(self.parent(), "show_mascot_context_menu"):
                self.parent().show_mascot_context_menu(self, event.pos())
    
    # マウスが動いたときのイベント（ドラッグ中）
    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() == Qt.LeftButton:
            # マスコットを移動
            self.move(self.mapToGlobal(event.pos() - self.offset))
    
    # マウスボタンが離されたときのイベント
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
    
    # 終了イベント（追加）
    def closeEvent(self, event):
        # リソースを解放してから閉じる
        self.cleanup_resources()
        super().closeEvent(event)

# マスコットアプリのクラスを定義
class MascotApp(QWidget):
    def __init__(self):
        super().__init__()
        
        # メインウィンドウを非表示にする
        self.setWindowFlags(Qt.Tool)
        self.hide()
        
        # 設定ファイルのパス - EXE化した場合でも動作するように修正
        try:
            # PyInstallerでexe化された場合
            if hasattr(sys, '_MEIPASS'):
                base_path = sys._MEIPASS
            else:
                # 通常のスクリプト実行
                base_path = os.path.dirname(os.path.abspath(__file__))
                
            # データディレクトリを作成（必要な場合）
            # EXE実行時はユーザーのホームディレクトリやAppDataにデータを保存する方がよい
            app_data_dir = os.path.join(os.path.expanduser('~'), '.mascot_app')
            if not os.path.exists(app_data_dir):
                os.makedirs(app_data_dir)
                
            self.config_file = os.path.join(app_data_dir, "mascot_config.json")
        except:
            # 何らかのエラーが発生した場合はスクリプトと同じ場所に保存
            self.config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mascot_config.json")
            
        # アイコンファイルのパスも同様に修正
        try:
            if hasattr(sys, '_MEIPASS'):
                self.icon_path = os.path.join(sys._MEIPASS, "icon.ico")
            else:
                self.icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
        except:
            self.icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
        
        # 画像リストの管理
        self.image_list = []  # パス、名前、GIFかどうかを保存
        self.mascot_widgets = []  # 表示中のマスコットウィジェットを管理
        
        # 前面表示の設定
        self.is_topmost = True
        
        # 設定を読み込む
        self.load_config()
        
        # システムトレイアイコンの設定
        self.setup_system_tray()
        
        # 前回の画像で起動
        self.load_last_mascots()
    
    # 設定を読み込むメソッド
    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    
                    # 画像リストを読み込む
                    if "image_list" in config:
                        self.image_list = config["image_list"]
                    
                    # トップモスト設定を読み込む
                    if "is_topmost" in config:
                        self.is_topmost = config["is_topmost"]
                    
                    # 前回表示していたマスコット情報を読み込む
                    self.last_mascots = config.get("last_mascots", [])
            except Exception as e:
                print(f"設定ファイルの読み込みエラー: {e}")
                self.last_mascots = []
        else:
            self.last_mascots = []
    
    # 設定を保存するメソッド
    def save_config(self):
        config = {
            "image_list": self.image_list,
            "is_topmost": self.is_topmost,
            "last_mascots": []
        }
        
        # 現在表示中のマスコット情報を保存
        for mascot in self.mascot_widgets:
            if mascot.image_info:
                # 画像インデックスを保存
                image_index = None
                for i, img in enumerate(self.image_list):
                    if img["path"] == mascot.image_info["path"]:
                        image_index = i
                        break
                
                if image_index is not None:
                    # 画像インデックスとマスコットの位置を保存
                    config["last_mascots"].append({
                        "image_index": image_index,
                        "position": {
                            "x": mascot.pos().x(),
                            "y": mascot.pos().y()
                        }
                    })
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"設定ファイルの保存エラー: {e}")
    
    # 前回のマスコットを読み込むメソッド
    def load_last_mascots(self):
        if hasattr(self, 'last_mascots') and self.last_mascots and self.image_list:
            for mascot_info in self.last_mascots:
                image_index = mascot_info.get("image_index")
                position = mascot_info.get("position")
                
                if image_index is not None and image_index < len(self.image_list):
                    # マスコットを作成
                    image_info = self.image_list[image_index]
                    mascot = MascotWidget(self, image_info)
                    mascot.set_topmost(self.is_topmost)
                    
                    # 保存された位置に移動
                    if position:
                        mascot.move(position.get("x", 0), position.get("y", 0))
                    
                    self.mascot_widgets.append(mascot)
            
            # メニューを更新
            self.update_tray_menu()
    
    # 画像を追加するメソッド
    def add_images(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "画像を選択", "", "画像ファイル (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        
        if file_paths:  # ファイルが選択された場合
            for file_path in file_paths:
                # 画像に名前を付ける
                file_name = os.path.basename(file_path)
                image_name, ok = QInputDialog.getText(
                    self, "画像の名前", f"「{file_name}」の表示名を入力してください:", 
                    text=file_name
                )
                
                if not ok:  # キャンセルされた場合
                    continue
                
                if not image_name:  # 名前が空の場合
                    image_name = file_name
                
                # ファイル拡張子を取得
                _, ext = os.path.splitext(file_path)
                is_gif = ext.lower() == ".gif"
                
                # 画像リストに追加
                image_info = {
                    "path": file_path,
                    "name": image_name,
                    "is_gif": is_gif
                }
                
                self.image_list.append(image_info)
                
                # マスコットを表示するか尋ねる
                reply = QMessageBox.question(
                    self, "マスコット表示", 
                    f"「{image_name}」をすぐに表示しますか？",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
                )
                
                if reply == QMessageBox.Yes:
                    self.create_mascot(image_info)
            
            # 設定を保存
            self.save_config()
            
            # システムトレイメニューを更新
            self.update_tray_menu()
    
    # マスコットを作成するメソッド
    def create_mascot(self, image_info):
        mascot = MascotWidget(self, image_info)
        mascot.set_topmost(self.is_topmost)
        
        # 新しいマスコットを既存のマスコットから少しずらした位置に表示
        if self.mascot_widgets:
            last_mascot = self.mascot_widgets[-1]
            new_pos = last_mascot.pos() + QPoint(20, 20)
            mascot.move(new_pos)
        
        self.mascot_widgets.append(mascot)
        
        # 設定を保存
        self.save_config()
        
        # メニューを更新
        self.update_tray_menu()
    
    # 選択したマスコットを削除するメソッド（修正）
    def remove_mascot(self, mascot):
        try:
            if mascot in self.mascot_widgets:
                # リストから削除（先に行う）
                self.mascot_widgets.remove(mascot)
                
                # リソースをクリーンアップしてから閉じる
                mascot.cleanup_resources()
                mascot.hide()  # いきなり閉じるのではなく、まず非表示に
                
                # イベントループの次のサイクルで削除するようスケジュール
                mascot.deleteLater()
                
                # 設定を保存
                self.save_config()
                
                # メニューを更新
                self.update_tray_menu()
        except Exception as e:
            print(f"マスコット削除エラー: {e}")
    
    # 全てのマスコットを削除（修正）
    def remove_all_mascots(self):
        try:
            # すべてのマスコットのリストのコピーを作成
            mascots_to_remove = self.mascot_widgets.copy()
            
            # マスコットリストをクリア
            self.mascot_widgets.clear()
            
            # 各マスコットを安全に削除
            for mascot in mascots_to_remove:
                mascot.cleanup_resources()
                mascot.hide()  # 先に非表示にする
                mascot.deleteLater()  # 次のイベントループで削除
            
            # 設定を保存
            self.save_config()
            
            # メニューを更新
            self.update_tray_menu()
        except Exception as e:
            print(f"全マスコット削除エラー: {e}")
    
    # 画像を削除するメソッド（修正）
    def remove_image(self, index):
        try:
            if 0 <= index < len(self.image_list):
                # 削除する画像情報
                removed_image = self.image_list[index]
                
                # 画像リストから削除
                del self.image_list[index]
                
                # この画像を使用しているマスコットを特定
                mascots_to_remove = []
                for mascot in self.mascot_widgets:
                    if mascot.image_info == removed_image:
                        mascots_to_remove.append(mascot)
                
                # 特定したマスコットを削除
                for mascot in mascots_to_remove:
                    self.remove_mascot(mascot)
                
                # 設定を保存
                self.save_config()
                
                # メニューを更新
                self.update_tray_menu()
        except Exception as e:
            print(f"画像削除エラー: {e}")
    
    # 前面表示を切り替えるメソッド
    def toggle_topmost(self):
        self.is_topmost = not self.is_topmost
        
        # 全てのマスコットの前面表示設定を変更
        for mascot in self.mascot_widgets:
            mascot.set_topmost(self.is_topmost)
        
        # 設定を保存
        self.save_config()
        
        # メニューを更新
        self.update_tray_menu()
    
    # システムトレイアイコンを設定するメソッド
    def setup_system_tray(self):
        # システムトレイアイコンの作成
        self.tray_icon = QSystemTrayIcon(self)
        
        # アイコンファイルの存在を確認
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            # デフォルトアイコンが見つからない場合は空のアイコンを使用
            empty_icon = QIcon()
            self.tray_icon.setIcon(empty_icon)
        
        # トレイアイコンのメニュー作成
        self.tray_menu = QMenu()
        
        # メニュー項目を追加
        self.create_tray_menu()
        
        # トレイアイコンにメニューをセット
        self.tray_icon.setContextMenu(self.tray_menu)
        # トレイアイコンを表示
        self.tray_icon.show()
    
    # トレイメニューを作成するメソッド
    def create_tray_menu(self):
        # メニューをクリア
        self.tray_menu.clear()
        
        # 「画像を追加」メニュー項目
        add_images_action = QAction("画像を追加", self)
        add_images_action.triggered.connect(self.add_images)
        self.tray_menu.addAction(add_images_action)
        
        self.tray_menu.addSeparator()  # 区切り線
        
        # 「マスコットを表示」サブメニュー
        self.display_menu = QMenu("マスコットを表示", self)
        self.update_display_menu()
        self.tray_menu.addMenu(self.display_menu)
        
        # 「表示中のマスコット」サブメニュー
        self.active_mascots_menu = QMenu("表示中のマスコット", self)
        self.update_active_mascots_menu()
        self.tray_menu.addMenu(self.active_mascots_menu)
        
        # 「画像管理」サブメニュー
        self.images_menu = QMenu("画像管理", self)
        self.update_images_menu()
        self.tray_menu.addMenu(self.images_menu)
        
        self.tray_menu.addSeparator()  # 区切り線
        
        # 「すべてのマスコットを削除」メニュー項目
        remove_all_action = QAction("すべてのマスコットを削除", self)
        remove_all_action.triggered.connect(self.remove_all_mascots)
        remove_all_action.setEnabled(len(self.mascot_widgets) > 0)
        self.tray_menu.addAction(remove_all_action)
        
        self.tray_menu.addSeparator()  # 区切り線
        
        # 「常に前面に表示」メニュー項目（チェックボックス付き）
        topmost_action = QAction("常に前面に表示", self)
        topmost_action.setCheckable(True)  # チェックボックスにする
        topmost_action.setChecked(self.is_topmost)  # 初期状態をセット
        topmost_action.triggered.connect(self.toggle_topmost)
        self.tray_menu.addAction(topmost_action)
        
        self.tray_menu.addSeparator()  # 区切り線
        
        # 「終了」メニュー項目
        exit_action = QAction("終了", self)
        exit_action.triggered.connect(self.on_exit)
        self.tray_menu.addAction(exit_action)
    
    # 終了時の処理メソッド
    def on_exit(self):
        # 設定を保存
        self.save_config()
        
        # すべてのマスコットを安全に閉じる
        self.remove_all_mascots()
        
        # アプリケーションを終了
        QApplication.quit()
    
    # 「マスコットを表示」メニューを更新するメソッド
    def update_display_menu(self):
        self.display_menu.clear()
        
        # 画像リストが空の場合
        if len(self.image_list) == 0:
            no_images_action = QAction("画像がありません", self)
            no_images_action.setEnabled(False)
            self.display_menu.addAction(no_images_action)
            return
        
        # 画像ごとにアクションを追加
        for i, image_info in enumerate(self.image_list):
            image_action = QAction(image_info["name"], self)
            
            # ラムダ式を使って各アクションに対応するインデックスを保持
            info_copy = image_info  # ローカル変数にコピー
            image_action.triggered.connect(lambda checked=False, info=info_copy: self.create_mascot(info))
            
            self.display_menu.addAction(image_action)
    
    # 「表示中のマスコット」メニューを更新するメソッド
    def update_active_mascots_menu(self):
        self.active_mascots_menu.clear()
        
        # 表示中のマスコットがない場合
        if len(self.mascot_widgets) == 0:
            no_mascots_action = QAction("表示中のマスコットがありません", self)
            no_mascots_action.setEnabled(False)
            self.active_mascots_menu.addAction(no_mascots_action)
            return
        
        # マスコットごとにアクションを追加
        for i, mascot in enumerate(self.mascot_widgets):
            name = mascot.image_info["name"] if mascot.image_info else "無名マスコット"
            mascot_action = QAction(f"{i+1}: {name}", self)
            
            # マスコットを削除するサブメニュー
            remove_action = QAction("削除", self)
            # ローカル変数にコピー
            target_mascot = mascot
            remove_action.triggered.connect(lambda checked=False, m=target_mascot: self.remove_mascot(m))
            
            # マスコットに移動するサブメニュー
            goto_action = QAction("移動", self)
            target_mascot_goto = mascot  # もう一度コピー
            goto_action.triggered.connect(lambda checked=False, m=target_mascot_goto: m.activateWindow())
            
            # サブメニューを作成
            mascot_submenu = QMenu()
            mascot_submenu.addAction(goto_action)
            mascot_submenu.addAction(remove_action)
            
            mascot_action.setMenu(mascot_submenu)
            self.active_mascots_menu.addAction(mascot_action)
    
    # 「画像管理」メニューを更新するメソッド
    def update_images_menu(self):
        self.images_menu.clear()
        
        # 画像リストが空の場合
        if len(self.image_list) == 0:
            no_images_action = QAction("画像がありません", self)
            no_images_action.setEnabled(False)
            self.images_menu.addAction(no_images_action)
            return
        
        # 画像ごとにアクションを追加
        for i, image_info in enumerate(self.image_list):
            image_action = QAction(image_info["name"], self)
            
            # 画像を削除するサブメニュー
            remove_action = QAction("削除", self)
            # 正しくインデックスを渡すためにローカル変数にコピー
            idx = i
            remove_action.triggered.connect(lambda checked=False, idx=idx: self.remove_image(idx))
            
            # サブメニューを作成
            image_submenu = QMenu()
            image_submenu.addAction(remove_action)
            
            image_action.setMenu(image_submenu)
            self.images_menu.addAction(image_action)
    
    # トレイメニューを更新するメソッド
    def update_tray_menu(self):
        # トレイメニューを再作成
        self.create_tray_menu()
    
    # マスコットのコンテキストメニューを表示するメソッド（修正）
    def show_mascot_context_menu(self, mascot, position):
        try:
            # コンテキストメニューを作成
            context_menu = QMenu()
            
            # メニュー項目を追加
            remove_action = QAction("このマスコットを削除", self)
            # ラムダ関数内でマスコットの参照を使う
            target_mascot = mascot  # ローカル変数にコピー
            remove_action.triggered.connect(lambda checked=False, m=target_mascot: self.remove_mascot(m))
            
            # 画像を切り替えるサブメニュー
            change_image_menu = QMenu("画像を変更", self)
            for image_info in self.image_list:
                image_action = QAction(image_info["name"], self)
                # 正しく画像情報を渡す
                info_copy = image_info  # ローカル変数にコピー
                target_mascot_for_image = mascot  # ここでもコピーを作成
                image_action.triggered.connect(lambda checked=False, info=info_copy, m=target_mascot_for_image: m.set_image_info(info))
                change_image_menu.addAction(image_action)
            
            if len(self.image_list) == 0:
                no_images_action = QAction("画像がありません", self)
                no_images_action.setEnabled(False)
                change_image_menu.addAction(no_images_action)
            
            # メニューに項目を追加
            context_menu.addMenu(change_image_menu)
            context_menu.addAction(remove_action)
            
            # コンテキストメニューを表示
            context_menu.exec_(mascot.mapToGlobal(position))
        except Exception as e:
            print(f"コンテキストメニューエラー: {e}")

# プログラムのメイン部分
if __name__ == '__main__':
    # QApplicationインスタンスを作成
    app = QApplication(sys.argv)
    # マスコットアプリのインスタンスを作成
    mascot_app = MascotApp()
    # アプリケーションのイベントループを開始
    sys.exit(app.exec_())