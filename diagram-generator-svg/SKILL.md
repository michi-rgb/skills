---
name: diagram-generator-svg
description: 技術ブログ記事用のSVG図解を生成するスキル。アクセシビリティ準拠、Material Icons統合、6つのデザインパターンをサポート。
allowed-tools: Read, Write, Bash
---

# Diagram Generator Skill

技術ブログ記事用のSVG図解を生成します。アクセシビリティ準拠、Material Icons統合、6つのデザインパターンをサポートします。

## When to Use

以下の場合にこのスキルを使用してください：

- ユーザーが技術ブログ記事用の図解を作成したい場合
- ユーザーが「図を作って」「ダイアグラムを生成して」などと依頼した場合
- アーキテクチャ図、フロー図、関係図、比較図が必要な場合
- SEO向上のため記事に図解を挿入したい場合

## Supported Diagram Patterns

### 1. アーキテクチャ図
- **レイヤードアーキテクチャ**: 水平層の表現
- **マイクロサービス**: サービス間通信の視覚化
- **イベント駆動**: イベントフローの表現

### 2. フロー図
- **プロセスフロー**: ステップバイステップの処理
- **データフロー**: データの変換と移動
- **ユーザーフロー**: ユーザーインタラクション

### 3. 関係図
- **エンティティ関係図**: データモデル
- **クラス図**: オブジェクト関係
- **シーケンス図**: 時系列の相互作用

### 4. 比較図
- **Before/After**: 改善前後の対比
- **オプション比較**: 複数選択肢の並列表示
- **パフォーマンス比較**: メトリクスの視覚化

### 5. コンポーネント図
- **システム構成**: コンポーネント間の依存関係
- **デプロイメント図**: 物理的な配置

### 6. 概念図
- **コンセプトマップ**: 概念間の関係
- **ツリー構造**: 階層的な情報

## Design Specifications

### サイズとフォーマット
- **推奨サイズ**: 1280 x 720 px (16:9)
- **viewBox**: `0 0 1280 720`
- **フォーマット**: SVG 1.1
- **保存先**: `docs/article/[feature-name]/images/`

**保存先の例**:
- `docs/article/tmp-driven-development/images/architecture-diagram.svg`
- `docs/article/uv-workspace/images/flow-diagram.svg`

### アクセシビリティ要件
- **コントラスト比**: WCAG Level AA準拠 (4.5:1以上)
- **代替テキスト**: `<title>` と `<desc>` 要素を含める
- **色依存の回避**: 色 + 形状 + パターンの組み合わせ
- **テキストサイズ**: 最小14px以上

### デザインガイドライン
- **シンプルさ優先**: 詰め込みすぎない
- **適切な余白**: 要素間に十分なスペース
- **文字間隔**: 読みやすい間隔を保つ
- **グラデーション**: 使用を控える
- **色数制限**: 過剰な色情報を避ける (3-5色推奨)

### Material Icons 使用
- **アイコンソース**: https://fonts.google.com/icons
- **形式**: SVG埋め込み
- **サイズ**: 24px, 32px, 48px (用途に応じて)
- **スタイル**: Outlined, Filled, Rounded から選択

## Usage Flow

### 1. ユーザーからの依頼を確認

ユーザーが以下の情報を提供しているか確認してください：
- 図解のタイプ (アーキテクチャ、フロー、関係、比較など)
- 含めるべき要素 (コンポーネント、ステップ、関係など)
- 特記事項 (色の好み、強調すべき部分など)

### 2. 不足情報の確認

必要に応じて以下を質問してください：
- 図解のタイトル
- 主要な要素とその関係
- 強調すべきポイント
- 配色の好み (あれば)

### 3. SVG生成

以下の要件を満たすSVGを生成してください：

#### 基本構造

``````xml
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     viewBox="0 0 1280 720"
     width="1280"
     height="720"
     role="img"
     aria-labelledby="diagram-title diagram-desc">

  <title id="diagram-title">[図解のタイトル]</title>
  <desc id="diagram-desc">[図解の説明]</desc>

  <defs>
    <!-- 再利用可能な要素を定義 -->
  </defs>

  <!-- 図解の内容 -->

</svg>
``````

#### 推奨カラーパレット

