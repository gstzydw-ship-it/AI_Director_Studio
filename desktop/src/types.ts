export type AssetType = "character" | "scene" | "prop" | "frame" | "upload";

export interface AssetItem {
  id: string;
  name: string;
  type: AssetType;
  filename: string;
  url: string;
  thumbnail: string;
  tags: string[];
  description: string;
  purpose: string;
  timecode?: string;
  timestamp_seconds?: number;
}

export interface AssetLibrary {
  assets: AssetItem[];
  groups: Record<string, AssetItem[]>;
}

export interface ModelProfile {
  id: string;
  name: string;
  base_url: string;
  api_key?: string;
  api_key_set?: boolean;
  default_model: string;
  agent_models: Record<string, string | { model?: string; fallback_models?: string[] }>;
  fallback_models: string[];
  vectordb_base_url: string;
  embedding_model: string;
  max_retries?: number;
  timeout_seconds?: number | string;
  base_url_host?: string;
}

export interface DirectorEdit {
  subject: string;
  scene: string;
  shotSize: string;
  camera: string;
  movement: string;
  transition: string;
  actionFocus: string;
  performanceBeat: string;
  cutPoint: string;
  continuity: string;
}

export interface TaskState {
  status?: string;
  step?: string;
  message?: string;
  error?: string;
  result?: string;
  project_name?: string;
  archived?: boolean;
  current_segment_index?: number;
  active_segment_index?: number;
  total_segments?: number;
  segment_names?: string[];
  agent_outputs?: Record<string, string>;
  model_profile_snapshot?: Partial<ModelProfile> & { base_url_host?: string };
  director_review_required?: boolean;
  director_edits_by_segment?: Record<string, { edited_yaml: string; edit_payload?: Record<string, unknown> }>;
  shot_director_original_by_segment?: Record<string, string>;
  shot_director_approved_by_segment?: Record<string, string>;
}

export interface ProjectSummary {
  session_id: string;
  name: string;
  status: string;
  current_segment_index: number;
  total_segments: number;
  archived: boolean;
  updated_at?: string;
}
