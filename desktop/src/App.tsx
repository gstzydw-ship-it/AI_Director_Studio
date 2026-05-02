import { ChangeEvent, useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  Box,
  CheckCircle2,
  ClipboardList,
  Clock3,
  Database,
  Eye,
  Film,
  FolderSearch,
  Images,
  KeyRound,
  MapPinned,
  Play,
  Save,
  Scissors,
  Settings,
  SlidersHorizontal,
  Upload,
  UserRound,
  WandSparkles
} from "lucide-react";
import {
  API_BASE,
  archiveProject,
  createProject,
  extractFrames,
  getAssets,
  getModelProfiles,
  getRecentProjects,
  importAsset,
  importAssetBatch,
  getStatus,
  runPipeline,
  saveDirectorEdit,
  saveModelProfile,
  submitDirectorEdit,
  testModelProfile
} from "./api";
import type { AssetItem, AssetLibrary, DirectorEdit, ModelProfile, ProjectSummary, TaskState } from "./types";

const agentLabels: Array<[string, string]> = [
  ["rhythm_rewrite_director", "节奏总控"],
  ["scene_analyst", "场景分析"],
  ["story_planner", "结构规划"],
  ["shot_director", "镜头导演"],
  ["prompt_compiler", "Prompt 编译"],
  ["quality_inspector", "质检导演"]
];

const emptyEdit: DirectorEdit = {
  subject: "",
  scene: "",
  shotSize: "中近景",
  camera: "固定机位",
  movement: "固定",
  transition: "镜头切至",
  actionFocus: "",
  performanceBeat: "",
  cutPoint: "",
  continuity: ""
};

const defaultProfile: ModelProfile = {
  id: "",
  name: "我的 API 方案",
  base_url: "",
  api_key: "",
  default_model: "gpt-5.5",
  agent_models: {
    rhythm_rewrite_director: "gpt-5.5",
    scene_analyst: "gpt-5.5",
    story_planner: "gpt-5.5",
    shot_director: "gpt-5.5",
    prompt_compiler: "seedance-1.0-pro",
    quality_inspector: "gpt-5.5"
  },
  fallback_models: [],
  vectordb_base_url: "https://vector.comfly.ai",
  embedding_model: "text-embedding-3-large",
  max_retries: 2,
  timeout_seconds: 180
};

const modelOf = (profile: ModelProfile, key: string) => {
  const value = profile.agent_models?.[key];
  return typeof value === "string" ? value : value?.model ?? "";
};

const yamlString = (value: string) => JSON.stringify(value || "");

const extractSegmentBlock = (text: string | undefined, index: number) => {
  const id = `F${String(index).padStart(2, "0")}`;
  const match = (text || "").match(
    new RegExp(`(^\\s*-?\\s*fragment_id\\s*:\\s*["']?${id}["']?[\\s\\S]*?)(?=\\n\\s*-?\\s*fragment_id\\s*:\\s*["']?F\\d+|$)`, "m")
  );
  return match?.[1]?.trim() ?? "";
};

const makeApprovedYaml = (original: string, segmentIndex: number, edit: DirectorEdit) => {
  const base = original.trim() || `fragment_id: F${String(segmentIndex).padStart(2, "0")}\nshots: []`;
  return `${base}

director_manual_overrides:
  subject: ${yamlString(edit.subject)}
  scene: ${yamlString(edit.scene)}
  shot_size: ${yamlString(edit.shotSize)}
  camera: ${yamlString(edit.camera)}
  movement: ${yamlString(edit.movement)}
  transition: ${yamlString(edit.transition)}
  action_focus: ${yamlString(edit.actionFocus)}
  performance_beat: ${yamlString(edit.performanceBeat)}
  cut_point: ${yamlString(edit.cutPoint)}
  continuity_note: ${yamlString(edit.continuity)}
`;
};

const assetSrc = (asset: AssetItem) => asset.thumbnail || `${API_BASE}${asset.url}`;

