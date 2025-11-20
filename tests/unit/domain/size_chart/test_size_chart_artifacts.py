+# -*- coding: utf-8 -*-
+# filepath: /Users/key27/TELEBOTYLAUKRAINE/tests/unit/domain/size_chart/test_size_chart_artifacts.py
+import pytest
+
+from app.domain.size_chart.interfaces import SizeChartArtifacts
+
+
+def test_artifacts_only_global():
+    artifacts = SizeChartArtifacts()
+    artifacts.register_global("general.png")
+
+    assert artifacts.global_table == "general.png"
+    assert artifacts.product_table is None
+    assert artifacts.ordered_paths() == ["general.png"]
+
+
+def test_artifacts_only_product():
+    artifacts = SizeChartArtifacts()
+    artifacts.register_product("unique.png")
+
+    assert artifacts.product_table == "unique.png"
+    assert artifacts.global_table is None
+    assert artifacts.ordered_paths() == ["unique.png"]
+
+
+def test_artifacts_product_and_global_with_extra():
+    artifacts = SizeChartArtifacts()
+    artifacts.register_product("unique.png")
+    artifacts.register_global("general.png")
+    artifacts.register_extra("grid", "grid.png")
+
+    assert artifacts.product_table == "unique.png"
+    assert artifacts.global_table == "general.png"
+    assert artifacts.ordered_paths() == ["unique.png", "general.png", "grid.png"]
+
+
+def test_artifacts_empty_behaviour():
+    artifacts = SizeChartArtifacts()
+
+    assert artifacts.ordered_paths() == []
+    assert artifacts.as_dict() == {"product": [], "global": []}