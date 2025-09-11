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

import collections
import dataclasses
import json
from typing import Dict, Optional, Sequence, Union

from instruction_following_eval import instructions_registry


@dataclasses.dataclass
class InputExample:
  key: int
  instruction_id_list: list[str]
  prompt: str
  kwargs: list[Dict[str, Optional[Union[str, int]]]]


@dataclasses.dataclass
class OutputExample:
  instruction_id_list: list[str]
  prompt: str
  response: str
  follow_all_instructions: bool
  follow_instruction_list: list[bool]


def read_prompt_list(input_jsonl_filename):
  """jsonlから入力を読み込みます。"""
  inputs = []
  with open(input_jsonl_filename, "r") as f:
    for l in f:
      example = json.loads(l)
      inputs.append(
          InputExample(key=example["key"],
                       instruction_id_list=example["instruction_id_list"],
                       prompt=example["prompt"],
                       kwargs=example["kwargs"]))
  return inputs


def write_outputs(output_jsonl_filename, outputs):
  """出力をjsonlに書き込みます。"""
  assert outputs
  with open(output_jsonl_filename, "w") as f:
    for o in outputs:
      f.write(
          json.dumps(
              {
                  attr_name: o.__getattribute__(attr_name)
                  for attr_name in [
                      name for name in dir(o) if not name.startswith("_")
                  ]
              }
          )
      )
      f.write("\n")


def test_instruction_following_strict(
    inp,
    prompt_to_response,
):
  """指示に従っているかどうかを確認するために応答をテストします。"""
  if inp.prompt not in prompt_to_response:
    # プロンプトに対応するレスポンスが見つからない場合、空のレスポンスで処理
    response = ""
  else:
    response = prompt_to_response[inp.prompt]
  instruction_list = inp.instruction_id_list
  is_following_list = []

  for index, instruction_id in enumerate(instruction_list):
    instruction_cls = instructions_registry.INSTRUCTION_DICT[instruction_id]
    instruction = instruction_cls(instruction_id)

    # 指示クラスが受け取るパラメータのみをフィルタリング
    kwargs = inp.kwargs[index]
    
    # 指示クラスが受け取るパラメータのキーを取得
    try:
      args_keys = instruction.get_instruction_args_keys()
      if args_keys:
        filtered_kwargs = {k: v for k, v in kwargs.items() if k in args_keys}
        # 必須パラメータが不足している場合はスキップ
        if not filtered_kwargs and args_keys:
          instruction.build_description()
        else:
          instruction.build_description(**filtered_kwargs)
      else:
        instruction.build_description()
    except (AttributeError, ValueError):
      # get_instruction_args_keysメソッドがない場合や必須パラメータが不足している場合は、デフォルトでbuild_descriptionを呼ぶ
      try:
        instruction.build_description()
      except ValueError:
        # 必須パラメータが不足している場合はスキップ
        pass
    
    # promptパラメータが必要な場合は追加
    try:
      args = instruction.get_instruction_args()
      if args and "prompt" in args:
        instruction.build_description(prompt=inp.prompt)
    except AttributeError:
      # get_instruction_argsメソッドがない場合はスキップ
      pass

    if response.strip() and instruction.check_following(response):
      is_following_list.append(True)
    else:
      is_following_list.append(False)

  return OutputExample(
      instruction_id_list=inp.instruction_id_list,
      prompt=inp.prompt,
      response=response,
      follow_all_instructions=all(is_following_list),
      follow_instruction_list=is_following_list,
  )


