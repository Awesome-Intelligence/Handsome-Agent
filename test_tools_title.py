#!/usr/bin/env python3
import os
os.environ['HANDSOME_LANGUAGE'] = 'en'
from common.i18n import t, reset_language_cache
reset_language_cache()

print("menu.tools.title =", t("menu.tools.title"))
print("menu.tools.label =", t("menu.tools.label"))
print()

# 模拟 _translate_menu 的行为
key = "🛠️ 工具与扩展"
print(f't("{key}") =', t(key))