アクセシビリティを考慮した配色例：

```
Primary:   #2196F3 (青)
Secondary: #4CAF50 (緑)
Accent:    #FF9800 (オレンジ)
Text:      #212121 (濃いグレー)
BG:        #FFFFFF (白)
Border:    #BDBDBD (グレー)
```

### 4. 保存先の確認

ユーザーに記事のディレクトリを確認してください：

```
どの記事用の図解ですか？
例: tmp-driven-development, uv-workspace など
```

### 5. ファイル保存

確認した記事ディレクトリの `images/` フォルダに保存してください：

```
docs/article/[feature-name]/images/[説明的なファイル名].svg
```

**保存パスの例**:
- `docs/article/tmp-driven-development/images/architecture-diagram.svg`
- `docs/article/uv-workspace/images/workflow-flow.svg`
- `docs/article/html-to-markdown-converter/images/before-after-comparison.svg`

**ファイル名の命名規則**:
- 小文字とハイフンを使用
- 図解の内容が分かる名前
- パターンを含めても良い (例: `flow-user-auth.svg`, `arch-layered.svg`)

### 6. ユーザーへの報告

以下の情報をユーザーに報告してください：
- 生成した図解のタイプ
- 保存先パス
- 含まれる主要要素
- アクセシビリティ対応状況
- 次のステップ（PNG変換の提案）

## Response to User

### 成功時

```
✅ SVG図解を生成しました。

【図解情報】
- タイプ: [パターン名]
- タイトル: [タイトル]
- サイズ: 1280 x 720 px (16:9)
- 保存先: docs/article/[feature-name]/images/[ファイル名].svg

【アクセシビリティ】
- コントラスト比: WCAG Level AA準拠
- 代替テキスト: 含まれています
- Material Icons: [使用数]個使用

【次のステップ】
PNG形式に変換する場合は、svg-to-png Skillを使用するか、以下のコマンドを実行してください：
```bash
uv run --package sios-tech-lab-analytics-ga4-tools svg2png docs/article/[feature-name]/images/[ファイル名].svg
```
```

### 確認が必要な場合

```
📝 図解の詳細を確認させてください。

以下の情報を教えていただけますか？
- [質問1]
- [質問2]
- [質問3]
```

## Important Notes

1. **viewBox設定**: 必ず `viewBox="0 0 1280 720"` を設定してください
2. **アクセシビリティ**: `<title>` と `<desc>` は必須です
3. **Material Icons**: SVGパスとして埋め込んでください (フォント参照は避ける)
4. **コントラスト**: テキストと背景のコントラスト比を4.5:1以上に保ってください
5. **シンプルさ**: 情報を詰め込みすぎず、適切な余白を確保してください
6. **再利用性**: `<defs>` を使って再利用可能な要素を定義してください

## Design Pattern Examples

### アーキテクチャ図の例

``````xml
<!-- レイヤードアーキテクチャ -->
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720">
  <title>レイヤードアーキテクチャ</title>
  <desc>3層アーキテクチャの構成図</desc>

  <!-- Presentation Layer -->
  <rect x="200" y="100" width="880" height="120"
        fill="#E3F2FD" stroke="#2196F3" stroke-width="2"/>
  <text x="640" y="170" text-anchor="middle"
        font-size="24" fill="#212121">Presentation Layer</text>

  <!-- Business Logic Layer -->
  <rect x="200" y="260" width="880" height="120"
        fill="#E8F5E9" stroke="#4CAF50" stroke-width="2"/>
  <text x="640" y="330" text-anchor="middle"
        font-size="24" fill="#212121">Business Logic Layer</text>

  <!-- Data Access Layer -->
  <rect x="200" y="420" width="880" height="120"
        fill="#FFF3E0" stroke="#FF9800" stroke-width="2"/>
  <text x="640" y="490" text-anchor="middle"
        font-size="24" fill="#212121">Data Access Layer</text>

  <!-- Arrows -->
  <path d="M 640 220 L 640 260"
        stroke="#212121" stroke-width="2"
        marker-end="url(#arrowhead)"/>
  <path d="M 640 380 L 640 420"
        stroke="#212121" stroke-width="2"
        marker-end="url(#arrowhead)"/>

  <defs>
    <marker id="arrowhead" markerWidth="10" markerHeight="10"
            refX="5" refY="5" orient="auto">
      <polygon points="0 0, 10 5, 0 10" fill="#212121"/>
    </marker>
  </defs>