function App() {
  const [activeSessionId, setActiveSessionId] = useState("local");
  const [status, setStatus] = useState<TaskState>({});
  const [assets, setAssets] = useState<AssetLibrary>({ assets: [], groups: {} });
  const [profiles, setProfiles] = useState<ModelProfile[]>([]);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [showProjects, setShowProjects] = useState(false);
  const [profileDraft, setProfileDraft] = useState<ModelProfile>(defaultProfile);
  const [edit, setEdit] = useState<DirectorEdit>(emptyEdit);
  const [activeTab, setActiveTab] = useState<"script" | "director" | "result" | "prompt">("script");
  const [scriptDraft, setScriptDraft] = useState("");
  const [scriptDirty, setScriptDirty] = useState(false);
  const [aspectRatio, setAspectRatio] = useState("9:16");
  const [stylePreset, setStylePreset] = useState("modern_short_drama");
  const [connected, setConnected] = useState(false);
  const [toast, setToast] = useState("");

  const segmentIndex = status.current_segment_index || 1;
  const originalBlock = useMemo(() => {
    return (
      status.shot_director_original_by_segment?.[String(segmentIndex)] ||
      extractSegmentBlock(status.agent_outputs?.shot_director, segmentIndex)
    );
  }, [segmentIndex, status.agent_outputs, status.shot_director_original_by_segment]);

  const approvedYaml = useMemo(() => makeApprovedYaml(originalBlock, segmentIndex, edit), [edit, originalBlock, segmentIndex]);

  const refresh = async () => {
    try {
      const nextStatus = await getStatus(activeSessionId);
      setStatus(nextStatus);
      setConnected(true);
    } catch {
      setConnected(false);
    }
  };

  const refreshAssets = async () => {
    const library = await getAssets();
    setAssets({ assets: library.assets, groups: library.groups });
  };

  const refreshProfiles = async () => {
    const data = await getModelProfiles();
    setProfiles(data.profiles);
    if (data.profiles[0] && !profileDraft.id) {
      setProfileDraft({ ...defaultProfile, ...data.profiles[0], api_key: "" });
    }
  };

  useEffect(() => {
    refresh();
    refreshAssets().catch(() => undefined);
    refreshProfiles().catch(() => undefined);
    const timer = window.setInterval(refresh, 2000);
    return () => window.clearInterval(timer);
  }, [activeSessionId]);

  useEffect(() => {
    setEdit((current) => ({
      ...emptyEdit,
      subject: current.subject,
      scene: current.scene,
      continuity: current.continuity
    }));
  }, [segmentIndex]);

  useEffect(() => {
    if (!scriptDirty) {
      setScriptDraft(status.input_script || "");
      setAspectRatio(status.input_aspect_ratio || "9:16");
      setStylePreset(status.style_preset || "modern_short_drama");
    }
  }, [scriptDirty, status.input_aspect_ratio, status.input_script, status.style_preset]);

  const startPipeline = async () => {
    const script = scriptDraft.trim();
    if (!script) {
      setToast("请先输入剧本");
      return;
    }
    await runPipeline({
      sessionId: activeSessionId,
      script,
      aspectRatio,
      modelProfileId: profileDraft.id,
      stylePreset
    });
    setScriptDirty(false);
    setToast("已开始拆片和镜头导演");
    await refresh();
  };

  const saveEdit = async () => {
    const state = await saveDirectorEdit({
      session_id: activeSessionId,
      segment_index: segmentIndex,
      edited_yaml: approvedYaml,
      edit_payload: edit
    });
    setStatus(state.state);
    setToast("导演修改已保存");
  };

  const submitEdit = async () => {
    await submitDirectorEdit({
      session_id: activeSessionId,
      segment_index: segmentIndex,
      edited_yaml: approvedYaml,
      edit_payload: edit
    });
    setToast("已提交 Prompt 编译");
    await refresh();
  };

  const onFrameUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    await extractFrames(file);
    setToast("抽帧完成");
    await refreshAssets();
    event.target.value = "";
  };

  const onAssetUpload = async (assetType: "character" | "scene" | "prop", event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    if (!files.length) return;
    if (files.length === 1) {
      await importAsset(files[0], assetType);
      setToast("资源已导入");
    } else {
      const result = await importAssetBatch(files, assetType);
      setToast(`已导入 ${result.count}/${files.length} 个资源`);
    }
    await refreshAssets();
    event.target.value = "";
  };

  const openRecentProjects = async () => {
    const data = await getRecentProjects();
    setProjects(data.projects);
    setShowProjects((visible) => !visible);
  };

  const newProject = async () => {
    const name = window.prompt("项目名称", `新项目 ${new Date().toLocaleTimeString("zh-CN", { hour12: false })}`) || "";
    if (!name.trim()) return;
    const result = await createProject(name.trim());
    setActiveSessionId(result.project.session_id);
    setShowProjects(false);
    setStatus({});
    setScriptDraft("");
    setScriptDirty(false);
    setActiveTab("script");
    setToast("新项目已创建");
  };

  const archiveCurrentProject = async () => {
    await archiveProject(activeSessionId);
    setToast("项目已归档");
    const data = await getRecentProjects();
    setProjects(data.projects);
    setShowProjects(true);
    await refresh();
  };

  const saveProfile = async () => {
    const payload: Partial<ModelProfile> & { api_key?: string } = { ...profileDraft };
    if (!payload.api_key) delete payload.api_key;
    const result = await saveModelProfile(payload);
    setProfileDraft({ ...defaultProfile, ...result.profile, api_key: "" });
    await refreshProfiles();
    setToast("模型方案已保存");
  };

  const testProfile = async () => {
    const result = await testModelProfile(profileDraft);
    setToast(result.success ? `连接成功：${result.base_url_host}` : `连接失败：${result.error}`);
  };

  const updateAgentModel = (key: string, value: string) => {
    setProfileDraft((profile) => ({
      ...profile,
      agent_models: { ...profile.agent_models, [key]: value }
    }));
  };

  const segmentNames = status.segment_names?.length
    ? status.segment_names
    : Array.from({ length: Math.max(status.total_segments || 4, 4) }, (_, index) => `F${String(index + 1).padStart(2, "0")} 剧本片段`);

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand"><Film size={19} />AI Director Studio</div>
        <div className="project-title">{status.project_name || "AI Director Studio"}</div>
        <div className="top-actions">
          <select
            value={profileDraft.id}
            onChange={(event) => {
              const profile = profiles.find((item) => item.id === event.target.value);
              setProfileDraft(profile ? { ...defaultProfile, ...profile, api_key: "" } : defaultProfile);
            }}
          >
            <option value="">我的 API 方案</option>
            {profiles.map((profile) => <option key={profile.id} value={profile.id}>{profile.name}</option>)}
          </select>
          <span className={connected ? "status-dot online" : "status-dot"} />
          <span>{connected ? "已连接" : "未连接"}</span>
          <button className="icon-button" title="设置"><Settings size={17} /></button>
        </div>
      </header>

      <main className="main-grid">
        <aside className="sidebar panel">
          <SectionTitle icon={<ClipboardList size={15} />} label="项目管理" />
          <button className={showProjects ? "nav-row active" : "nav-row"} onClick={openRecentProjects}>最近项目</button>
          <button className="nav-row" onClick={newProject}>新建项目</button>
          <button className="nav-row" onClick={archiveCurrentProject}>归档项目</button>
          {showProjects && (
            <div className="project-list">
              {projects.map((project) => (
                <button
                  key={project.session_id}
                  className={project.session_id === activeSessionId ? "project-item active" : "project-item"}
                  onClick={() => {
                    setActiveSessionId(project.session_id);
                    setShowProjects(false);
                    setScriptDirty(false);
                    setActiveTab(project.total_segments ? "director" : "script");
                  }}
                >
                  <strong>{project.name}</strong>
                  <span>{project.status} · {project.total_segments || 0} 段</span>
                </button>
              ))}
            </div>
          )}

          <SectionTitle icon={<Scissors size={15} />} label="剧本片段" action="+" />
          <div className="segment-list">
            {segmentNames.map((name, index) => (
              <button
                key={name}
                className={index + 1 === segmentIndex ? "segment active" : "segment"}
                onClick={() => setStatus((current) => ({ ...current, current_segment_index: index + 1 }))}
              >
                <span>F{String(index + 1).padStart(2, "0")}</span>
                <strong>{name.replace(/^F\d+\s*/, "")}</strong>
              </button>
            ))}
          </div>

          <AssetShelf title="角色库" icon={<UserRound size={15} />} assets={assets.groups.character || []} onImport={(event) => onAssetUpload("character", event)} />
          <AssetShelf title="场景库" icon={<MapPinned size={15} />} assets={assets.groups.scene || []} onImport={(event) => onAssetUpload("scene", event)} />
          <AssetShelf title="道具库" icon={<Box size={15} />} assets={assets.groups.prop || []} onImport={(event) => onAssetUpload("prop", event)} />

          <SectionTitle icon={<Images size={15} />} label="抽帧库" action={<label className="mini-upload"><Upload size={13} /><input type="file" accept="video/*" onChange={onFrameUpload} /></label>} />
          <div className="thumb-strip">
            {(assets.groups.frame || []).slice(0, 8).map((asset) => (
              <div className="frame-thumb" key={asset.id}>
                {asset.thumbnail && <img src={assetSrc(asset)} alt={asset.name} />}
                <span>{asset.timecode || asset.name}</span>
              </div>
            ))}
          </div>
        </aside>

        <section className="workspace panel">
          <div className="tabs">
            <button className={activeTab === "script" ? "tab active" : "tab"} onClick={() => setActiveTab("script")}>剧本输入</button>
            <button className={activeTab === "result" ? "tab active" : "tab"} onClick={() => setActiveTab("result")}>镜头导演结果</button>
            <button className={activeTab === "director" ? "tab active" : "tab"} onClick={() => setActiveTab("director")}>导演修改台</button>
            <button className={activeTab === "prompt" ? "tab active" : "tab"} onClick={() => setActiveTab("prompt")}>Seedance Prompt</button>
          </div>

          {activeTab === "script" && (
            <div className="script-board">
              <div className="board-header">
                <div>
                  <p className="eyebrow">剧本输入</p>
                  <h1>{status.project_name || "新项目"}</h1>
                </div>
                <div className="script-controls">
                  <label>
                    <span>画幅</span>
                    <select value={aspectRatio} onChange={(event) => setAspectRatio(event.target.value)}>
                      <option value="9:16">9:16 竖屏</option>
                      <option value="16:9">16:9 横屏</option>
                      <option value="1:1">1:1 方屏</option>
                    </select>
                  </label>
                  <label>
                    <span>风格</span>
                    <select value={stylePreset} onChange={(event) => setStylePreset(event.target.value)}>
                      <option value="modern_short_drama">现代短剧</option>
                      <option value="ceo_short_drama">霸总短剧</option>
                      <option value="urban_emotion">都市情感</option>
                      <option value="suspense_thriller">悬疑惊悚</option>
                      <option value="crime_realism">犯罪写实</option>
                      <option value="cyberpunk">赛博朋克</option>
                      <option value="new_chinese">新中式</option>
                      <option value="ancient_politics">古装权谋</option>
                      <option value="martial_hero">武侠江湖</option>
                      <option value="xianxia_fantasy">仙侠玄幻</option>
                      <option value="korean_drama">韩剧质感</option>
                      <option value="japanese_mood">日系清冷</option>
                      <option value="hongkong_cinema">港风电影</option>
                      <option value="wong_kar_wai">王家卫式</option>
                      <option value="film_noir">黑色电影</option>
                      <option value="documentary">纪录片写实</option>
                      <option value="commercial">广告大片</option>
                      <option value="music_mv">音乐 MV</option>
                      <option value="anime_storyboard">动漫分镜</option>
                      <option value="vertical_drama">竖屏爽剧</option>
                    </select>
                  </label>
                  <button className="primary" onClick={startPipeline} disabled={status.status?.startsWith("running")}>
                    <Play size={16} />开始拆片
                  </button>
                </div>
              </div>
              <textarea
                className="script-input"
                value={scriptDraft}
                onChange={(event) => {
                  setScriptDraft(event.target.value);
                  setScriptDirty(true);
                }}
                placeholder="在这里输入完整剧本。点击“开始拆片”后，后端会执行：剧本输入 → 拆片 → 镜头导演 → 导演修改确认。"
              />
              <div className="script-meta">
                <span>{scriptDraft.trim().length} 字</span>
                <span>{status.message || "等待输入剧本"}</span>
              </div>
            </div>
          )}

          {activeTab === "director" && (
            <div className="director-board">
              <div className="board-header">
                <div>
                  <p className="eyebrow">F{String(segmentIndex).padStart(2, "0")} 镜头确认</p>
                  <h1>{segmentNames[segmentIndex - 1] || "当前片段"}</h1>
                </div>
                <div className="duration-lock">时长锁定：{segmentIndex === 1 ? "0-3s" : "由节奏控制"}</div>
              </div>

              <div className="edit-grid">
                <Field label="主体" value={edit.subject} onChange={(value) => setEdit({ ...edit, subject: value })} options={(assets.groups.character || []).map((item) => item.name)} />
                <Field label="场景" value={edit.scene} onChange={(value) => setEdit({ ...edit, scene: value })} options={(assets.groups.scene || []).map((item) => item.name)} />
                <Field label="景别" value={edit.shotSize} onChange={(value) => setEdit({ ...edit, shotSize: value })} options={["远景", "全景", "中景", "中近景", "近景", "特写"]} />
                <Field label="机位" value={edit.camera} onChange={(value) => setEdit({ ...edit, camera: value })} options={["固定机位", "正面机位", "侧前方机位", "过肩机位", "低角度", "高角度"]} />
                <Field label="运镜" value={edit.movement} onChange={(value) => setEdit({ ...edit, movement: value })} options={["固定", "缓慢推进", "跟拍", "横移", "轻微手持", "拉远"]} />
                <Field label="衔接方式" value={edit.transition} onChange={(value) => setEdit({ ...edit, transition: value })} options={["镜头切至", "反应切", "动作切", "视线切", "插入切", "当前人物其他景别"]} />
                <Field label="动作焦点" value={edit.actionFocus} onChange={(value) => setEdit({ ...edit, actionFocus: value })} options={["冲进电梯", "抬眼确认", "伸手阻止", "撞上瞬间", "转身离开"]} />
                <Field label="表演落点" value={edit.performanceBeat} onChange={(value) => setEdit({ ...edit, performanceBeat: value })} options={["错愕", "压住怒气", "短暂停顿", "眼神回避", "强装镇定"]} />
                <Field label="切点" value={edit.cutPoint} onChange={(value) => setEdit({ ...edit, cutPoint: value })} options={["撞上瞬间", "抬眼瞬间", "台词断点", "情绪落点", "尾帧可承接"]} />
              </div>

              <label className="textarea-label">连续性说明</label>
              <textarea
                value={edit.continuity}
                onChange={(event) => setEdit({ ...edit, continuity: event.target.value })}
                placeholder="保持上一镜头已建立的人物位置、服装、空间方向与动作结果。"
              />

              <div className="reference-row">
                {["character", "scene", "frame"].flatMap((type) => (assets.groups[type] || []).slice(0, 3)).map((asset) => (
                  <div className="reference-item" key={asset.id}>
                    {asset.thumbnail && <img src={assetSrc(asset)} alt={asset.name} />}
                    <span>{asset.name}</span>
                  </div>
                ))}
              </div>

              <div className="action-row">
                <button onClick={saveEdit}><Save size={16} />保存导演修改</button>
                <button className="secondary" onClick={() => setEdit(emptyEdit)}>恢复 AI 原始版</button>
                <button className="primary" onClick={submitEdit}><WandSparkles size={16} />提交 Prompt 编译</button>
              </div>
            </div>
          )}

          {activeTab === "result" && <pre className="code-pane">{originalBlock || status.agent_outputs?.shot_director || "暂无镜头导演结果"}</pre>}
          {activeTab === "prompt" && <pre className="code-pane">{status.agent_outputs?.[`compiled_segment_${segmentIndex}`] || status.result || "暂无 Seedance Prompt"}</pre>}
        </section>

        <aside className="inspector panel">
          <SectionTitle icon={<Eye size={15} />} label="诊断面板" />
          <div className="diagnostic">
            <Row label="当前 Agent" value={status.step || "等待任务"} />
            <Row label="模型" value={status.model_profile_snapshot?.default_model || profileDraft.default_model} />
            <Row label="BaseURL" value={status.model_profile_snapshot?.base_url_host || profileDraft.base_url_host || "local"} />
            <Row label="状态" value={status.director_review_required ? "等待导演确认" : status.status || "idle"} strong />
          </div>
          <div className="rule-list">
            <CheckCircle2 size={16} /> 时间段来自节奏控制
            <CheckCircle2 size={16} /> 禁止同一机位滥用
            <CheckCircle2 size={16} /> 动作连续性
          </div>
          {status.error && <div className="error-box"><AlertCircle size={16} />{status.error}</div>}

          <SectionTitle icon={<SlidersHorizontal size={15} />} label="模型配置中心" />
          <div className="profile-form">
            <input value={profileDraft.name} onChange={(event) => setProfileDraft({ ...profileDraft, name: event.target.value })} placeholder="方案名称" />
            <input value={profileDraft.base_url} onChange={(event) => setProfileDraft({ ...profileDraft, base_url: event.target.value })} placeholder="BaseURL" />
            <div className="key-field">
              <KeyRound size={15} />
              <input type="password" value={profileDraft.api_key || ""} onChange={(event) => setProfileDraft({ ...profileDraft, api_key: event.target.value })} placeholder={profileDraft.api_key_set ? "已保存，留空不变" : "API Key"} />
            </div>
            <button onClick={testProfile}>测试连接</button>
            {agentLabels.map(([key, label]) => (
              <label className="agent-row" key={key}>
                <span>{label}</span>
                <input value={modelOf(profileDraft, key)} onChange={(event) => updateAgentModel(key, event.target.value)} />
              </label>
            ))}
            <input value={profileDraft.vectordb_base_url} onChange={(event) => setProfileDraft({ ...profileDraft, vectordb_base_url: event.target.value })} placeholder="向量库 BaseURL" />
            <input value={profileDraft.embedding_model} onChange={(event) => setProfileDraft({ ...profileDraft, embedding_model: event.target.value })} placeholder="Embedding Model" />
            <button className="primary" onClick={saveProfile}>保存方案</button>
          </div>
        </aside>
      </main>

      <footer className="pipeline">
        {[
          ["节奏总控", "step_0_rhythm"],
          ["场景分析", "step_1_analyze"],
          ["结构规划", "step_2_plan"],
          ["镜头导演", "step_3_direct"],
          ["导演修改", "review"],
          ["Prompt 编译", "step_4_compile"],
          ["质检", "step_5_inspect"]
        ].map(([label, step]) => (
          <div className={status.step === step || (step === "review" && status.director_review_required) ? "pipe active" : "pipe"} key={step}>
            {status.step === step || (step === "review" && status.director_review_required) ? <Clock3 size={18} /> : <CheckCircle2 size={18} />}
            <span>{label}</span>
          </div>
        ))}
      </footer>
      {toast && <button className="toast" onClick={() => setToast("")}>{toast}</button>}
    </div>
  );
}

