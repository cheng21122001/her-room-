// 录入工具：把表单内容拼成 seed_data.py 的 CASES 条目代码片段。
// 只在浏览器里生成文本，不向服务器提交任何数据。

(function () {
  var form = document.getElementById("capture-form");
  var section = document.getElementById("snippet-section");
  var output = document.getElementById("snippet-output");

  function py(str) {
    return '"' + String(str).replace(/\\/g, "\\\\").replace(/"/g, '\\"').trim() + '"';
  }

  function field(name) {
    var el = form.elements[name];
    return el ? el.value.trim() : "";
  }

  document.getElementById("generate-btn").addEventListener("click", function () {
    if (!field("name")) {
      alert("请至少填写姓名。");
      return;
    }

    var timelineLines = field("timeline")
      .split("\n")
      .map(function (line) { return line.trim(); })
      .filter(Boolean)
      .map(function (line) {
        var parts = line.split("|");
        var date = (parts[0] || "").trim();
        var event = parts.slice(1).join("|").trim();
        return "            (" + py(date) + ", " + py(event) + "),";
      });

    var terms = Array.prototype.slice
      .call(form.querySelectorAll('input[name="terms"]:checked'))
      .map(function (el) { return py(el.value); });

    var lines = [
      "    {",
      "        \"archive_no\": " + py(field("archive_no")) + ",",
      "        \"name\": " + py(field("name")) + ",",
      "        \"aliases\": " + py(field("aliases")) + ",",
      "        \"period\": " + py(field("period")) + ",",
      "        \"era\": " + py(field("era")) + ",",
      "        \"region\": " + py(field("region")) + ",",
      "        \"year_start\": " + (parseInt(field("year_start"), 10) || 0) + ",",
      "        \"location\": " + py(field("location")) + ",",
      "        \"case_type\": " + py(field("case_type")) + ",",
      "        \"credibility\": " + py(field("credibility")) + ",",
      "        \"symbol\": " + py(field("symbol")) + ",",
      "        \"summary\": " + py(field("summary")) + ",",
      "        \"case_details\": (",
      "            " + py(field("case_details")),
      "        ),",
      "        \"timeline\": [",
    ]
      .concat(timelineLines)
      .concat([
        "        ],",
        "        \"psychological_profile\": (",
        "            " + py(field("psychological_profile")),
        "        ),",
        "        \"terms\": [" + terms.join(", ") + "],",
        "        \"sources\": (",
        "            " + py(field("sources")),
        "        ),",
        "    },",
      ]);

    output.textContent = lines.join("\n");

    // 预填 GitHub issue：访客点开即是带代码的投稿页。
    var githubBtn = document.getElementById("github-btn");
    var title = "案例投稿：" + field("archive_no") + " " + field("name");
    var body =
      "以下案例条目由录入工具生成，请馆主审核后加入 `seed_data.py`：\n\n" +
      "```python\n" + output.textContent + "\n```\n";
    githubBtn.href =
      githubBtn.dataset.repo +
      "/issues/new?title=" + encodeURIComponent(title) +
      "&body=" + encodeURIComponent(body);

    section.hidden = false;
    section.scrollIntoView({ behavior: "smooth" });
  });

  document.getElementById("copy-btn").addEventListener("click", function () {
    navigator.clipboard.writeText(output.textContent).then(function () {
      var btn = document.getElementById("copy-btn");
      btn.textContent = "已复制 ✓";
      setTimeout(function () { btn.textContent = "复制"; }, 2000);
    });
  });
})();
