# イベント開催ランブック

## 目次
1. [事前準備](#事前準備)
2. [デプロイ手順](#デプロイ手順)
3. [問題編集方法](#問題編集方法)
4. [コスト試算](#コスト試算)
5. [注意事項](#注意事項)
6. [イベント当日の運用](#イベント当日の運用)
7. [トラブルシューティング](#トラブルシューティング)

---

## 事前準備

### 必要な環境
- AWS CLI
- Node.js 18以上
- Python 3.11以上
- AWS CDK CLI

---

## デプロイ手順

### 1. 初回セットアップ
```bash
# Python依存関係インストール
pip3 install -r requirements.txt

# CDK Bootstrap（初回のみ、リージョンごとに1回）
cdk bootstrap
```

### 2. 認証情報の準備
管理者用の認証情報を決定
- ユーザー名
- パスワード（強力なものを推奨）

### 3. デプロイ実行
```bash
cdk deploy --parameters AdminUsername=<ユーザー名> --parameters AdminPassword=<セキュアなパスワード>
```

**重要**: パスワードに特殊文字が含まれる場合はシングルクォートで囲む

### 4. 動作確認
デプロイ後に出力される`WebsiteUrl`にアクセス

- リーダーボード: `https://xxxxx.cloudfront.net/`
- 問題一覧ページ: `https://xxxxx.cloudfront.net/problems.html`
- 管理ページ: `https://xxxxx.cloudfront.net/admin.html`（Basic認証が求められる）

### 提出コマンド凡例 （API）

```bash
curl -X POST https://xxxxx.execute-api.us-east-1.amazonaws.com/prod/submit \
  -H "Content-Type: application/json" \
  -d '{
    "username": "<username>",
    "problem_number": <problem_number>,
    "code": "<Python code>"
  }'
```

---

## 問題編集方法

### 問題定義の場所
`contents/problems.json`

### 問題編集手順

1. `contents/problems.json`を開く
2. 問題を編集（テストケースのinput, outputはそれぞれ固定長で1になっています）

```json
{
  "問題番号": {
    "title": "新しい問題名",
    "description": [
      "問題の説明文（複数行可）",
      "HTMLタグも使用可能"
    ],
    "examples": [
      {"input": "solver(123)", "output": "\"結果\""}
    ],
    "test_cases": [
      ["入力1", "期待出力1"],
      ["入力2", "期待出力2"]
    ]
  }
}
```

3. デプロイ
```bash
cdk deploy --parameters AdminUsername=<ユーザー名> --parameters AdminPassword=<セキュアなパスワード>
```

### 問題タイプ

**引数ありの問題**
```json
"test_cases": [
  ["test_string", "result"],
  [123, "result"]
]
```

**引数なしの問題**
```json
"test_cases": [
  [null, "result"]
]
```

### 画像の追加
`contents/`ディレクトリに画像を配置し、descriptionで参照
```json
"description": [
  "<img src=\"image.png\" alt=\"説明\" style=\"max-width: 100%;\">"
]
```

### サンプル問題解説

AI駆動で取り組む想定の問題になっています。

#### 問題1

AIエージェントにそのまま問題文を渡してコーディングさせます。

**回答例**
```bash
curl -X POST https://xxxxxx.execute-api.us-east-1.amazonaws.com/prod/submit \
  -H "Content-Type: application/json" \
  -d '{
    "username": "user1",
    "problem_number": 1,
    "code": "def solver(s):\n    stack = []\n    pairs = {\")\": \"(\", \"}\": \"{\", \"]\": \"[\"}\n    max_depth = 0\n    for char in s:\n        if char in \"({[\":\n            stack.append(char)\n            max_depth = max(max_depth, len(stack))\n        elif char in \")}]\":\n            if not stack or stack[-1] != pairs[char]:\n                return \"-1\"\n            stack.pop()\n    return \"-1\" if stack else str(max_depth)"
  }'
```

### 問題2

AIエージェントに画像を読み込ませて予想させます。

**回答例**
```bash
curl -X POST https://xxxxx.execute-api.us-east-1.amazonaws.com/prod/submit \
  -H "Content-Type: application/json" \
  -d '{
    "username": "user1",
    "problem_number": 2,
    "code": "def solver():\n    return \"イギリス\""
  }'
```

### 問題3

CloudFrontの定額プランに関する問題です。
入出力のサンプルをヒントにその法則を解明し、リクエスト数に対応するプラン名を返せれば正解となります。


**回答例**
```bash
curl -X POST https://xxxxx.execute-api.us-east-1.amazonaws.com/prod/submit \
  -H "Content-Type: application/json" \
  -d '{
    "username": "user1",
    "problem_number": 3,
    "code": "def solver(n):\n    if n <= 1000000:\n        return \"Free\"\n    elif n <= 10000000:\n        return \"Pro\"\n    elif n <= 125000000:\n        return \"Business\"\n    elif n <= 500000000:\n        return \"Premium\"\n    else:\n        return \"担当SAにご相談ください\""
  }'
```

---

## コスト試算

### 想定条件
- イベント時間: 2時間
- 参加者: 50名
- 1人あたり提出回数: 平均20回
- 総提出数: 1,000回

### コスト内訳（us-east-1リージョン）

| サービス | 使用量 | 単価 | 月額コスト |
|---------|--------|------|-----------|
| **Lambda（Submit）** | 1,000回 × 30秒 | $0.0000166667/GB-秒 | $0.50 |
| **Lambda（Leaderboard）** | 2,400回（5秒更新） × 1秒 | $0.0000166667/GB-秒 | $0.04 |
| **API Gateway** | 3,400リクエスト | $3.50/100万 | $0.01 |
| **DynamoDB** | 1,000書込 + 2,400読取 | 書込$1.25/100万、読取$0.25/100万 | $0.01 |
| **Bedrock AgentCore** | 1,000セッション × 30秒 | $0.01/分 | $5.00 |
| **CloudFront** | 10GB転送 | $0.085/GB | $0.85 |
| **S3** | 1GB保存 + リクエスト | $0.023/GB + リクエスト | $0.03 |
| **Lambda@Edge** | 3,400リクエスト | $0.60/100万 | $0.01 |

**合計: 約$6.45/イベント**

### コスト削減のヒント
- イベント終了後すぐに`cdk destroy`で削除
- DynamoDBはPay-per-requestモードで使用量課金のみ
- CloudFrontキャッシュ活用で転送量削減

---

## 注意事項

### 重要: コード実行のセキュリティ

このシステムは**ユーザー提出コードをクラウド上で実行**します。以下の対策が実装されていますが、追加の注意が必要です。

### 実装済みのセキュリティ対策

#### 1. Bedrock AgentCore Code Interpreter
- **サンドボックス実行**: 隔離された環境でコード実行
- **ネットワーク分離**: `SANDBOX`モードで外部通信を制限
- **タイムアウト**: 30秒で強制終了

#### 2. 実行時間制限
```python
timeout=Duration.seconds(30)  # Lambda全体
```

### 追加推奨対策

#### 1. コード静的解析（推奨）
`lambda/submit.py`を編集し、提出前に危険な関数呼び出しを検出

#### 2. リソース制限
- メモリ: Lambda 512MB（デフォルト）
- 実行時間: 30秒
- Code Interpreterセッション: 1提出1セッション

#### 3. レート制限（推奨）
API Gatewayにスロットリング設定：
```python
api = apigw.RestApi(
    self, "ProgrammingContestApi",
    deploy_options=apigw.StageOptions(
        throttling_rate_limit=10,  # 秒間10リクエスト
        throttling_burst_limit=20
    )
)
```

#### 4. 監視とアラート
CloudWatch Logsで異常検知：
- 長時間実行
- エラー率の急増
- 異常なリクエストパターン

### 運用上の注意

#### 重要: API提出の制御

**管理画面で提出受付のON/OFF切り替えが可能です。セキュリティ上、以下を厳守してください**

1. **平常時**: 提出受付を**OFF**にする
2. **イベント・テスト時のみ**: 提出受付を**ON**にする
3. **イベント終了後**: 即座に提出受付を**OFF**にする

**操作方法:**
- 管理ページ（`https://xxxxx.cloudfront.net/admin.html`）にアクセス
- 「提出受付状態」セクションで「受付開始」/「受付停止」ボタンをクリック

**理由:**
- 不正なコード実行のリスクを最小化
- 予期しない課金を防止
- イベント外での悪用を防止

#### ユーザー名の重複

チーム内で複数人が同一のユーザー名を使うことを想定し、重複の際にエラー等は出ないようになっています。

チーム間で別々のユーザー名を使うようにしてください。

#### その他の運用注意事項

1. **イベント前**
   - 提出受付をONにする
   - テストコードで動作確認
   - 必要に応じ、悪意あるコードのテスト実行（隔離環境で）

2. **イベント中**
   - CloudWatch Logsをモニタリング
   - 異常な提出があれば調査

3. **イベント後**
   - **制限時間終了後、即座に提出受付をOFFにする**
   - ログの保存と分析

### 緊急時の対応

**不正なコード実行を検知した場合:**
```bash
# 1. API Gatewayを無効化
aws apigateway update-stage --rest-api-id <API_ID> --stage-name prod --patch-operations op=replace,path=/throttle/rateLimit,value=0

# 2. 環境削除
cdk destroy
```

---

## イベント当日の運用

### 開始前チェックリスト
- [ ] デプロイ完了確認
- [ ] 一般ページアクセス確認
- [ ] 管理ページアクセス確認
- [ ] **提出受付をONにする（管理画面）**
- [ ] テスト提出の動作確認
- [ ] リーダーボード更新確認

### 開始時
1. 参加者にURL共有: `https://xxxxx.cloudfront.net/`
2. 問題説明
3. 提出方法のデモ

### 進行中
- 管理ページでリアルタイム監視
- CloudWatch Logsで異常チェック
- 参加者からの質問対応

### 終了時
1. **提出受付をOFFにする（管理画面）**
2. 最終順位の確定
3. スクリーンショット保存
4. 環境削除（コスト削減）:
```bash
cdk destroy
```

---

## トラブルシューティング

### デプロイエラー

**エラー: "Admin username is required", "Admin password must be at least 8 characters"**
```bash
# 解決: 認証情報を適切に指定
cdk deploy --parameters AdminUsername=<ユーザー名> --parameters AdminPassword=<セキュアなパスワード>
```

**エラー: "CDK bootstrap required"**
```bash
# 解決: Bootstrap実行
cdk bootstrap
```

### 実行時エラー

**提出が失敗する**
- CloudWatch Logsで`/aws/lambda/ProgrammingContestStack-SubmitFunction`を確認
- Code Interpreterのタイムアウトを確認

**管理ページにアクセスできない**
- Basic認証情報が正しいかParameter Storeを確認
- CloudFrontの配信完了を待つ（最大15分）

### 削除時エラー

Lambda@Edgeを利用しているため、削除時に以下のエラーが出ることがあります。

```
There was an error deleting your function: Lambda was unable to delete arn:aws:lambda:us-east-1:624929674184:function:lambda-auth:1 because it is a replicated function.
```

この場合、1日ほど時間を空けて再度削除をお試しください。

詳細は公式ドキュメントをご参照ください。
https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/lambda-edge-delete-replicas.html

---

## 付録: 便利なコマンド

### ログ確認
```bash
# Submit Lambda
aws logs tail /aws/lambda/ProgrammingContestStack-SubmitFunction --follow

# Leaderboard Lambda
aws logs tail /aws/lambda/ProgrammingContestStack-LeaderboardFunction --follow
```

### DynamoDB確認
```bash
# Leaderboard全件取得
aws dynamodb scan --table-name ProgrammingContestStack-LeaderboardTable

# GameState確認
aws dynamodb scan --table-name ProgrammingContestStack-GameStateTable
```

### リセット
```bash
# 管理ページから、またはAPI直接呼び出し
curl -X POST https://xxxxx.execute-api.us-east-1.amazonaws.com/prod/reset
```