function SectionTitle({ icon, label, action }: { icon: JSX.Element; label: string; action?: JSX.Element | string }) {
  return <div className="section-title">{icon}<span>{label}</span>{action && <span className="section-action">{action}</span>}</div>;
}

function AssetShelf({ title, icon, assets, onImport }: { title: string; icon: JSX.Element; assets: AssetItem[]; onImport: (event: ChangeEvent<HTMLInputElement>) => void }) {
  return (
    <>
      <SectionTitle icon={icon} label={title} action={<span className="asset-upload-row"><label className="mini-upload" title="单图导入"><Upload size={13} /><input type="file" accept="image/*" onChange={onImport} /></label><label className="mini-upload" title="文件夹导入"><FolderSearch size={13} /><input type="file" accept="image/*" {...{ webkitdirectory: "" }} onChange={onImport} /></label></span>} />
      <div className="asset-grid">
        {assets.slice(0, 6).map((asset) => (
          <div className="asset-card" key={asset.id}>
            {asset.thumbnail && <img src={assetSrc(asset)} alt={asset.name} />}
            <span>{asset.name}</span>
          </div>
        ))}
      </div>
    </>
  );
}

function Field({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (value: string) => void }) {
  const values = value && !options.includes(value) ? [value, ...options] : options;
  return (
    <label className="field">
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">未选择</option>
        {values.map((option) => <option key={option} value={option}>{option}</option>)}
      </select>
    </label>
  );
}

function Row({ label, value, strong }: { label: string; value?: string; strong?: boolean }) {
  return <div className="row"><span>{label}</span><b className={strong ? "warn" : ""}>{value || "-"}</b></div>;
}

export default App;
