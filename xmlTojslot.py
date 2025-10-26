import json
import re
import tkinter as tk
from tkinter import filedialog, simpledialog
import os

def select_file(title, filetypes):
    root = tk.Tk()
    root.withdraw()
    return filedialog.askopenfilename(title=title, filetypes=filetypes)

def get_weight_input(title):
    while True:
        weight = simpledialog.askfloat(title, f"请输入{title}（0-1）：", minvalue=0, maxvalue=1)
        if weight is not None:
            return weight

def extract_all_target_names(jslot_data):
    target_names = []
    body_morphs = jslot_data.get("bodyMorphs", [])
    for morph in body_morphs:
        has_target_key = False
        for key_item in morph.get("keys", []):
            if key_item.get("key") == "RaceMenuMorphsCBBE.esp":
                has_target_key = True
                break
        if has_target_key and morph.get("name"):
            target_names.append(morph["name"])
    return target_names

def parse_xml_for_value(xml_path, target_name):
    if not os.path.exists(xml_path):
        return {}
    with open(xml_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = [line.strip() for line in f.readlines()]
    value_dict = {}
    for i, line in enumerate(lines):
        if line.startswith('<SetSlider') and f'name="{target_name}"' in line:
            size_match = re.search(r'size="(big|small)"', line)
            value_match = re.search(r'value="(-?\d+)"', line)
            if size_match and value_match:
                value_dict[size_match.group(1)] = float(value_match.group(1))
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if next_line.startswith('<SetSlider') and f'name="{target_name}"' in next_line:
                        next_size = re.search(r'size="(big|small)"', next_line)
                        next_value = re.search(r'value="(-?\d+)"', next_line)
                        if next_size and next_value:
                            value_dict[next_size.group(1)] = float(next_value.group(1))
                break
    return value_dict

def calculate_mapped_value(value_dict, weight):
    if not value_dict:
        return 0.0
    if len(value_dict) == 1:
        return next(iter(value_dict.values()))
    return value_dict.get('small', 0) + (value_dict.get('big', 0) - value_dict.get('small', 0)) * weight

def update_jslot_content(content, target_name, final_value):
    # 支持keys数组中包含多个key对象的情况，精准定位RaceMenuMorphsCBBE.esp对应的value
    pattern = re.compile(
        r'(?s)(\{[^\}]*?"keys"\s*:\s*\[[^\]]*?"key"\s*:\s*"RaceMenuMorphsCBBE\.esp"\s*,\s*"value"\s*:\s*)[-+]?\d*\.?\d+'
        r'([^\]]*\]\s*,\s*"name"\s*:\s*"' + re.escape(target_name) + r'")'
    )
    return pattern.sub(rf'\g<1>{final_value:.2f}\g<2>', content)

def main():
    # 选择文件
    rmPrestFile = select_file("选择RM预设文件（.jslot）", [("JSLOT文件", "*.jslot")])
    if not rmPrestFile:
        print("未选择RM预设文件，程序退出")
        return

    basicShapeFile = select_file("选择基础BS身形文件（.xml）", [("XML文件", "*.xml")])
    if not basicShapeFile:
        print("未选择基础身形文件，程序退出")
        return
    weight1 = get_weight_input("基础身形体重")

    playerShapeFile = select_file("选择玩家BS身形文件（.xml）", [("XML文件", "*.xml")])
    if not playerShapeFile:
        print("未选择玩家身形文件，程序退出")
        return
    weight2 = get_weight_input("玩家身形体重")

    # 读取与解析
    with open(rmPrestFile, 'r', encoding='utf-8') as f:
        jslot_content = f.read()
    try:
        jslot_data = json.loads(jslot_content)
    except json.JSONDecodeError as e:
        print(f"JSLOT文件解析错误：{e}")
        return

    target_names = extract_all_target_names(jslot_data)
    if not target_names:
        print("未找到任何包含'RaceMenuMorphsCBBE.esp'的条目")
        return
    print(f"共找到{len(target_names)}个需要处理的条目：{target_names}")

    # 循环处理
    current_content = jslot_content
    for name in target_names:
        print(f"\n处理条目：{name}")
        
        basic_values = parse_xml_for_value(basicShapeFile, name)
        reverse_value = calculate_mapped_value(basic_values, weight1)
        print(f"基础身形解析结果：{basic_values}，反转值：{reverse_value}")

        player_values = parse_xml_for_value(playerShapeFile, name)
        add_value = calculate_mapped_value(player_values, weight2)
        print(f"玩家身形解析结果：{player_values}，叠加值：{add_value}")

        if not basic_values and not player_values:
            final_value = 0.0
        elif not player_values:
            final_value = (-reverse_value) / 100
        elif not basic_values:
            final_value = add_value / 100
        else:
            final_value = (-reverse_value + add_value) / 100
        print(f"计算得到最终值：{final_value:.2f}")

        original_content = current_content
        current_content = update_jslot_content(current_content, name, final_value)
        if original_content == current_content:
            print(f"警告：未找到'{name}'对应的value位置")
        else:
            print(f"成功更新'{name}'的value值")

    # 生成新文件名（核心修改：使用文件2的名字作为前缀）
    dir_name, original_file_name = os.path.split(rmPrestFile)
    # 获取文件2的纯名称（不含路径和后缀）
    file2_basename = os.path.splitext(os.path.basename(playerShapeFile))[0]
    # 新文件名格式：_文件2名字_原文件名
    new_file_name = f"_{file2_basename}_{original_file_name}"
    new_file_path = os.path.join(dir_name, new_file_name)
    
    with open(new_file_path, 'w', encoding='utf-8') as f:
        f.write(current_content)
    
    print(f"\n处理完成，新文件已保存至: {new_file_path}")

if __name__ == "__main__":
    main()

