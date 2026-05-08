const modifiedFiles = danger.git.modified_files || [];
const createdFiles = danger.git.created_files || [];
const deletedFiles = danger.git.deleted_files || [];
const changedFiles = [...modifiedFiles, ...createdFiles, ...deletedFiles];
const pr = danger.github && danger.github.pr ? danger.github.pr : {};
const prBody = pr.body || "";

const additions = Number(pr.additions || 0);
const deletions = Number(pr.deletions || 0);
const totalDiffLines = additions + deletions;

const normalizePath = (file) => file.replace(/\\/g, "/");
const files = changedFiles.map(normalizePath);
const bodyHas = (pattern) => pattern.test(prBody);
const anyFile = (pattern) => files.some((file) => pattern.test(file));

const highRiskFiles = [
  "agents/knowledge_base.py",
  "agents/director_graph_package/shot_director_impl.py",
  "agents/director_graph_package/prompt_compiler_impl.py",
  "agents/director_graph_package/helpers.py",
  "mcp_director_enhanced.py",
];

const touchedHighRiskFiles = highRiskFiles.filter((file) => files.includes(file));
const touchedKnowledgeRules = files.filter((file) =>
  /^knowledge\/(?:rules|cases)\//.test(file)
);
const touchedWorkflowOrScripts = files.filter((file) =>
  /^\.github\/workflows\//.test(file) ||
  /^scripts\//.test(file) ||
  /^tools\/.*\.(?:sh|bash|ps1|bat|cmd|py|js|ts)$/.test(file) ||
  /\.(?:sh|bash|ps1|bat|cmd)$/.test(file)
);
const rootTemporaryScripts = createdFiles
  .map(normalizePath)
  .filter((file) => /^(?:fix_|scratch_|_tmp_|tmp_).+\.py$/.test(file));

const touchedAgents = anyFile(/^agents\//);
const touchedTests = files.some((file) =>
  /^tests\//.test(file) ||
  /(^|\/)__tests__\//.test(file) ||
  /(^|\/)test_[^/]+\.py$/.test(file) ||
  /(^|\/)[^/]+_test\.py$/.test(file) ||
  /(^|\/)[^/]+\.(?:test|spec)\.(?:js|jsx|ts|tsx)$/.test(file)
);

if (totalDiffLines > 1200) {
  warn(
    `这个 PR 改了 ${totalDiffLines} 行，已经很难一次审完。请让 AI 补一句：` +
      `"把这个 PR 按功能拆成 2-4 个更小 PR，并说明每个 PR 的目标、文件和测试。"`
  );
} else if (totalDiffLines > 500) {
  warn(
    `这个 PR 改了 ${totalDiffLines} 行，建议拆小一点。请让 AI 补一句：` +
      `"列出本 PR 能否拆分，如果能，请给出拆分顺序和每一步测试。"`
  );
}

if (touchedHighRiskFiles.length > 0) {
  warn(
    [
      "这个 PR 改到了高风险文件，需要把测试说清楚：",
      ...touchedHighRiskFiles.map((file) => `- \`${file}\``),
      "",
      "请让 AI 补：`说明这些文件为什么要改、影响哪些流程、已经跑了哪些测试、还有哪些没测。`",
    ].join("\n")
  );

  if (!bodyHas(/测试|test|pytest|验证|未测试/i)) {
    warn(
      "PR 描述里还没有清楚写测试。请让 AI 补：`为高风险文件补上测试结果和未测试风险，不能只写未测试。`"
    );
  }
}

if (touchedKnowledgeRules.length > 0) {
  warn(
    [
      "这个 PR 改到了 `knowledge/rules/**` 或 `knowledge/cases/**`。",
      "这些知识文件需要 frontmatter、`runtime_retrieval`、标签和检索测试。",
      "",
      "请让 AI 补：`检查本次知识文件是否都有 frontmatter、runtime_retrieval、tags，并补充或说明检索测试结果。`",
    ].join("\n")
  );
}

if (touchedWorkflowOrScripts.length > 0) {
  warn(
    [
      "这个 PR 改到了 GitHub workflow 或脚本，请重点检查权限和危险命令。",
      "请让 AI 补：`说明 workflow/script 是否新增权限、密钥读取、网络下载、删除命令、执行外部代码，并列出安全检查结果。`",
    ].join("\n")
  );
}

if (rootTemporaryScripts.length > 0) {
  warn(
    [
      "新增了根目录临时修复脚本，后续很容易忘记清理：",
      ...rootTemporaryScripts.map((file) => `- \`${file}\``),
      "",
      "请让 AI 补：`这些脚本是否必须保留？如果必须，移入 tools/ 并写清用途；如果不是，请删除。`",
    ].join("\n")
  );
}

if (touchedAgents && !touchedTests) {
  warn(
    "这个 PR 改了 `agents/**`，但没有看到测试文件变化。请让 AI 补：`为本次 agents 改动补测试，或说明为什么不能补，并写出手动验证步骤。`"
  );
}
