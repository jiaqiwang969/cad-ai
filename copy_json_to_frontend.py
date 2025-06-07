import shutil
from pathlib import Path

# 路径配置
BACKEND_ROOT = Path(".")
FRONTEND_PUBLIC = BACKEND_ROOT / "cad-ai-frontend" / "public"

# 1. 复制分类树
src_tree = BACKEND_ROOT / "results" / "cache"
dst_tree = FRONTEND_PUBLIC / "classification_tree.json"
tree_files = list(src_tree.glob("classification_tree*.json"))
if tree_files:
    shutil.copy(tree_files[0], dst_tree)
    print(f"✅ 分类树已复制到 {dst_tree}")
else:
    print("❌ 未找到分类树文件")

# 2. 复制产品链接
src_products = src_tree / "products"
dst_products = FRONTEND_PUBLIC / "products"
dst_products.mkdir(exist_ok=True)
for f in src_products.glob("*.json"):
    shutil.copy(f, dst_products / f.name)
print(f"✅ 产品链接已复制到 {dst_products}")

# 3. 复制产品规格（可选，后续用到时再复制）
src_specs = src_tree / "specifications"
dst_specs = FRONTEND_PUBLIC / "specifications"
dst_specs.mkdir(exist_ok=True)
for f in src_specs.glob("*.json"):
    shutil.copy(f, dst_specs / f.name)
print(f"✅ 产品规格已复制到 {dst_specs}") 