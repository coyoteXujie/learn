"""
将 Markdown 中的 PlantUML 代码块渲染为 PNG 图片文件。
使用 PlantUML 在线服务：http://www.plantuml.com/plantuml/png/
"""

import zlib
import re
import os
import urllib.request
import urllib.parse


def plantuml_encode(text):
    """将 PlantUML 文本编码为 URL 安全格式（PlantUML 在线服务使用的编码）"""
    compressed = zlib.compress(text.encode("utf-8"), 9)
    # 去掉 zlib 头部前 2 字节
    b64 = compressed[2:-4]
    # 使用 PlantUML 的自定义字母表编码
    alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_."
    result = []
    for i in range(0, len(b64), 3):
        if i + 2 < len(b64):
            b1, b2, b3 = b64[i], b64[i + 1], b64[i + 2]
            result.append(alphabet[b1 >> 2])
            result.append(alphabet[((b1 & 0x3) << 4) | (b2 >> 4)])
            result.append(alphabet[((b2 & 0xF) << 2) | (b3 >> 6)])
            result.append(alphabet[b3 & 0x3F])
        elif i + 1 < len(b64):
            b1, b2 = b64[i], b64[i + 1]
            result.append(alphabet[b1 >> 2])
            result.append(alphabet[((b1 & 0x3) << 4) | (b2 >> 4)])
            result.append(alphabet[(b2 & 0xF) << 2])
        else:
            b1 = b64[i]
            result.append(alphabet[b1 >> 2])
            result.append(alphabet[(b1 & 0x3) << 4])
    return "".join(result)


def render_plantuml(text, output_path):
    """调用 PlantUML 在线服务渲染为 PNG 并保存"""
    encoded = plantuml_encode(text)
    url = f"http://www.plantuml.com/plantuml/png/{encoded}"
    print(f"  渲染中... ({len(text)} 字符)")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        response = urllib.request.urlopen(req, timeout=30)
        image_data = response.read()
        with open(output_path, "wb") as f:
            f.write(image_data)
        print(f"  ✅ 已保存: {output_path} ({len(image_data)} bytes)")
        return True
    except Exception as e:
        print(f"  ❌ 渲染失败: {e}")
        return False


def main():
    md_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "OAuth学习指南.md")
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")

    os.makedirs(output_dir, exist_ok=True)

    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = r"```plantuml\s*\n(.*?)\n```"
    matches = list(re.finditer(pattern, content, re.DOTALL))

    print(f"找到 {len(matches)} 个 PlantUML 图，开始渲染...\n")

    names = [
        "01_四大角色交互流程",
        "02_授权码模式详细流程",
        "03_隐式模式(已废弃)",
        "04_密码模式(不推荐)",
        "05_客户端凭证模式",
        "06_Provider需要实现的模块",
        "07_普通登录vs_OAuth登录对比",
        "08_Token类型对比",
    ]

    success_count = 0
    for i, match in enumerate(matches):
        name = names[i] if i < len(names) else f"diagram_{i + 1}"
        text = match.group(1).strip()
        if not text.startswith("@startuml"):
            text = "@startuml\n" + text + "\n@enduml"
        output_path = os.path.join(output_dir, f"{name}.png")
        print(f"[{i + 1}/{len(matches)}] {name}")
        if render_plantuml(text, output_path):
            success_count += 1
        print()

    print(f"完成！{success_count}/{len(matches)} 张图片已保存到: {output_dir}")


if __name__ == "__main__":
    main()