</svg>
``````

### フロー図の例

``````xml
<!-- シンプルなプロセスフロー -->
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720">
  <title>ユーザー認証フロー</title>
  <desc>ログインからセッション確立までのフロー</desc>

  <!-- Start -->
  <ellipse cx="200" cy="100" rx="80" ry="40"
           fill="#4CAF50" stroke="#2E7D32" stroke-width="2"/>
  <text x="200" y="110" text-anchor="middle"
        font-size="18" fill="#FFFFFF">開始</text>

  <!-- Process 1 -->
  <rect x="120" y="180" width="160" height="60" rx="5"
        fill="#2196F3" stroke="#1976D2" stroke-width="2"/>
  <text x="200" y="215" text-anchor="middle"
        font-size="16" fill="#FFFFFF">認証情報入力</text>

  <!-- Process 2 -->
  <rect x="120" y="280" width="160" height="60" rx="5"
        fill="#2196F3" stroke="#1976D2" stroke-width="2"/>
  <text x="200" y="315" text-anchor="middle"
        font-size="16" fill="#FFFFFF">検証処理</text>

  <!-- End -->
  <ellipse cx="200" cy="400" rx="80" ry="40"
           fill="#F44336" stroke="#C62828" stroke-width="2"/>
  <text x="200" y="410" text-anchor="middle"
        font-size="18" fill="#FFFFFF">完了</text>

  <!-- Arrows -->
  <path d="M 200 140 L 200 180" stroke="#212121" stroke-width="2"
        marker-end="url(#arrowhead)"/>
  <path d="M 200 240 L 200 280" stroke="#212121" stroke-width="2"
        marker-end="url(#arrowhead)"/>
  <path d="M 200 340 L 200 360" stroke="#212121" stroke-width="2"
        marker-end="url(#arrowhead)"/>

  <defs>
    <marker id="arrowhead" markerWidth="10" markerHeight="10"
            refX="5" refY="5" orient="auto">
      <polygon points="0 0, 10 5, 0 10" fill="#212121"/>
    </marker>
  </defs>
</svg>
``````

## Material Icons Integration

Material Iconsを使用する場合は、SVGパスとして埋め込んでください。

### アイコン取得方法

1. https://fonts.google.com/icons にアクセス
2. 使用したいアイコンを選択
3. "SVG" タブから `<path>` 要素をコピー
4. 図解のSVG内に埋め込む

### 埋め込み例

``````xml
<!-- Database アイコンの例 -->
<g transform="translate(100, 100)">
  <path d="M12,3C7.58,3 4,4.79 4,7C4,9.21 7.58,11 12,11C16.42,11 20,9.21 20,7C20,4.79 16.42,3 12,3M4,9V12C4,14.21 7.58,16 12,16C16.42,16 20,14.21 20,12V9C20,11.21 16.42,13 12,13C7.58,13 4,11.21 4,9M4,14V17C4,19.21 7.58,21 12,21C16.42,21 20,19.21 20,17V14C20,16.21 16.42,18 12,18C7.58,18 4,16.21 4,14Z"
        fill="#2196F3"/>
</g>
``````

## Related Skills

- **svg-to-png**: 生成したSVGをPNG形式に変換
- **diagram-generator-html**: HTMLで図解を生成（Tailwind CSS使用）
- **html-to-png**: HTML→PNG変換Skill

## Related Documentation

詳細な設計情報は以下を参照：
- `docs/research/blog-diagram-design-patterns.md`: デザインパターン研究
- Material Icons: https://fonts.google.com/icons
- WCAG Guidelines: https://www.w3.org/WAI/WCAG21/quickref/

## 依存関係

依存関係なし。SVGはテキストとしてRead/Writeツールのみで直接記述するため、追加のソフトウェア・ライブラリ・他スキルは不要（PNG変換したい場合に `svg-to-png` 等の関連スキルを任意で使うことはあるが、本スキル自体の実行に必須ではない）。
