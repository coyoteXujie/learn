"""
将 OAuth学习指南.md 转换为两个版本：
  1. OAuth学习指南-插图版.md — PlantUML 替换为图片引用
  2. OAuth学习指南-代码版.md — 保留原始 PlantUML 代码块
"""

import re
import os


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    src_path = os.path.join(base_dir, "OAuth学习指南.md")

    with open(src_path, "r", encoding="utf-8") as f:
        content = f.read()

    image_names = [
        "01_四大角色交互流程",
        "02_授权码模式详细流程",
        "03_隐式模式(已废弃)",
        "04_密码模式(不推荐)",
        "05_客户端凭证模式",
        "06_Provider需要实现的模块",
        "07_普通登录vs_OAuth登录对比",
        "08_Token类型对比",
    ]

    pattern = re.compile(r"```plantuml\s*\n(.*?)\n```", re.DOTALL)
    matches = list(pattern.finditer(content))

    # 版本1：插图版 — 替换为图片
    image_content = content
    for i, match in enumerate(matches):
        name = image_names[i] if i < len(image_names) else f"diagram_{i + 1}"
        img_md = f"![{name}](images/{name}.png)"
        image_content = image_content.replace(match.group(0), img_md, 1)

    img_output = os.path.join(base_dir, "OAuth学习指南-插图版.md")
    with open(img_output, "w", encoding="utf-8") as f:
        f.write(image_content)
    print(f"✅ 插图版: {img_output}")

    # 版本2：代码版 — 原样保留（就是当前文件，复制一份）
    code_output = os.path.join(base_dir, "OAuth学习指南-代码版.md")
    with open(code_output, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ 代码版: {code_output}")


if __name__ == "__main__":
    main()
