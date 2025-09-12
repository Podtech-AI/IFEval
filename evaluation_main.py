# coding=utf-8
# Copyright 2025 The Google Research Authors.
#
# Apache License, Version 2.0（「ライセンス」）に基づいてライセンスされています。
# このファイルは、ライセンスに準拠していない限り使用できません。
# ライセンスのコピーは以下で入手できます：
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# 適用法で要求されるか、書面で合意されない限り、ライセンスに基づいて
# 配布されるソフトウェアは「現状のまま」で配布され、
# 明示的または黙示的を問わず、いかなる保証も条件もありません。
# 詳細については、ライセンスを参照してください。

"""指示追従評価のバイナリ。README.mdを参照してください。"""

import os
from typing import Sequence

from absl import app
from absl import flags
from absl import logging

from instruction_following_eval import evaluation_lib

import nltk
nltk.download('punkt_tab')

_INPUT_DATA = flags.DEFINE_string(
    "input_data", None, "入力データへのパス", required=True
)

_INPUT_RESPONSE_DATA = flags.DEFINE_string(
    "input_response_data", None, "入力応答データへのパス", required=False
)

_USE_GPT = flags.DEFINE_bool(
    "use_gpt", False, "GPTモデルを使用して応答を生成するかどうか"
)

_GPT_MODEL = flags.DEFINE_string(
    "gpt_model", "gpt-3.5-turbo", "使用するGPTモデル名（gpt-3.5-turbo, gpt-4, gpt-4-turbo等）"
)

_OPENAI_API_KEY = flags.DEFINE_string(
    "openai_api_key", None, "OpenAI APIキー（環境変数OPENAI_API_KEYでも設定可能）"
)

_MODEL_PROVIDER = flags.DEFINE_string(
    "model_provider", "openai", "使用するAIモデルプロバイダー（openai, anthropic, google）"
)

_MODEL_NAME = flags.DEFINE_string(
    "model_name", None, "使用するモデル名（指定されない場合、プロバイダーのデフォルトを使用）"
)

_API_KEY = flags.DEFINE_string(
    "api_key", None, "API キー（環境変数でも設定可能：OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_AI_API_KEY）"
)

_OUTPUT_DIR = flags.DEFINE_string(
    "output_dir",
    None,
    "推論と評価結果の出力ディレクトリ。",
    required=True,
)


def main(argv):
  if len(argv) > 1:
    raise app.UsageError("コマンドライン引数が多すぎます。")

  inputs = evaluation_lib.read_prompt_list(_INPUT_DATA.value)
  
  # レスポンスデータの取得方法を判定
  if _INPUT_RESPONSE_DATA.value:
    # 既存の応答データがある場合はそれを使用
    prompt_to_response = evaluation_lib.read_prompt_to_response_dict(
        _INPUT_RESPONSE_DATA.value)
    logging.info("既存の応答データを使用します: %s", _INPUT_RESPONSE_DATA.value)
  elif _USE_GPT.value:
    # 旧来のGPTフラグが有効な場合（後方互換性）
    logging.info("GPTモデルを使用して応答を生成します...")
    prompt_to_response = evaluation_lib.generate_responses_with_gpt(
        inputs, 
        model=_GPT_MODEL.value,
        api_key=_OPENAI_API_KEY.value
    )
  else:
    # 新しいモデル選択フラグを使用
    provider = _MODEL_PROVIDER.value
    model_name = _MODEL_NAME.value
    api_key = _API_KEY.value
    
    logging.info("プロバイダー '%s' のモデルを使用して応答を生成します...", provider)
    if model_name:
      logging.info("使用モデル: %s", model_name)
    
    prompt_to_response = evaluation_lib.generate_responses(
        inputs,
        provider=provider,
        model=model_name,
        api_key=api_key
    )

  # 指示追従の結果を取得
  for func, output_file_name in [
      (evaluation_lib.test_instruction_following_strict, "eval_results_strict"),
      (evaluation_lib.test_instruction_following_loose, "eval_results_loose"),
  ]:
    logging.info("Generating %s...", output_file_name)
    outputs = []
    for inp in inputs:
      outputs.append(func(inp, prompt_to_response))
    follow_all_instructions = [o.follow_all_instructions for o in outputs]
    accuracy = sum(follow_all_instructions) / len(outputs)
    logging.info("Accuracy: %f", accuracy)

    output_file_name = os.path.join(
        _OUTPUT_DIR.value, output_file_name + ".jsonl"
    )
    evaluation_lib.write_outputs(output_file_name, outputs)
    logging.info("Generated: %s", output_file_name)

    # 指示追従精度レポートを出力します。
    print("=" * 64)
    print(f"{output_file_name} Accuracy Scores:")
    evaluation_lib.print_report(outputs)


if __name__ == "__main__":
  app.run(main)
