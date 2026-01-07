"use client";

import { useState, useEffect, useRef } from "react";
import {
  Settings as SettingsIcon,
  Sun,
  Moon,
  Globe,
  Save,
  RotateCcw,
  Loader2,
  Check,
  Server,
  AlertCircle,
  Database,
  Search,
  MessageSquare,
  Volume2,
  Cpu,
  Key,
  Brain,
  Eye,
  EyeOff,
  RefreshCw,
  CheckCircle,
  XCircle,
  Info,
  Sliders,
} from "lucide-react";
import { apiUrl } from "@/lib/api";
import { getTranslation } from "@/lib/i18n";
import { setTheme } from "@/lib/theme";
import { debounce } from "@/lib/debounce";

import { useGlobal } from "@/context/GlobalContext";

// --- Types matching backend ---

interface UISettings {
  theme: "light" | "dark";
  language: "zh" | "en";
  output_language: "zh" | "en";
}

interface EnvInfo {
  model: string;
  [key: string]: string;
}

// Config is dynamic, but we know some structure
interface ConfigData {
  system?: {
    language?: string;
    [key: string]: any;
  };
  tools?: {
    rag_tool?: {
      kb_base_dir?: string;
      default_kb?: string;
      [key: string]: any;
    };
    run_code?: {
      workspace?: string;
      allowed_roots?: string[];
      language?: string;
      timeout?: number;
      sandbox?: boolean;
      [key: string]: any;
    };
    web_search?: {
      enabled?: boolean;
      max_results?: number;
      [key: string]: any;
    };
    [key: string]: any;
  };
  logging?: {
    level?: string;
    [key: string]: any;
  };
  tts?: {
    default_voice?: string;
    default_language?: string;
    [key: string]: any;
  };
  [key: string]: any;
}

interface FullSettingsResponse {
  ui: UISettings;
  config: ConfigData;
  env: EnvInfo;
}

// Environment variable types
interface EnvVarInfo {
  key: string;
  value: string;
  description: string;
  category: string;
  required: boolean;
  default: string;
  sensitive: boolean;
  is_set: boolean;
}

interface EnvCategoryInfo {
  id: string;
  name: string;
  description: string;
  icon: string;
}

interface EnvConfigResponse {
  variables: EnvVarInfo[];
  categories: EnvCategoryInfo[];
}

interface TestResults {
  llm: { status: string; model: string | null; error: string | null };
  embedding: { status: string; model: string | null; error: string | null };
  tts: { status: string; model: string | null; error: string | null };
}

interface LLMProvider {
  name: string;
  binding: string;
  base_url: string;
  api_key: string;
  model: string;
  is_active: boolean;
}

// Tab types
type SettingsTab = "general" | "environment" | "llm_providers";

