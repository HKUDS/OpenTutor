// Settings page types

export interface ConfigItem {
  id: string;
  name: string;
  provider: string;
  base_url?: string;
  api_key?: string;
  model?: string;
  dimensions?: number;
  voice?: string;
  api_version?: string;
  is_default?: boolean;
  is_active?: boolean;
}

export interface ConfigStatus {
  configured: boolean;
  active_config_id: string;
  active_config_name: string;
  model: string | null;
  provider: string | null;
  env_configured: Record<string, boolean>;
  total_configs: number;
}

export interface FullStatus {
  llm: ConfigStatus;
  embedding: ConfigStatus;
  tts: ConfigStatus;
  search: ConfigStatus;
}

export interface PortsInfo {
  backend_port: number;
  frontend_port: number;
}

export type ConfigType = "llm" | "embedding" | "tts" | "search";
export type TabType = "overview" | ConfigType;
