# 論文要約 — example_papers (1/1)

生成日時: 2026-03-02 15:00 JST
言語: 日本語
ソースPDF数: 3

---

## Attention Is All You Need
- **著者**: Ashish Vaswani et al. (Google Brain)
- **概要**: 本研究ではTransformerアーキテクチャを提案した。従来のRNNやCNNに依存しない、自己注意機構のみに基づくモデルにより、機械翻訳タスクで新たなSOTAを達成した。
- **手法**: Multi-Head Self-Attention と Positional Encoding を組み合わせたEncoder-Decoderモデル
- **結果・貢献**: WMT 2014 英独翻訳で BLEU 28.4 を達成。学習時間を大幅に短縮。
- **キーワード**: Transformer, Self-Attention, 機械翻訳, Encoder-Decoder

## BERT: Pre-training of Deep Bidirectional Transformers
- **著者**: Jacob Devlin et al. (Google AI Language)
- **概要**: 双方向Transformerの事前学習モデルBERTを提案。多様なNLPタスクでファインチューニングにより高精度を実現。
- **手法**: Masked Language Model と Next Sentence Prediction による事前学習
- **結果・貢献**: 11のNLPベンチマークでSOTAを更新。
- **キーワード**: BERT, 事前学習, NLP, Transfer Learning

## GPT-3: Language Models are Few-Shot Learners
- **著者**: Tom B. Brown et al. (OpenAI)
- **概要**: 1750億パラメータの大規模言語モデルGPT-3を提案。Few-shot学習により、タスク固有のファインチューニングなしで多様なNLPタスクを実行可能であることを示した。
- **手法**: 大規模Transformerデコーダーモデルによる自己回帰的事前学習。In-context learningを活用。
- **結果・貢献**: 翻訳、QA、文章生成など多数のベンチマークでfew-shot設定において高い性能を達成。
- **キーワード**: GPT-3, Few-Shot Learning, 大規模言語モデル, In-Context Learning
