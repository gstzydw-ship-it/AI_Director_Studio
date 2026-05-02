import type { AssetLibrary, ModelProfile, ProjectSummary, TaskState } from "./types";

export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8686";

const readJson = async <T>(path: string, init?: RequestInit): Promise<T> => {
  const response = await fetch(`${API_BASE}${path}`, init);
  const data = await response.json();
  if (!response.ok || data.success === false) {
    throw new Error(data.error || `HTTP ${response.status}`);
  }
  return data as T;
};

export const getStatus = (sessionId = "local") =>
  readJson<TaskState>(`/api/status?session_id=${encodeURIComponent(sessionId)}`);

export const getAssets = () => readJson<{ success: true } & AssetLibrary>("/api/assets/library");

export const getRecentProjects = () =>
  readJson<{ success: true; projects: ProjectSummary[] }>("/api/projects/recent");

export const createProject = (name: string) =>
  readJson<{ success: true; project: ProjectSummary }>("/api/projects/new", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name })
  });

export const archiveProject = (sessionId: string) =>
  readJson<{ success: true; project: ProjectSummary }>("/api/projects/archive", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId })
  });

export const getModelProfiles = () =>
  readJson<{ success: true; profiles: ModelProfile[] }>("/api/model_profiles");

export const saveModelProfile = (profile: Partial<ModelProfile> & { api_key?: string }) =>
  readJson<{ success: true; profile: ModelProfile }>("/api/model_profiles", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(profile)
  });

export const testModelProfile = (profile: Partial<ModelProfile> & { api_key?: string }) =>
  fetch(`${API_BASE}/api/model_profiles/test`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(profile)
  }).then((response) => response.json() as Promise<{ success: boolean; error?: string; base_url_host?: string }>);

export const saveDirectorEdit = (payload: unknown) =>
  readJson<{ success: true; state: TaskState }>("/api/director_edits/save", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

export const submitDirectorEdit = (payload: unknown) =>
  readJson<{ success: true; message: string }>("/api/director_edits/submit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

export const extractFrames = (file: File, intervalSeconds = 3) => {
  const body = new FormData();
  body.append("video_file", file);
  body.append("interval_seconds", String(intervalSeconds));
  body.append("max_frames", "18");
  body.append("purpose", "action_reference");
  return readJson<{ success: true }>("/api/video/extract_frames", { method: "POST", body });
};

export const importAsset = (file: File, assetType: "character" | "scene" | "prop") => {
  const body = new FormData();
  body.append("file", file);
  body.append("asset_type", assetType);
  body.append("name", file.name.replace(/\.[^.]+$/, ""));
  return readJson<{ success: true }>("/api/assets/import", { method: "POST", body });
};
