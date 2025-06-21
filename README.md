## 📊 処理フロー概要（推薦APIの内部処理）

### 1️⃣ クライアントから推薦リクエスト送信

エンドポイント:
**POST /recipes/recommend**

リクエスト内容（例）:

```json
{
  "available_ingredients": ["キャベツ", "じゃがいも", ...],
  "required_ingredients": ["鶏肉"],
  "max_cooking_time": 30
}
```

* `available_ingredients` … 現在冷蔵庫にある食材リスト
* `required_ingredients` … 絶対に使いたい食材リスト
* `max_cooking_time` … 希望する調理時間（分）

---

### 2️⃣ APIサーバーでルーターがリクエストを受信

FastAPI の router 層がリクエストデータを受け取り、推薦ロジックへ渡す。

---

### 3️⃣ 名前 ➔ 食材ID 変換処理

* `ingredient_master` コレクションを検索
* `standard_name` と `synonyms` にマッチする食材ID（`ingredient_id`）を抽出
* ユーザー入力された食材名 ➔ DB内部の食材IDに変換する

---

### 4️⃣ MongoDB Aggregation によるレシピ絞り込み & ランダム抽出

* `recipes` コレクションに対して以下の条件でフィルター

#### フィルター条件：

* 使用食材が `available_ids` 内に完全一致する
* `required_ids` のすべてを含んでいる
* 調理時間が `max_cooking_time` 以下である

#### さらに：

* `$sample` ステージを利用し、条件に合致したレシピの中から**ランダムに1件**抽出

---

### 5️⃣ MongoDBから取得したレシピデータを整形

* MongoDB の `_id`（ObjectId型）を文字列に変換
* Pydantic モデルにマッピングして整形

---

### 6️⃣ レスポンス生成

最終的なAPIレスポンス例：

```json
{
  "name": "...",
  "ingredients": [...],
  "steps": [...],
  "missing_ingredients": [],
  "recommend_score": 1.0,
  "recommend_reason": "おすすめのレシピを見つけました！"
}
```
