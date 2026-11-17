# -*- coding: utf-8 -*-
"""PPT QA: 边界越界 + 文本溢出粗估 + 内容完整性"""
from pptx import Presentation
from pptx.util import Emu

EMU_IN = 914400
prs = Presentation("shopify_admin_architecture.pptx")
W, H = prs.slide_width / EMU_IN, prs.slide_height / EMU_IN
print(f"slide size: {W:.2f} x {H:.2f} in, slides: {len(prs.slides)}")
issues = []
for idx, slide in enumerate(prs.slides, 1):
    texts, pics = [], 0
    for sh in slide.shapes:
        x, y = sh.left / EMU_IN, sh.top / EMU_IN
        w, h = sh.width / EMU_IN, sh.height / EMU_IN
        if x < -1.2 or y < -1.8 or x + w > W + 1.2 or y + h > H + 1.2:
            issues.append(f"S{idx}: 装饰元素严重越界 {sh.shape_type} at ({x:.2f},{y:.2f}) {w:.2f}x{h:.2f}")
        elif (x < -0.01 or y < -0.01 or x + w > W + 0.01 or y + h > H + 0.01) and "OVAL" not in str(sh.shape_type):
            issues.append(f"S{idx}: 越界 {sh.shape_type} at ({x:.2f},{y:.2f}) {w:.2f}x{h:.2f}")
        if sh.shape_type == 13:  # picture
            pics += 1
        if sh.has_text_frame:
            t = sh.text_frame.text.strip()
            if t:
                texts.append(t)
                # 溢出粗估：中文按字号全宽估行数
                for para in sh.text_frame.paragraphs:
                    line = "".join(r.text for r in para.runs)
                    if not line:
                        continue
                    fs = max((r.font.size.pt if r.font.size else 12) for r in para.runs)
                    # 中文字符≈fs pt宽, ascii≈0.55*fs
                    width_pt = sum((fs if ord(c) > 0x2E80 else 0.55 * fs) for c in line)
                    lines = max(1, -(-width_pt // (w * 72)))
                    need_h = lines * fs * 1.35 / 72
                    if need_h > h + 0.12:
                        issues.append(f"S{idx}: 可能溢出 fs={fs:.0f} 需{need_h:.2f}in 框高{h:.2f}in: {line[:28]}")
    print(f"S{idx}: shapes={len(slide.shapes)} pics={pics} text_head={' | '.join(texts[:2])[:70]}")
print("\n== ISSUES ==" if issues else "\n== NO ISSUES ==")
for i in issues:
    print(" ", i)
