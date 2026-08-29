# Transcript Reconciler

同じ会議を別々のAIや入力経路で書き起こした複数ファイルを突き合わせ、話者境界をレビュー可能な形で統合するための小さなCLIとCodex Skillです。

CSVなどの読みやすいチャンクを骨格にし、VTT/SRTの細粒度な時刻・話者情報を重ねます。自動判定が危険な複数話者区間、短い相づち、根拠不足、話者不一致はJSONLのレビュー候補として残し、会議別の明示的なオーバーライドで確定します。

## ツールの意図

このツールは、AIによる発話分析ツール「toitta」と他のAI書き起こしツールを併用し、複数の発話録を突き合わせることで、話者分離精度と書き起こし精度を高めた発話録を生成します。
そうして生成した精度の高い発話録を、再び「toitta」に投入することで、精度の高い切片を生成することができます。

## 添付するファイル

添付するファイルは、それぞれ以下のツールからダウンロードしてください。

### CSV

- AIによる発話分析ツール「toitta」に動画をいったんアップロードし、「書き起こし」だけをダウンロードしてください。

### VTT、SRT、Markdown、TXT

- Zoom、Microsoft Teams、Google Meetなどのツールで書き起こした発話録をダウンロードしてください。

## できること

- CSV、VTT、SRT、Markdown、TXTを共通セグメントへ変換
- 骨格ソースの各行を「開始時刻から次行の開始時刻まで」として細粒度ソースを対応付け
- 共有文字列と時間重複から話者ごとの根拠スコアを計算
- 複数話者、根拠なし、低いスコア差、未登録話者などをレビュー候補化
- 会議別JSON設定による本文のみ・話者のみ・チャンク分割の再現可能な上書き
- 本文修正と話者境界の確定を区別し、未解決の話者候補を保持
- 存在しないセグメント番号を参照する古い上書き設定をエラーとして検出
- 発話者ラベル、空行、禁止語、隣接重複、引用符、見出しの機械監査
- Codexが手順とチェックリストを自動参照するSkill

## しないこと

- 曖昧な発話境界を自動的に正解として確定すること
- 音声を確認していないのに、音声との完全一致を保証すること
- ある会議の固有語や話者名を別の会議へ自動適用すること
- 入力にない発話を自然さのために補うこと

## クイックスタート

Python 3.10以上だけで動作し、実行時依存はありません。

```bash
./scripts/transcript-reconcile inspect --config /path/to/session.json

./scripts/transcript-reconcile reconcile \
  --config /path/to/session.json \
  --output /path/to/draft.md \
  --review /path/to/review.jsonl

./scripts/transcript-reconcile audit \
  --config /path/to/session.json \
  --input /path/to/final.md
```

設定の雛形は [`examples/session.example.json`](examples/session.example.json) にあります。実務手順と設定項目は以下を参照してください。

- [Codexへの依頼プロンプト雛形](examples/prompt-template.md)
- [統合作業手順](.agents/skills/merge-transcripts/references/workflow.md)
- [レビュー・完了チェックリスト](.agents/skills/merge-transcripts/references/review-checklist.md)
- [設定リファレンス](.agents/skills/merge-transcripts/references/configuration.md)
- [継続改善の運用](.agents/skills/merge-transcripts/references/maintenance.md)

## Codex Skillの設定

リポジトリ内のSkillをユーザー領域へシンボリックリンクします。

```bash
python3 scripts/install_skill.py
```

既存の同名ファイルや別のリンクは上書きしません。Codexで変更がすぐに見えない場合は、新しいタスクまたはセッションを開始してください。

## 開発と検証

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m compileall -q src scripts
python3 /path/to/skill-creator/scripts/quick_validate.py \
  .agents/skills/merge-transcripts
```

## データ保護

このリポジトリへ顧客の発話録、実名入り設定、クラウドストレージのパス、生成したレビューJSONLをコミットしないでください。回帰テストには合成データまたは不可逆に匿名化した最小例だけを使用します。

案件固有の修正は公開リポジトリへ移さず、入力発話録、セッションJSON、最終発話録を非公開の案件フォルダにまとめて保管してください。最終版へ直接修正を加えたままにせず、セッションJSONから同じ内容を再生成できる状態を正本とします。
