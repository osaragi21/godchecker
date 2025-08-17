# God Checker (GitHub Pages + Actions)

個人運用の「皇族 / 首相 / 国賓」等の**公開情報ベースの規制予定**を表示するPWA。

## 使い方（最短）
1. このリポジトリを GitHub に作成（公開でも非公開でもOK）
2. **Settings → Pages → Build and deployment → Source: Deploy from a branch**  
   - Branch: `main`（または `master`） / Folder: `/web`
3. 数十秒で `https://<username>.github.io/<repo>/` のURLが発行されます
4. PixelのChromeでURLを開き、右上「︙」→ **ホーム画面に追加**

## 自動更新（GitHub Actions）
- `.github/workflows/update.yml` が **毎時** 自動実行
- `scripts/scrape.py` が公開サイトを収集して `web/restrictions.json` を生成
- 成果はコミット（`GITHUB_TOKEN` を利用）→ Pages で自動配信

> 初期状態の `scrape.py` は**サンプル実装／雛形**です。実サイトの構造に合わせてパーサを育ててください。

## ディレクトリ構成
- `/web` … 公開ディレクトリ（GitHub Pagesはここを配信）
  - `index.html`, `manifest.webmanifest`, `sw.js`, `icons/`, `restrictions.json`
- `/scripts` … 収集スクリプト（Python）
- `/.github/workflows/update.yml` … スケジュール実行

## ローカルでテスト
```bash
python -m http.server 8000 -d web
# http://localhost:8000/ にアクセス
```

## 免責
- このツールは**公開情報**のみを集約表示します。実移動ルートの推測は行いません。
- スクレイピングは各サイトの利用規約に従ってください。