def test_instruction_following_loose(
    inp,
    prompt_to_response,
):
  """指示に従うための上限について応答をテストします。"""
  if inp.prompt not in prompt_to_response:
    # プロンプトに対応するレスポンスが見つからない場合、空のレスポンスで処理
    response = ""
  else:
    response = prompt_to_response[inp.prompt]
  r = response.split("\n")
  response_remove_first = "\n".join(r[1:]).strip()
  response_remove_last = "\n".join(r[:-1]).strip()
  response_remove_both = "\n".join(r[1:-1]).strip()
  revised_response = response.replace("*", "")
  revised_response_remove_first = response_remove_first.replace("*", "")
  revised_response_remove_last = response_remove_last.replace("*", "")
  revised_response_remove_both = response_remove_both.replace("*", "")
  all_responses = [
      response,
      revised_response,
      response_remove_first,
      response_remove_last,
      response_remove_both,
      revised_response_remove_first,
      revised_response_remove_last,
      revised_response_remove_both,
  ]
  instruction_list = inp.instruction_id_list
  is_following_list = []

  for index, instruction_id in enumerate(instruction_list):
    instruction_cls = instructions_registry.INSTRUCTION_DICT[instruction_id]
    instruction = instruction_cls(instruction_id)

    # 指示クラスが受け取るパラメータのみをフィルタリング
    kwargs = inp.kwargs[index]
    
    # 指示クラスが受け取るパラメータのキーを取得
    try:
      args_keys = instruction.get_instruction_args_keys()
      if args_keys:
        filtered_kwargs = {k: v for k, v in kwargs.items() if k in args_keys}
        # 必須パラメータが不足している場合はスキップ
        if not filtered_kwargs and args_keys:
          instruction.build_description()
        else:
          instruction.build_description(**filtered_kwargs)
      else:
        instruction.build_description()
    except (AttributeError, ValueError):
      # get_instruction_args_keysメソッドがない場合や必須パラメータが不足している場合は、デフォルトでbuild_descriptionを呼ぶ
      try:
        instruction.build_description()
      except ValueError:
        # 必須パラメータが不足している場合はスキップ
        pass
    
    # promptパラメータが必要な場合は追加
    try:
      args = instruction.get_instruction_args()
      if args and "prompt" in args:
        instruction.build_description(prompt=inp.prompt)
    except AttributeError:
      # get_instruction_argsメソッドがない場合はスキップ
      pass

    is_following = False
    for r in all_responses:
      if r.strip() and instruction.check_following(r):
        is_following = True
        break

    is_following_list.append(is_following)

  return OutputExample(
      instruction_id_list=inp.instruction_id_list,
      prompt=inp.prompt,
      response=response,
      follow_all_instructions=all(is_following_list),
      follow_instruction_list=is_following_list,
  )


def read_prompt_to_response_dict(input_jsonl_filename):
  """プロンプトと応答を対応付ける辞書を作成します。"""
  return_dict = {}
  with open(input_jsonl_filename, "r") as f:
    for l in f:
      example = json.loads(l)
      return_dict[example["prompt"]] = example["response"]
  return return_dict


def print_report(outputs):
  """精度スコアのレポートを出力します。"""

  prompt_total = 0
  prompt_correct = 0
  instruction_total = 0
  instruction_correct = 0

  tier0_total = collections.defaultdict(int)
  tier0_correct = collections.defaultdict(int)

  tier1_total = collections.defaultdict(int)
  tier1_correct = collections.defaultdict(int)

  for example in outputs:
    follow_instruction_list = example.follow_instruction_list
    instruction_id_list = example.instruction_id_list

    prompt_total += 1
    if all(follow_instruction_list):
      prompt_correct += 1

    instruction_total += len(instruction_id_list)
    instruction_correct += sum(follow_instruction_list)

    for instruction_id, followed_or_not in zip(
        instruction_id_list, follow_instruction_list
    ):
      instruction_id = instruction_id.split(":")[0]
      tier0_total[instruction_id] += 1
      if followed_or_not:
        tier0_correct[instruction_id] += 1

    for instruction_id, followed_or_not in zip(
        instruction_id_list, follow_instruction_list
    ):
      tier1_total[instruction_id] += 1
      if followed_or_not:
        tier1_correct[instruction_id] += 1

  print(f"prompt-level: {prompt_correct / prompt_total}")
  print(f"instruction-level: {instruction_correct / instruction_total}")
  print()
  for instruction_id in sorted(tier0_total.keys()):
    accuracy = tier0_correct[instruction_id] / tier0_total[instruction_id]
    print(f"{instruction_id} {accuracy}")
  print()
  for instruction_id in sorted(tier1_total.keys()):
    accuracy = tier1_correct[instruction_id] / tier1_total[instruction_id]
    print(f"{instruction_id} {accuracy}")

