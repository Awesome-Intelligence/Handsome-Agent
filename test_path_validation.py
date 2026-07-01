"""测试路径验证函数"""
from tools.skill_manager_tool import _validate_file_path, _resolve_skill_target
from pathlib import Path

# 测试 _validate_file_path 边界情况
tests = [
    # 正常路径
    ("references/test.md", None),
    # 路径遍历尝试
    ("../etc/passwd", "Path traversal ('..') is not allowed."),
    ("references/../../../etc/passwd", "Path traversal ('..') is not allowed."),
    ("references/../..wrong.txt", "Path traversal ('..') is not allowed."),
    # 绝对路径
    ("/etc/passwd", "Absolute paths are not allowed. Use relative paths."),
    # 空路径
    ("", "file_path is required."),
    # 不允许的子目录
    ("forbidden/test.txt", "File must be under one of: assets, references, scripts, templates. Got: 'forbidden/test.txt'"),
    # 只有目录没有文件
    ("references", "Provide a file path, not just a directory. Example: 'references/myfile.md'"),
    # 隐藏文件
    ("references/.hidden", "Hidden files (starting with '.') are not allowed."),
    # 正常多级路径
    ("references/subdir/test.txt", None),
    ("templates/../references/test.txt", "Path traversal ('..') is not allowed."),
]

print("Testing _validate_file_path:")
all_passed = True
for path, expected in tests:
    result = _validate_file_path(path)
    status = "PASS" if result == expected else "FAIL"
    if result != expected:
        all_passed = False
        print(f"FAIL: {path!r}")
        print(f"  Expected: {expected!r}")
        print(f"  Got: {result!r}")
    else:
        result_str = result if result else "valid"
        print(f'PASS: {path!r} -> {result_str}')

print(f"\nAll _validate_file_path tests passed: {all_passed}")

# 测试 _resolve_skill_target
print("\nTesting _resolve_skill_target:")
skill_dir = Path.home() / ".handsome_agent" / "skills" / "test_skill"
skill_dir.mkdir(parents=True, exist_ok=True)

resolve_tests = [
    # 正常路径
    ("references/test.md", True, None),
    # 路径遍历 - 即使通过初步验证，resolve后应该被拦截
    ("../etc/passwd", False, "Path traversal ('..') is not allowed."),
]

for path, should_succeed, expected_error in resolve_tests:
    target, error = _resolve_skill_target(skill_dir, path)
    if should_succeed:
        if target is not None:
            print(f"PASS: {path!r} -> resolved successfully")
        else:
            print(f"FAIL: {path!r} should succeed but got error: {error}")
            all_passed = False
    else:
        if error == expected_error:
            print(f"PASS: {path!r} -> blocked with: {error}")
        else:
            print(f"FAIL: {path!r}")
            print(f"  Expected error: {expected_error!r}")
            print(f"  Got error: {error!r}")
            all_passed = False

print(f"\nAll tests passed: {all_passed}")
