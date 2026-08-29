# Transcript Reconciler

同じ会議を別々のAIや入力経路で書き起こした複数ファイルを突き合わせ、話者境界をレビュー可能な形で統合するための小さなCLIとCodex Skillです。

CSVなどの読みやすいチャンクを骨格にし、VTT/SRTの細粒度な時刻・話者情報を重ねます。自動判定が危険な複数話者区間、短い相づち、根拠不足、話者不一致はJSONLのレビュー候補として残し、会議別の明示的なオーバーライドで確定します。

## できること

- CSV、VTT、SRT、Markdown、TXTを共通セグメントへ変換
- 骨格ソースの各行を「開始時刻から次行の開始時刻まで」として細粒度ソースを対応付け
- 共有文字列と時間重複から話者ごとの根拠スコアを計算
- 複数話者、根拠なし、低いスコア差、未登録話者などをレビュー候補化
- 会議別JSON設定による話者名、固有語、チャンク分割の再現可能な上書き
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
