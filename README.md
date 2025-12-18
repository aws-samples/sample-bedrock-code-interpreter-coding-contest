# Code Interpreter Coding Contest

Code Interpreter Coding Contestは、様々な問題をコーディングコンテスト・タイムアタック形式で競い合うためのサーバーレスプラットフォームです。

Amazon Bedrock AgentCore Code Interpreterを活用したサンドボックスでの安全なコード実行環境、リアルタイムリーダーボード、RESTful APIを提供し、AI駆動のコーディングコンテストを簡単に開催できます。

## 主な機能

- **安全なコード実行**: Amazon Bedrock AgentCore Code Interpreterによるサンドボックス環境でのPythonコード実行
- **リアルタイムリーダーボード**: CloudFront + S3でホストされる自動更新型のWebインターフェース
- **RESTful API**: コード提出、順位取得、ゲーム状態管理のためのAPI Gateway統合
- **カスタマイズ可能な問題セット**: JSON形式で簡単に問題を追加・編集可能
- **Basic認証**: 管理画面へのアクセス制御

## デプロイ

```bash
pip3 install -r requirements.txt
cdk bootstrap  # 初回のみ
cdk deploy --parameters AdminUsername=<ユーザー名> --parameters AdminPassword=<セキュアなパスワード>
```

## 使用方法

詳細はRUNBOOK.mdをご参照ください。

## アーキテクチャ

```mermaid
graph TB
    User[ユーザー]
    CF[CloudFront]
    S3[S3 Bucket<br/>静的Webサイト]
    APIGW[API Gateway]
    SubmitLambda[Submit Lambda<br/>コード実行・採点]
    LeaderboardLambda[Leaderboard Lambda<br/>順位取得]
    ResetLambda[Reset Lambda<br/>リセット]
    CodeInterpreter[Code Interpreter<br/>サンドボックス実行]
    DDB1[(DynamoDB<br/>Leaderboard)]
    DDB2[(DynamoDB<br/>GameState)]
    
    User -->|HTTPS| CF
    CF --> S3
    User -->|API Call| APIGW
    APIGW --> SubmitLambda
    APIGW --> LeaderboardLambda
    APIGW --> ResetLambda
    SubmitLambda --> CodeInterpreter
    SubmitLambda --> DDB1
    SubmitLambda --> DDB2
    LeaderboardLambda --> DDB1
    LeaderboardLambda --> DDB2
    ResetLambda --> DDB1
    ResetLambda --> DDB2
```

## データフロー

### コード提出フロー
```mermaid
sequenceDiagram
    participant U as ユーザー
    participant API as API Gateway
    participant SL as Submit Lambda
    participant CI as Code Interpreter
    participant DDB1 as Leaderboard Table
    participant DDB2 as GameState Table
    
    U->>API: POST /submit<br/>{username, problem_number, code}
    API->>SL: リクエスト転送
    SL->>CI: セッション開始
    SL->>CI: コード実行
    CI->>SL: 実行結果
    SL->>CI: セッション終了
    alt 正解
        SL->>DDB2: 問題状態確認
        alt 初回正解
            SL->>DDB1: 記録保存<br/>{username, problem_number, timestamp}
            SL->>DDB2: 問題状態更新
        end
    end
    SL->>API: 結果返却
    API->>U: {result, message}
```

### リーダーボード取得フロー
```mermaid
sequenceDiagram
    participant U as ユーザー
    participant API as API Gateway
    participant LL as Leaderboard Lambda
    participant DDB1 as Leaderboard Table
    participant DDB2 as GameState Table
    
    U->>API: GET /leaderboard
    API->>LL: リクエスト転送
    LL->>DDB1: 全記録取得
    LL->>DDB2: 問題状態取得
    LL->>LL: ユーザー別集計・ソート
    LL->>API: ランキングデータ
    API->>U: {leaderboard, problem_states}
```

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