export default function SettingsPage() {
  const { uiSettings, refreshSettings } = useGlobal();
  const t = (key: string) => getTranslation(uiSettings.language, key);
  const [activeTab, setActiveTab] = useState<SettingsTab>("general");
  const [data, setData] = useState<FullSettingsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [error, setError] = useState("");

  // Edit states
  const [editedConfig, setEditedConfig] = useState<ConfigData | null>(null);
  const [editedUI, setEditedUI] = useState<UISettings | null>(null);

  // --- Helper Data ---

  interface ProviderPreset {
    id: string;
    name: string;
    binding: "openai" | "azure_openai" | "ollama";
    base_url?: string;
    default_model: string;
    models: string[];
    requires_key: boolean;
    help_text?: string;
  }

  const PROVIDER_PRESETS: ProviderPreset[] = [
    {
      id: "ollama",
      name: "Ollama (Local)",
      binding: "ollama",
      base_url: "http://localhost:11434/v1",
      default_model: "llama3.2",
      models: [
        "llama3.3",
        "llama3.2",
        "qwen2.5",
        "mistral-nemo",
        "deepseek-r1",
      ],
      requires_key: false,
      help_text: "Ensure Ollama is running (`ollama serve`).",
    },
    {
      id: "lmstudio",
      name: "LM Studio (Local)",
      binding: "openai",
      base_url: "http://localhost:1234/v1",
      default_model: "uploaded-model",
      models: [],
      requires_key: false,
      help_text: "Ensure LM Studio is running. Standard port is 1234.",
    },
  ];

  // Environment variables states
  const [envConfig, setEnvConfig] = useState<EnvConfigResponse | null>(null);
  const [editedEnvVars, setEditedEnvVars] = useState<Record<string, string>>(
    {},
  );
  const [showSensitive, setShowSensitive] = useState<Record<string, boolean>>(
    {},
  );
  const [envSaving, setEnvSaving] = useState(false);
  const [envSaveSuccess, setEnvSaveSuccess] = useState(false);
  const [envError, setEnvError] = useState("");
  const [testResults, setTestResults] = useState<TestResults | null>(null);
  const [testing, setTesting] = useState(false);

  // LLM Providers state
  const [providers, setProviders] = useState<LLMProvider[]>([]);
  const [loadingProviders, setLoadingProviders] = useState(false);
  const [editingProvider, setEditingProvider] = useState<LLMProvider | null>(
    null,
  ); // null means adding new
  const [selectedPresetId, setSelectedPresetId] = useState<string>("ollama");
  const [customModelInput, setCustomModelInput] = useState(true);
  const [showProviderForm, setShowProviderForm] = useState(false);
  const [testProviderResult, setTestProviderResult] = useState<{
    success: boolean;
    message: string;
  } | null>(null);
  const [testingProvider, setTestingProvider] = useState(false);
  const [fetchedModels, setFetchedModels] = useState<string[]>([]);
  const [fetchingModels, setFetchingModels] = useState(false);
  const [savingProvider, setSavingProvider] = useState(false);
  const [providerError, setProviderError] = useState<string | null>(null);
  const [originalProviderName, setOriginalProviderName] = useState<
    string | null
  >(null);

  // Create debounced theme save function
  const debouncedSaveTheme = useRef(
    debounce(async (themeValue: "light" | "dark", uiSettings: UISettings) => {
      try {
        await fetch(apiUrl("/api/v1/settings/ui"), {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ...uiSettings, theme: themeValue }),
        });
      } catch (err) {
        // Silently fail - theme is still saved to localStorage
      }
    }, 500),
  ).current;

  useEffect(() => {
    fetchSettings();
    fetchEnvConfig();
    if (activeTab === "llm_providers") {
      fetchProviders();
    }
  }, [uiSettings, activeTab]);

  const fetchProviders = async () => {
    setLoadingProviders(true);
    try {
      const res = await fetch(apiUrl("/api/v1/config/llm"));
      if (res.ok) {
        const data = await res.json();
        setProviders(data);
      }
    } catch (err) {
      console.error("Failed to fetch providers:", err);
    } finally {
      setLoadingProviders(false);
    }
  };

  const fetchModels = async () => {
    if (!editingProvider || !editingProvider.base_url) return;
    setFetchingModels(true);
    setFetchedModels([]);

    // Determine endpoints to try based on provider/URL
    // We try multiple strategies if one fails
    let errorMsg = "";

    try {
      let models: string[] = [];
      let success = false;

      const headers = editingProvider.api_key
        ? {
            Authorization: `Bearer ${editingProvider.api_key}`,
          }
        : undefined;

      // Strategy 1: Ollama /api/tags
      if (
        !success &&
        (editingProvider.base_url.includes("11434") ||
          selectedPresetId === "ollama")
      ) {
        try {
          // Remove /v1 if present for the tags endpoint
          const baseUrl = editingProvider.base_url.replace(/\/v1\/?$/, "");
          const res = await fetch(`${baseUrl}/api/tags`, { headers });
          if (res.ok) {
            const data = await res.json();
            if (Array.isArray(data.models)) {
              models = data.models.map((m: any) => m.name);
              success = true;
            }
          }
        } catch (e) {
          console.warn("Ollama fetch failed", e);
        }
      }

      // Strategy 2: LM Studio /api/v0/models (user requested specific format)
      if (
        !success &&
        (editingProvider.base_url.includes("1234") ||
          selectedPresetId === "lmstudio")
      ) {
        try {
          const baseUrl = editingProvider.base_url.replace(/\/v1\/?$/, "");
          const res = await fetch(`${baseUrl}/api/v0/models`, { headers });
          if (res.ok) {
            const data = await res.json();
            if (Array.isArray(data.data)) {
              models = data.data.map((m: any) => m.id);
              success = true;
            }
          }
        } catch (e) {
          console.warn("LM Studio v0 fetch failed", e);
        }
      }

      // Strategy 3: Standard OpenAI /models
      if (!success) {
        try {
          let url = editingProvider.base_url;
          if (url.endsWith("/")) url = url.slice(0, -1);
          // Don't append /models if it's already there (rare but possible)
          if (!url.endsWith("/models")) url = `${url}/models`;

          const res = await fetch(url, { headers });
          if (res.ok) {
            const data = await res.json();
            if (Array.isArray(data.data)) {
              models = data.data.map((m: any) => m.id || m.model || m.name);
              success = true;
            } else if (Array.isArray(data.models)) {
              models = data.models.map((m: any) => m.id || m.model || m.name);
              success = true;
            }
          } else {
            errorMsg = `HTTP ${res.status}`;
          }
        } catch (e) {
          errorMsg = (e as any).message;
        }
      }

      if (success && models.length > 0) {
        setFetchedModels(models);
        setCustomModelInput(false);
      } else {
        // Fallback to preset models if available
        const preset = PROVIDER_PRESETS.find((p) => p.id === selectedPresetId);
        if (preset && preset.models.length > 0) {
          setFetchedModels(preset.models);
          alert(
            `Could not fetch models from API (${errorMsg}), used preset defaults.`,
          );
        } else {
          alert(`No models found. Error: ${errorMsg || "Unknown"}`);
        }
      }
    } catch (err) {
      console.error(err);
      alert("Failed to fetch models: " + (err as any).message);
    } finally {
      setFetchingModels(false);
    }
  };

  const handleProviderSave = async (provider: LLMProvider) => {
    setSavingProvider(true);
    setProviderError(null);
    try {
      const isUpdate = originalProviderName !== null;
      const method = isUpdate ? "PUT" : "POST";
      const url = isUpdate
        ? apiUrl(`/api/v1/config/llm/${originalProviderName}`)
        : apiUrl("/api/v1/config/llm");

      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(provider),
      });

      if (res.ok) {
        fetchProviders();
        setShowProviderForm(false);
        setEditingProvider(null);
      } else {
        const err = await res.json();
        setProviderError(err.detail || "Failed to save provider");
      }
    } catch (err) {
      console.error(err);
      setProviderError("Failed to save provider: " + (err as any).message);
    } finally {
      setSavingProvider(false);
    }
  };

  const handleDeleteProvider = async (name: string) => {
    if (!confirm(`Delete provider ${name}?`)) return;
    try {
      const res = await fetch(apiUrl(`/api/v1/config/llm/${name}`), {
        method: "DELETE",
      });
      if (res.ok) fetchProviders();
    } catch (err) {
      console.error(err);
    }
  };

  const handleActivateProvider = async (name: string) => {
    try {
      const res = await fetch(apiUrl("/api/v1/config/llm/active"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      if (res.ok) fetchProviders();
    } catch (err) {
      console.error(err);
    }
  };

  const handleTestProvider = async (provider: LLMProvider) => {
    setTestingProvider(true);
    setTestProviderResult(null);
    try {
      // Find preset to check if key is required
      const preset = PROVIDER_PRESETS.find((p) => p.id === selectedPresetId);
      const requiresKey = preset ? preset.requires_key : true;

      const res = await fetch(apiUrl("/api/v1/config/llm/test"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...provider, requires_key: requiresKey }),
      });
      const data = await res.json();
      setTestProviderResult(data);
    } catch (err) {
      setTestProviderResult({ success: false, message: "Connection failed" });
    } finally {
      setTestingProvider(false);
    }
  };

  const fetchSettings = async () => {
    try {
      const res = await fetch(apiUrl("/api/v1/settings"));
      if (res.ok) {
        const responseData = await res.json();
        setData(responseData);
        setEditedConfig(JSON.parse(JSON.stringify(responseData.config)));
        if (!editedUI) {
          const uiData = JSON.parse(JSON.stringify(responseData.ui));
          // localStorage takes priority over backend
          const storedTheme = localStorage.getItem("deeptutor-theme");
          if (storedTheme === "light" || storedTheme === "dark") {
            uiData.theme = storedTheme;
          }
          setEditedUI(uiData);
          // Apply theme if present
          if (uiData.theme) {
            applyTheme(uiData.theme);
          }
        }
      } else {
        setError("Failed to load settings");
      }
    } catch (err) {
      setError("Failed to connect to backend");
    } finally {
      setLoading(false);
    }
  };

  const fetchEnvConfig = async () => {
    try {
      const res = await fetch(apiUrl("/api/v1/settings/env"));
      if (res.ok) {
        const responseData: EnvConfigResponse = await res.json();
        setEnvConfig(responseData);
        const initialValues: Record<string, string> = {};
        responseData.variables.forEach((v) => {
          initialValues[v.key] = v.value;
        });
        setEditedEnvVars(initialValues);
        // Auto test on load
        testEnvConfig();
      }
    } catch (err) {
      console.error("Failed to fetch env config:", err);
    }
  };

  const handleEnvVarChange = (key: string, value: string) => {
    setEditedEnvVars((prev) => ({ ...prev, [key]: value }));
  };

  const toggleSensitiveVisibility = (key: string) => {
    setShowSensitive((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleEnvSave = async () => {
    setEnvSaving(true);
    setEnvSaveSuccess(false);
    setEnvError("");

    try {
      const updates = Object.entries(editedEnvVars)
        .filter(([key, value]) => {
          const original = envConfig?.variables.find((v) => v.key === key);
          if (
            original?.sensitive &&
            value.includes("*") &&
            value === original.value
          ) {
            return false;
          }
          return true;
        })
        .map(([key, value]) => ({ key, value }));

      const res = await fetch(apiUrl("/api/v1/settings/env"), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ variables: updates }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(
          errorData.detail?.errors?.join(", ") || "Failed to save",
        );
      }

      setEnvSaveSuccess(true);
      setTimeout(() => setEnvSaveSuccess(false), 2000);

      await fetchEnvConfig();
      await testEnvConfig();
    } catch (err: any) {
      setEnvError(err.message || "Failed to save environment variables");
    } finally {
      setEnvSaving(false);
    }
  };

  const testEnvConfig = async () => {
    setTesting(true);
    try {
      const res = await fetch(apiUrl("/api/v1/settings/env/test"), {
        method: "POST",
      });
      if (res.ok) {
        const results = await res.json();
        setTestResults(results);
      }
    } catch (err) {
      console.error("Failed to test env config:", err);
    } finally {
      setTesting(false);
    }
  };

  const getCategoryIcon = (iconName: string) => {
    switch (iconName) {
      case "brain":
        return <Brain className="w-4 h-4" />;
      case "database":
        return <Database className="w-4 h-4" />;
      case "volume":
        return <Volume2 className="w-4 h-4" />;
      case "search":
        return <Search className="w-4 h-4" />;
      case "settings":
        return <SettingsIcon className="w-4 h-4" />;
      default:
        return <Key className="w-4 h-4" />;
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "configured":
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case "not_configured":
        return <XCircle className="w-4 h-4 text-amber-500" />;
      case "error":
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      default:
        return <Info className="w-4 h-4 text-slate-400" />;
    }
  };

  const applyTheme = (theme: "light" | "dark") => {
    // Persist theme to localStorage and document immediately
    setTheme(theme);
  };

  const handleSave = async () => {
    if (!editedConfig || !editedUI) return;
    setSaving(true);
    setSaveSuccess(false);
    setError("");

    try {
      const configRes = await fetch(apiUrl("/api/v1/settings/config"), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ config: editedConfig }),
      });

      if (!configRes.ok) throw new Error("Failed to save configuration");

      const uiRes = await fetch(apiUrl("/api/v1/settings/ui"), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(editedUI),
      });

      if (!uiRes.ok) throw new Error("Failed to save UI settings");

      const newConfig = await configRes.json();
      const newUI = await uiRes.json();

      setData((prev) =>
        prev ? { ...prev, config: newConfig, ui: newUI } : null,
      );

      // Sync theme immediately when saving
      if (editedUI.theme) {
        setTheme(editedUI.theme);
      }

      await refreshSettings();

      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2000);
    } catch (err: any) {
      setError(err.message || "Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  const handleConfigChange = (
    section: string,
    key: string,
    value: any,
    subSection?: string,
  ) => {
    setEditedConfig((prev) => {
      if (!prev) return null;
      const newConfig = { ...prev };

      if (subSection) {
        if (!newConfig[section]) newConfig[section] = {};
        if (!newConfig[section][subSection])
          newConfig[section][subSection] = {};
        newConfig[section][subSection][key] = value;
      } else {
        if (!newConfig[section]) newConfig[section] = {};
        newConfig[section][key] = value;
      }
      return newConfig;
    });
  };

  const handleUIChange = (key: keyof UISettings, value: any) => {
    setEditedUI((prev) => {
      if (!prev) return null;
      const newUI = { ...prev, [key]: value };
      if (key === "theme") {
        applyTheme(value);
        // Debounced auto-save to backend
        debouncedSaveTheme(value, newUI);
      }
      return newUI;
    });
  };

  if (loading) {
    return (
      <div className="h-[calc(100vh-4rem)] flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600 dark:text-blue-400" />
      </div>
    );
  }

  if (!editedConfig || !editedUI)
    return (
      <div className="p-8 text-red-500 dark:text-red-400">
        Error loading data
      </div>
    );

  return (
    <div className="h-[calc(100vh-4rem)] overflow-y-auto animate-fade-in">
      {/* Sticky Save Button at Top */}
      <div className="sticky top-0 z-50 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-700 shadow-md">
        <div className="max-w-4xl mx-auto p-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
              System Settings
            </h1>
          </div>
          <button
            onClick={handleSave}
            disabled={saving}
            className={`py-2 px-6 rounded-lg font-medium flex items-center gap-2 transition-all ${
              saving
                ? "bg-slate-100 dark:bg-slate-700 text-slate-400 dark:text-slate-500"
                : saveSuccess
                  ? "bg-green-500 text-white"
                  : "bg-blue-600 text-white hover:bg-blue-700"
            }`}
          >
            {saving ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : saveSuccess ? (
              <Check className="w-4 h-4" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            {saving
              ? t("Saving...")
              : saveSuccess
                ? t("Saved")
                : t("Save All Changes")}
          </button>
        </div>
      </div>

      <div className="max-w-4xl mx-auto p-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 flex items-center gap-3">
              <div className="p-2 bg-blue-50 dark:bg-blue-900/30 rounded-xl">
                <SettingsIcon className="w-6 h-6 text-blue-600 dark:text-blue-400" />
              </div>
              {t("System Settings")}
            </h1>
            <p className="text-slate-500 dark:text-slate-400 mt-2 ml-1">
              {t("Manage system configuration and preferences")}
            </p>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center gap-1 p-1 bg-slate-100 dark:bg-slate-800 rounded-xl mb-6">
          <button
            onClick={() => setActiveTab("general")}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === "general"
                ? "bg-white dark:bg-slate-700 text-blue-600 dark:text-blue-400 shadow-sm"
                : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200"
            }`}
          >
            <Sliders className="w-4 h-4" />
            {t("General Settings")}
          </button>
          <button
            onClick={() => setActiveTab("environment")}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === "environment"
                ? "bg-white dark:bg-slate-700 text-blue-600 dark:text-blue-400 shadow-sm"
                : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200"
            }`}
          >
            <Key className="w-4 h-4" />
            {t("Environment Variables")}
            {testResults && (
              <span
                className={`ml-1 w-2 h-2 rounded-full ${
                  Object.values(testResults).every(
                    (r) => r.status === "configured",
                  )
                    ? "bg-green-500"
                    : Object.values(testResults).some(
                          (r) => r.status === "error",
                        )
                      ? "bg-red-500"
                      : "bg-amber-500"
                }`}
              />
            )}
          </button>
          <button
            onClick={() => setActiveTab("llm_providers")}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === "llm_providers"
                ? "bg-white dark:bg-slate-700 text-blue-600 dark:text-blue-400 shadow-sm"
                : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200"
            }`}
          >
            <Brain className="w-4 h-4" />
            LLM Providers
          </button>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl flex items-center gap-3 text-red-700 dark:text-red-400 font-medium">
            <AlertCircle className="w-5 h-5" />
            <span>{error}</span>
          </div>
        )}

        {/* General Settings Tab */}
        {activeTab === "general" && (
          <div className="space-y-6">
            {/* 1. Interface Settings (UI) */}
            <section className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden transition-colors duration-200">
              <div className="p-4 border-b border-slate-100 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50 flex items-center gap-2">
                <Globe className="w-4 h-4 text-slate-500 dark:text-slate-400" />
                <h2 className="font-semibold text-slate-900 dark:text-slate-100">
                  {t("Interface Preferences")}
                </h2>
              </div>
              <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* Theme Mode */}
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-3">
                    {t("Theme")}
                  </label>
                  <div className="flex bg-slate-100 dark:bg-slate-700 p-1 rounded-xl">
                    {["light", "dark"].map((themeOption) => (
                      <button
                        key={themeOption}
                        onClick={() =>
                          handleUIChange("theme", themeOption as any)
                        }
                        className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium flex items-center justify-center gap-2 transition-all ${
                          editedUI.theme === themeOption
                            ? "bg-white dark:bg-slate-600 text-blue-600 dark:text-blue-400 shadow-sm"
                            : "text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200"
                        }`}
                      >
                        {themeOption === "light" ? (
                          <Sun className="w-4 h-4" />
                        ) : (
                          <Moon className="w-4 h-4" />
                        )}
                        <span>
                          {themeOption === "light"
                            ? t("Light Mode")
                            : t("Dark Mode")}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Interface Language */}
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-3">
                    {t("Language")}
                  </label>
                  <select
                    value={editedUI.language}
                    onChange={(e) => handleUIChange("language", e.target.value)}
                    className="w-full p-2.5 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-sm text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none"
                  >
                    <option value="en">{t("English")}</option>
                    <option value="zh">{t("Chinese")}</option>
                  </select>
                </div>
              </div>
            </section>

            {/* 2. System Configuration */}
            <section className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden transition-colors duration-200">
              <div className="p-4 border-b border-slate-100 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50 flex items-center gap-2">
                <Server className="w-4 h-4 text-slate-500 dark:text-slate-400" />
                <h2 className="font-semibold text-slate-900 dark:text-slate-100">
                  {t("System Configuration")}
                </h2>
              </div>
              <div className="p-6 space-y-6">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                    {t("System Language")}
                  </label>
                  <p className="text-xs text-slate-400 dark:text-slate-500 mb-3">
                    {t("Default language for system operations")}
                  </p>
                  <select
                    value={editedConfig.system?.language || "en"}
                    onChange={(e) =>
                      handleConfigChange("system", "language", e.target.value)
                    }
                    className="w-full md:w-1/2 p-2.5 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-sm text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none"
                  >
                    <option value="en">English</option>
                    <option value="zh">Chinese</option>
                  </select>
                </div>
              </div>
            </section>

            {/* 3. Research Tools */}
            <section className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden transition-colors duration-200">
              <div className="p-4 border-b border-slate-100 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50 flex items-center gap-2">
                <Search className="w-4 h-4 text-slate-500 dark:text-slate-400" />
                <h2 className="font-semibold text-slate-900 dark:text-slate-100">
                  {t("Research Tools")}
                </h2>
              </div>
              <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* Web Search */}
                <div className="p-5 bg-slate-50 dark:bg-slate-700/50 rounded-xl border border-slate-100 dark:border-slate-600">
                  <div className="flex items-center justify-between mb-4">
                    <span className="font-medium text-slate-800 dark:text-slate-200 flex items-center gap-2">
                      <Globe className="w-4 h-4 text-blue-500 dark:text-blue-400" />{" "}
                      {t("Web Search")}
                    </span>
                    <div className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={
                          editedConfig.tools?.web_search?.enabled ?? true
                        }
                        onChange={(e) =>
                          handleConfigChange(
                            "tools",
                            "enabled",
                            e.target.checked,
                            "web_search",
                          )
                        }
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-slate-200 dark:bg-slate-600 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-100 dark:peer-focus:ring-blue-900 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 dark:after:border-slate-500 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">
                      {t("Max Results")}
                    </label>
                    <input
                      type="number"
                      min="1"
                      max="20"
                      value={editedConfig.tools?.web_search?.max_results || 5}
                      onChange={(e) =>
                        handleConfigChange(
                          "tools",
                          "max_results",
                          parseInt(e.target.value),
                          "web_search",
                        )
                      }
                      className="w-full p-2 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg text-sm text-slate-900 dark:text-slate-100"
                    />
                  </div>
                </div>

                {/* RAG / Knowledge Base */}
                <div className="p-5 bg-slate-50 dark:bg-slate-700/50 rounded-xl border border-slate-100 dark:border-slate-600">
                  <div className="flex items-center justify-between mb-4">
                    <span className="font-medium text-slate-800 dark:text-slate-200 flex items-center gap-2">
                      <Database className="w-4 h-4 text-purple-500 dark:text-purple-400" />{" "}
                      {t("Knowledge Base")}
                    </span>
                  </div>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">
                        {t("Default KB")}
                      </label>
                      <input
                        type="text"
                        value={editedConfig.tools?.rag_tool?.default_kb || ""}
                        onChange={(e) =>
                          handleConfigChange(
                            "tools",
                            "default_kb",
                            e.target.value,
                            "rag_tool",
                          )
                        }
                        className="w-full p-2 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg text-sm text-slate-900 dark:text-slate-100"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">
                        {t("Base Directory")}
                      </label>
                      <input
                        type="text"
                        value={editedConfig.tools?.rag_tool?.kb_base_dir || ""}
                        onChange={(e) =>
                          handleConfigChange(
                            "tools",
                            "kb_base_dir",
                            e.target.value,
                            "rag_tool",
                          )
                        }
                        className="w-full p-2 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg text-sm font-mono text-slate-600 dark:text-slate-300"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </section>

            {/* 4. TTS Settings */}
            <section className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden transition-colors duration-200">
              <div className="p-4 border-b border-slate-100 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50 flex items-center gap-2">
                <Volume2 className="w-4 h-4 text-slate-500 dark:text-slate-400" />
                <h2 className="font-semibold text-slate-900 dark:text-slate-100">
                  {t("Text-to-Speech")}
                </h2>
              </div>
              <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-8">
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                    {t("Default Voice")}
                  </label>
                  <input
                    type="text"
                    value={editedConfig.tts?.default_voice || "Cherry"}
                    onChange={(e) =>
                      handleConfigChange("tts", "default_voice", e.target.value)
                    }
                    className="w-full p-2.5 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-sm text-slate-900 dark:text-slate-100"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                    {t("Default Language")}
                  </label>
                  <input
                    type="text"
                    value={editedConfig.tts?.default_language || "English"}
                    onChange={(e) =>
                      handleConfigChange(
                        "tts",
                        "default_language",
                        e.target.value,
                      )
                    }
                    className="w-full p-2.5 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-sm text-slate-900 dark:text-slate-100"
                  />
                </div>
              </div>
            </section>

            {/* Active Models Status */}
            {data?.env && (
              <section className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden transition-colors duration-200">
                <div className="p-4 border-b border-slate-100 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Cpu className="w-4 h-4 text-slate-500 dark:text-slate-400" />
                    <h2 className="font-semibold text-slate-900 dark:text-slate-100">
                      {t("Active Models")}
                    </h2>
                  </div>
                  <span className="text-xs bg-slate-200 dark:bg-slate-600 text-slate-600 dark:text-slate-300 px-2 py-1 rounded">
                    {t("Status")}
                  </span>
                </div>
                <div className="p-6">
                  <div className="flex items-center p-4 bg-emerald-50 dark:bg-emerald-900/20 rounded-xl border border-emerald-100 dark:border-emerald-800">
                    <div className="p-3 bg-white dark:bg-slate-700 rounded-full shadow-sm mr-4">
                      <Server className="w-6 h-6 text-emerald-600 dark:text-emerald-400" />
                    </div>
                    <div>
                      <p className="text-sm text-emerald-800 dark:text-emerald-300 font-medium mb-1">
                        {t("Active LLM Model")}
                      </p>
                      <p className="text-lg font-bold text-emerald-900 dark:text-emerald-200 font-mono">
                        {data.env.model || t("Not configured")}
                      </p>
                      <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-1">
                        {t("Configure in Environment Variables tab")}
                      </p>
                    </div>
                  </div>
                </div>
              </section>
            )}
          </div>
        )}

        {/* Environment Variables Tab */}
        {activeTab === "environment" && envConfig && (
          <div className="space-y-6">
            {/* Status Overview */}
            <section className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden transition-colors duration-200">
              <div className="p-4 border-b border-slate-100 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-slate-500 dark:text-slate-400" />
                  <h2 className="font-semibold text-slate-900 dark:text-slate-100">
                    {t("Configuration Status")}
                  </h2>
                </div>
                <button
                  onClick={testEnvConfig}
                  disabled={testing}
                  className="px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 rounded-lg flex items-center gap-1.5 transition-colors"
                >
                  {testing ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <RefreshCw className="w-3.5 h-3.5" />
                  )}
                  {t("Refresh Status")}
                </button>
              </div>

              <div className="p-6">
                {/* Info Banner */}
                <div className="mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-800 rounded-lg text-xs text-blue-700 dark:text-blue-300 flex items-start gap-2">
                  <Info className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="font-medium mb-1">
                      {t("Runtime Configuration")}
                    </p>
                    <p className="text-blue-600 dark:text-blue-400">
                      <code className="bg-blue-100 dark:bg-blue-800 px-1 rounded">
                        .env
                      </code>{" "}
                      {t("file on startup")}.{" "}
                      {t(
                        "Changes made here take effect immediately but are not saved to file",
                      )}
                      . {t("On restart, values will be reloaded from")} .env.
                    </p>
                  </div>
                </div>

                {/* Test Results */}
                {testResults && (
                  <div className="grid grid-cols-3 gap-3">
                    {Object.entries(testResults).map(([key, result]) => (
                      <div
                        key={key}
                        className={`p-4 rounded-xl border ${
                          result.status === "configured"
                            ? "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800"
                            : result.status === "not_configured"
                              ? "bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800"
                              : "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800"
                        }`}
                      >
                        <div className="flex items-center gap-2 mb-2">
                          {getStatusIcon(result.status)}
                          <span className="text-sm font-semibold uppercase text-slate-700 dark:text-slate-200">
                            {key}
                          </span>
                        </div>
                        <p className="text-xs text-slate-600 dark:text-slate-400 truncate font-mono">
                          {result.model || result.error || "Not configured"}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </section>

            {/* Environment Variables by Category */}
            {envConfig.categories.map((category) => {
              const categoryVars = envConfig.variables.filter(
                (v) => v.category === category.id,
              );
              if (categoryVars.length === 0) return null;

              return (
                <section
                  key={category.id}
                  className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden transition-colors duration-200"
                >
                  <div className="p-4 border-b border-slate-100 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50 flex items-center gap-2">
                    <div className="text-blue-500 dark:text-blue-400">
                      {getCategoryIcon(category.icon)}
                    </div>
                    <div>
                      <h2 className="font-semibold text-slate-900 dark:text-slate-100">
                        {category.name}
                      </h2>
                      <p className="text-xs text-slate-500 dark:text-slate-400">
                        {category.description}
                      </p>
                    </div>
                  </div>

                  <div className="p-6 space-y-5">
                    {categoryVars.map((envVar) => (
                      <div key={envVar.key} className="space-y-2">
                        <div className="flex items-center justify-between">
                          <label className="text-sm font-medium text-slate-700 dark:text-slate-300 flex items-center gap-2">
                            <code className="bg-slate-100 dark:bg-slate-700 px-2 py-0.5 rounded text-slate-800 dark:text-slate-200 text-xs">
                              {envVar.key}
                            </code>
                            {envVar.required && (
                              <span className="text-red-500 text-[10px] font-semibold">
                                REQUIRED
                              </span>
                            )}
                            {envVar.is_set && (
                              <CheckCircle className="w-3.5 h-3.5 text-green-500" />
                            )}
                          </label>
                          {envVar.sensitive && (
                            <button
                              onClick={() =>
                                toggleSensitiveVisibility(envVar.key)
                              }
                              className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 p-1"
                            >
                              {showSensitive[envVar.key] ? (
                                <EyeOff className="w-4 h-4" />
                              ) : (
                                <Eye className="w-4 h-4" />
                              )}
                            </button>
                          )}
                        </div>
                        <p className="text-xs text-slate-500 dark:text-slate-400">
                          {envVar.description}
                        </p>
                        <input
                          type={
                            envVar.sensitive && !showSensitive[envVar.key]
                              ? "password"
                              : "text"
                          }
                          value={editedEnvVars[envVar.key] || ""}
                          onChange={(e) =>
                            handleEnvVarChange(envVar.key, e.target.value)
                          }
                          placeholder={envVar.default || `Enter ${envVar.key}`}
                          className="w-full p-3 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-sm text-slate-900 dark:text-slate-100 font-mono placeholder:text-slate-300 dark:placeholder:text-slate-500 focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none"
                        />
                      </div>
                    ))}
                  </div>
                </section>
              );
            })}

            {/* Save Environment Variables */}
            <div className="pt-4 pb-8">
              {envError && (
                <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center gap-2 text-red-700 dark:text-red-400 text-sm">
                  <AlertCircle className="w-4 h-4" />
                  <span>{envError}</span>
                </div>
              )}
              <button
                onClick={handleEnvSave}
                disabled={envSaving}
                className={`w-full py-4 rounded-xl font-bold text-lg flex items-center justify-center gap-3 transition-all ${
                  envSaving
                    ? "bg-slate-100 dark:bg-slate-700 text-slate-400 dark:text-slate-500"
                    : envSaveSuccess
                      ? "bg-green-500 text-white shadow-xl shadow-green-500/30 scale-[1.02]"
                      : "bg-gradient-to-r from-amber-500 to-orange-500 text-white hover:shadow-xl hover:shadow-orange-500/30 hover:-translate-y-1"
                }`}
              >
                {envSaving ? (
                  <Loader2 className="w-6 h-6 animate-spin" />
                ) : envSaveSuccess ? (
                  <Check className="w-6 h-6" />
                ) : (
                  <Key className="w-6 h-6" />
                )}
                {envSaveSuccess
                  ? t("Environment Updated!")
                  : t("Apply Environment Changes")}
              </button>
            </div>
          </div>
        )}

        {/* LLM Providers Tab */}
        {activeTab === "llm_providers" && (
          <div className="space-y-6">
            {/* Header & Add Button */}
            <div className="flex justify-between items-center bg-white dark:bg-slate-800 p-6 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700">
              <div>
                <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                  LLM Service Providers
                </h2>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  Configure and manage multiple LLM backends.
                </p>
              </div>
              <button
                onClick={() => {
                  const defaultPreset = PROVIDER_PRESETS[0];
                  setEditingProvider({
                    name: "",
                    binding: defaultPreset.binding,
                    base_url: defaultPreset.base_url || "",
                    api_key: "",
                    model: defaultPreset.default_model,
                    is_active: false,
                  });
                  setOriginalProviderName(null);
                  setSelectedPresetId(defaultPreset.id);
                  setFetchedModels([]);
                  setShowProviderForm(true);
                  setTestProviderResult(null);
                }}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg flex items-center gap-2 text-sm font-medium transition-colors"
              >
                <SettingsIcon className="w-4 h-4" />
                Add Provider
              </button>
            </div>

            {/* Provider List */}
            {loadingProviders ? (
              <div className="flex justify-center p-8">
                <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
              </div>
            ) : providers.length === 0 ? (
              <div className="text-center p-12 bg-slate-50 dark:bg-slate-800/50 rounded-2xl border border-dashed border-slate-300 dark:border-slate-700">
                <Brain className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
                <p className="text-slate-500 dark:text-slate-400">
                  No providers configured yet.
                </p>
              </div>
            ) : (
              <div className="grid gap-4">
                {providers.map((provider) => (
                  <div
                    key={provider.name}
                    className={`bg-white dark:bg-slate-800 p-6 rounded-2xl shadow-sm border transition-all ${provider.is_active ? "border-blue-500 ring-1 ring-blue-500/20" : "border-slate-200 dark:border-slate-700"}`}
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex items-start gap-4">
                        <div
                          className={`p-3 rounded-xl ${provider.is_active ? "bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400" : "bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400"}`}
                        >
                          <Server className="w-6 h-6" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <h3 className="font-semibold text-slate-900 dark:text-slate-100 text-lg">
                              {provider.name}
                            </h3>
                            {provider.is_active && (
                              <span className="px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-xs rounded-full font-medium">
                                Active
                              </span>
                            )}
                          </div>
                          <div className="mt-1 space-y-1">
                            <div className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
                              <span className="text-xs bg-slate-100 dark:bg-slate-700 px-1.5 py-0.5 rounded border border-slate-200 dark:border-slate-600 uppercase tracking-wider font-semibold">
                                {provider.binding}
                              </span>
                              <span>{provider.model}</span>
                            </div>
                            <div className="text-xs text-slate-400 font-mono">
                              {provider.base_url}
                            </div>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {!provider.is_active && (
                          <button
                            onClick={() =>
                              handleActivateProvider(provider.name)
                            }
                            className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors"
                            title="Set as Active"
                          >
                            <CheckCircle className="w-5 h-5" />
                          </button>
                        )}
                        <button
                          onClick={() => handleTestProvider(provider)}
                          className="p-2 text-slate-400 hover:text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 rounded-lg transition-colors"
                          title="Test Connection"
                        >
                          <RefreshCw className="w-5 h-5" />
                        </button>
                        <button
                          onClick={() => {
                            setEditingProvider({ ...provider });
                            setOriginalProviderName(provider.name);
                            // Try to infer preset from URL
                            const preset =
                              PROVIDER_PRESETS.find(
                                (p) =>
                                  p.base_url &&
                                  provider.base_url.includes(p.base_url),
                              ) ||
                              PROVIDER_PRESETS.find((p) => p.id === "custom");
                            if (preset) setSelectedPresetId(preset.id);
                            setFetchedModels([]);
                            setShowProviderForm(true);
                            setTestProviderResult(null);
                          }}
                          className="p-2 text-slate-400 hover:text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-900/20 rounded-lg transition-colors"
                          title="Edit"
                        >
                          <Sliders className="w-5 h-5" />
                        </button>
                        <button
                          onClick={() => handleDeleteProvider(provider.name)}
                          className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                          title="Delete"
                        >
                          <XCircle className="w-5 h-5" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Edit/Add Form Modal */}
            {showProviderForm && editingProvider && (
              <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-xl w-full max-w-lg overflow-hidden flex flex-col max-h-[90vh]">
                  <div className="p-6 border-b border-slate-100 dark:border-slate-700 flex justify-between items-center">
                    <h3 className="font-semibold text-lg text-slate-900 dark:text-slate-100">
                      {editingProvider.name ? "Edit Provider" : "Add Provider"}
                    </h3>
                    <button
                      onClick={() => setShowProviderForm(false)}
                      className="text-slate-400 hover:text-slate-600"
                    >
                      <XCircle className="w-6 h-6" />
                    </button>
                  </div>
                  <div className="p-6 overflow-y-auto space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                        Provider Service
                      </label>
                      <select
                        value={selectedPresetId}
                        onChange={(e) => {
                          const newId = e.target.value;
                          setSelectedPresetId(newId);
                          const preset = PROVIDER_PRESETS.find(
                            (p) => p.id === newId,
                          );
                          if (preset && editingProvider) {
                            setEditingProvider({
                              ...editingProvider,
                              binding: preset.binding,
                              base_url:
                                preset.base_url || editingProvider.base_url,
                              model:
                                preset.default_model || editingProvider.model,
                              // don't clear api key if switching between compatible presets? maybe better to clear or keep? keeping for now.
                            });
                            setCustomModelInput(preset.models.length === 0);
                            setFetchedModels([]);
                          }
                        }}
                        className="w-full p-2.5 bg-slate-50 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg text-slate-900 dark:text-slate-100 font-medium"
                      >
                        {PROVIDER_PRESETS.map((preset) => (
                          <option key={preset.id} value={preset.id}>
                            {preset.name}
                          </option>
                        ))}
                      </select>
                      {PROVIDER_PRESETS.find((p) => p.id === selectedPresetId)
                        ?.help_text && (
                        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                          {
                            PROVIDER_PRESETS.find(
                              (p) => p.id === selectedPresetId,
                            )?.help_text
                          }
                        </p>
                      )}
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                          Name
                        </label>
                        <input
                          type="text"
                          value={editingProvider.name}
                          onChange={(e) =>
                            setEditingProvider((prev) =>
                              prev ? { ...prev, name: e.target.value } : null,
                            )
                          }
                          disabled={
                            !!providers.find(
                              (p) =>
                                p.name === editingProvider.name &&
                                p.name !== "",
                            )
                          }
                          placeholder="My Provider"
                          className="w-full p-2.5 bg-slate-50 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg"
                        />
                      </div>
                      <div>
                        {/* Hidden binding but kept for data structure */}
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                          Binding
                        </label>
                        <input
                          type="text"
                          value={editingProvider.binding}
                          disabled
                          className="w-full p-2.5 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-500"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                        Base URL
                      </label>
                      <input
                        type="text"
                        value={editingProvider.base_url}
                        onChange={(e) =>
                          setEditingProvider((prev) =>
                            prev ? { ...prev, base_url: e.target.value } : null,
                          )
                        }
                        placeholder="https://api.openai.com/v1"
                        className="w-full p-2.5 bg-slate-50 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg font-mono text-sm"
                      />
                    </div>

                    {PROVIDER_PRESETS.find((p) => p.id === selectedPresetId)
                      ?.requires_key !== false && (
                      <div>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                          API Key
                        </label>
                        <div className="relative">
                          <input
                            type="password"
                            value={editingProvider.api_key}
                            onChange={(e) =>
                              setEditingProvider((prev) =>
                                prev
                                  ? { ...prev, api_key: e.target.value }
                                  : null,
                              )
                            }
                            placeholder="sk-..."
                            className="w-full p-2.5 bg-slate-50 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg font-mono text-sm"
                          />
                        </div>
                      </div>
                    )}

                    <div>
                      <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1 flex justify-between">
                        <span>Model</span>
                        {PROVIDER_PRESETS.find((p) => p.id === selectedPresetId)
                          ?.models.length! > 0 && (
                          <button
                            onClick={() =>
                              setCustomModelInput(!customModelInput)
                            }
                            className="text-xs text-blue-600 hover:underline"
                          >
                            {customModelInput
                              ? "Select from list"
                              : "Enter custom"}
                          </button>
                        )}
                      </label>
                      <div className="flex gap-2">
                        {!customModelInput &&
                        (fetchedModels.length > 0 ||
                          PROVIDER_PRESETS.find(
                            (p) => p.id === selectedPresetId,
                          )?.models.length! > 0) ? (
                          <div className="relative flex-1">
                            <select
                              value={editingProvider.model}
                              onChange={(e) =>
                                setEditingProvider((prev) =>
                                  prev
                                    ? { ...prev, model: e.target.value }
                                    : null,
                                )
                              }
                              className="w-full p-2.5 bg-slate-50 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg appearance-none"
                            >
                              {fetchedModels.length > 0 ? (
                                <>
                                  <option value="" disabled>
                                    Select a fetched model
                                  </option>
                                  {fetchedModels.map((m) => (
                                    <option key={m} value={m}>
                                      {m}
                                    </option>
                                  ))}
                                </>
                              ) : (
                                PROVIDER_PRESETS.find(
                                  (p) => p.id === selectedPresetId,
                                )?.models.map((m) => (
                                  <option key={m} value={m}>
                                    {m}
                                  </option>
                                ))
                              )}
                            </select>
                            <div className="absolute inset-y-0 right-0 flex items-center px-2 pointer-events-none text-slate-500">
                              <svg
                                className="w-4 h-4"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                              >
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  strokeWidth="2"
                                  d="M19 9l-7 7-7-7"
                                ></path>
                              </svg>
                            </div>
                          </div>
                        ) : (
                          <input
                            type="text"
                            value={editingProvider.model}
                            onChange={(e) =>
                              setEditingProvider((prev) =>
                                prev
                                  ? { ...prev, model: e.target.value }
                                  : null,
                              )
                            }
                            placeholder="gpt-4o-mini"
                            className="flex-1 p-2.5 bg-slate-50 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg"
                          />
                        )}
                        <button
                          type="button"
                          onClick={fetchModels}
                          disabled={fetchingModels || !editingProvider.base_url}
                          className="p-2.5 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors disabled:opacity-50"
                          title="Refresh Models from API"
                        >
                          {fetchingModels ? (
                            <Loader2 className="w-5 h-5 animate-spin" />
                          ) : (
                            <RotateCcw className="w-5 h-5" />
                          )}
                        </button>
                      </div>
                    </div>
                    <div className="pt-2">
                      <button
                        type="button"
                        onClick={() => handleTestProvider(editingProvider)}
                        disabled={testingProvider}
                        className="text-sm text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1"
                      >
                        {testingProvider ? (
                          <Loader2 className="w-3 h-3 animate-spin" />
                        ) : (
                          <RefreshCw className="w-3 h-3" />
                        )}
                        Test Connection
                      </button>
                      {testProviderResult && (
                        <div
                          className={`mt-2 p-2 text-xs rounded ${testProviderResult.success ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300" : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300"}`}
                        >
                          {testProviderResult.success
                            ? "Connection Successful!"
                            : `Failed: ${testProviderResult.message}`}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="p-6 border-t border-slate-100 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50 flex flex-col gap-3">
                    {providerError && (
                      <div className="p-3 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-sm">
                        {providerError}
                      </div>
                    )}
                    <div className="flex justify-end gap-3">
                      <button
                        onClick={() => setShowProviderForm(false)}
                        className="px-4 py-2 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg font-medium"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={() => handleProviderSave(editingProvider)}
                        disabled={savingProvider}
                        className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium shadow-sm disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                      >
                        {savingProvider && (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        )}
                        {savingProvider ? "Saving..." : "Save Provider"}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
