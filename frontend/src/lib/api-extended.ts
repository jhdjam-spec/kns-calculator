/**
 * Расширенный API-клиент для Phase 22-32.
 * Покрывает: fire_water, water_supply, electrical (через project),
 * climate, structural, los, encyclopedia, project (главный flow).
 *
 * Базовый префикс — `/api/backend/*` (см. lib/api.ts).
 */

const API_PREFIX =
  process.env.NEXT_PUBLIC_API_BASE
    ? `${process.env.NEXT_PUBLIC_API_BASE}`
    : "/api/backend";

async function postJSON<T>(endpoint: string, payload: unknown): Promise<T> {
  const res = await fetch(`${API_PREFIX}${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`Backend error ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

async function getJSON<T>(endpoint: string): Promise<T> {
  const res = await fetch(`${API_PREFIX}${endpoint}`);
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`Backend error ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

// ─── Project (главный flow) ─────────────────────────────────────────

export interface ProjectPresetMeta {
  key: string;
  title: string;
  description: string;
  default_subsystems: Record<string, boolean>;
}

export interface ProjectInput {
  project_name: string;
  project_code?: string;
  customer?: string;
  preset: string;
  region_city: string;
  population: number;
  floors: number;
  volume_m3: number;
  area_m2?: number;
  subsystems?: Record<string, boolean>;
  has_groundwater?: boolean;
  soil_type?: string;
  is_atex_zone?: boolean;
}

export interface SubsystemResult {
  name: string;
  status: "ok" | "warning" | "skipped" | "error";
  summary: string;
  data: Record<string, unknown>;
  references?: Array<Record<string, string>>;
  warnings?: string[];
}

export interface ProjectResult {
  project_name: string;
  project_code: string;
  preset: string;
  kns: SubsystemResult | null;
  vns_potable: SubsystemResult | null;
  vns_fire: SubsystemResult | null;
  storm: SubsystemResult | null;
  los: SubsystemResult | null;
  electrical: SubsystemResult | null;
  climate: SubsystemResult | null;
  structural: SubsystemResult | null;
  total_estimated_cost_rub: number;
  total_warnings: number;
  bom: Array<Record<string, unknown>>;
  references_consolidated: Array<Record<string, string>>;
  notes: string[];
}

export const projectApi = {
  listPresets: () => getJSON<{ presets: ProjectPresetMeta[] }>("/project/presets"),
  calculate: (input: ProjectInput) =>
    postJSON<ProjectResult>("/project/calculate", input),
};

// ─── Encyclopedia ───────────────────────────────────────────────────

export interface RegulationFull {
  code: string;
  name: string;
}

export interface EncyclopediaTopicMeta {
  key: string;
  title: string;
  short_description: string;
  api_module: string;
  sections_count: number;
  regulations_full?: RegulationFull[];
}

export interface EncyclopediaExample {
  id: string;
  title: string;
  topic: string;
  description: string;
  api_endpoint: string;
  payload: Record<string, unknown>;
  expected_outcome: string;
}

export interface EncyclopediaTopic {
  key: string;
  title: string;
  short_description: string;
  api_module: string;
  content_markdown: string;
  examples: EncyclopediaExample[];
  regulations_full?: RegulationFull[];
}

export interface EncyclopediaSection {
  topic: string;
  section_anchor: string;
  section_title: string;
  content_markdown: string;
}

export const encyclopediaApi = {
  listTopics: () =>
    getJSON<{ topics: EncyclopediaTopicMeta[] }>("/encyclopedia/topics"),
  getTopic: (key: string) =>
    getJSON<EncyclopediaTopic>(`/encyclopedia/topic/${key}`),
  getSection: (topic: string, anchor: string) =>
    getJSON<EncyclopediaSection>(
      `/encyclopedia/section/${topic}?anchor=${encodeURIComponent(anchor)}`,
    ),
  listExamples: () =>
    getJSON<{ examples: EncyclopediaExample[] }>("/encyclopedia/examples"),
};

// ─── Fire water (Phase 22) ──────────────────────────────────────────

export interface FireScenarioInput {
  occupancy: string;
  building_class?: string;
  volume_m3: number;
  height_m?: number;
  floors: number;
  population?: number;
  fire_duration_h?: number;
  has_internal_system?: boolean;
  water_source?: string;
  sprinkler_flow_lps?: number;
}

export const fireWaterApi = {
  calculate: (input: FireScenarioInput) =>
    postJSON<Record<string, unknown>>("/fire-water/calc", input),
};

// ─── Water supply (Phase 23) ────────────────────────────────────────

export interface WaterScenarioInput {
  building_type: string;
  population?: number;
  rooms?: number;
  beds?: number;
  visits_per_day?: number;
  area_m2?: number;
  floors?: number;
  has_hot_water?: boolean;
  has_irrigation?: boolean;
  irrigation_area_m2?: number;
  water_source?: string;
}

export const waterSupplyApi = {
  calculate: (input: WaterScenarioInput) =>
    postJSON<Record<string, unknown>>("/water/demand", input),
  listNorms: () => getJSON<Record<string, unknown>>("/water/norms"),
};

// ─── Climate (Phase 25) ─────────────────────────────────────────────

export interface BurialDepthInput {
  region_city: string;
  soil_type?: string;
  pipe_dn_mm?: number;
  has_groundwater?: boolean;
}

// Phase 28 Climate Simulator
export interface ClimateCity {
  city: string;
  region: string;
  climate_zone: string;
  altitude_m: number;
  frost_depth_mm: number;
  t_min_5pct_c: number;
  lat?: number | null;
  lon?: number | null;
}

export interface ClimateCardResponse {
  climate: Record<string, unknown> & ClimateCity;
  recommendations: Array<{
    code: string;
    severity: string;
    title: string;
    text: string;
  }>;
}

export const climateApi = {
  burialDepth: (input: BurialDepthInput) =>
    postJSON<Record<string, unknown>>("/climate/burial-depth", input),
  loads: (input: Record<string, unknown>) =>
    postJSON<Record<string, unknown>>("/climate/loads", input),
  cities: () =>
    getJSON<{ cities: ClimateCity[]; count: number }>("/climate/cities"),
  forCity: (city: string) =>
    getJSON<ClimateCardResponse>(`/climate/${encodeURIComponent(city)}`),
};

// ─── TCO (Phase 31) ─────────────────────────────────────────────────

export interface TCORequestBody {
  selection?: unknown;
  selection_request?: unknown;
  segment?: "budget" | "mid" | "premium";
  horizon_years?: number;
  tariff_rub_per_kwh?: number;
  install_pct?: number;
  transport_pct?: number;
}

export interface TCOSankeyNode {
  id: string;
  name: string;
  category: string;
  value: number;
}

export interface TCOSankeyLink {
  source: string;
  target: string;
  value: number;
}

export interface TCOResponse {
  horizon_years: number;
  operating_mode: string;
  hours_per_year: number;
  tariff_rub_per_kwh: number;
  capex: Record<string, number>;
  opex_annual: Record<string, number>;
  opex_horizon_rub: number;
  tco_horizon_rub: number;
  flow_horizon_m3: number;
  cost_per_m3_rub: number;
  sankey_nodes: TCOSankeyNode[];
  sankey_links: TCOSankeyLink[];
  pump_meta?: Record<string, unknown>;
}

export const tcoApi = {
  calculate: (body: TCORequestBody) =>
    postJSON<TCOResponse>("/tco/calculate", body),
};

// ─── Failure modes (Phase 31) ───────────────────────────────────────

export interface FailureMode {
  id: string;
  name: string;
  category: string;
  severity: "low" | "medium" | "high" | "critical";
  symptoms: string[];
  causes: string[];
  prevention: string[];
  fix_cost_rub: [number, number];
  downtime_hours: [number, number];
  lifecycle_impact: string;
  trigger_in_calculator?: string | null;
  sp_norm?: string;
  image_alt?: string;
}

export interface FailureModesListResponse {
  count: number;
  categories: string[];
  filter: { trigger: string | null; category: string | null; severity: string | null };
  modes: FailureMode[];
}

export const failureModesApi = {
  list: (params?: { trigger?: string; category?: string; severity?: string }) => {
    const qs = new URLSearchParams();
    if (params?.trigger) qs.set("trigger", params.trigger);
    if (params?.category) qs.set("category", params.category);
    if (params?.severity) qs.set("severity", params.severity);
    const suffix = qs.toString();
    return getJSON<FailureModesListResponse>(
      `/failure-modes${suffix ? "?" + suffix : ""}`,
    );
  },
  get: (id: string) => getJSON<FailureMode>(`/failure-modes/${encodeURIComponent(id)}`),
};

// ─── Structural (Phase 26) ──────────────────────────────────────────

export interface StructuralInput {
  diameter_m: number;
  height_m: number;
  material: string;
  wall_thickness_mm?: number;
  groundwater_depth_m?: number;
  burial_depth_m: number;
  soil_type?: string;
  fill_level_pct?: number;
}

export const structuralApi = {
  ballast: (input: StructuralInput) =>
    postJSON<Record<string, unknown>>("/structural/ballast", input),
  wallThickness: (input: StructuralInput) =>
    postJSON<Record<string, unknown>>("/structural/wall-thickness", input),
  ladder: (input: { height_m: number; pit_diameter_m: number; is_corrosive_environment?: boolean }) =>
    postJSON<Record<string, unknown>>("/structural/ladder", input),
};

// ─── LOS (Phase 27) ─────────────────────────────────────────────────

export interface LOSInput {
  source_type: string;
  flow_m3_per_day: number;
  discharge_category: string;
  population_equivalent?: number;
}

export const losApi = {
  select: (input: LOSInput) =>
    postJSON<Record<string, unknown>>("/los/select", input),
  catalog: () => getJSON<Record<string, unknown>>("/los/catalog"),
};

// ─── Reports (Phase 28) — PDF расчётной записки ─────────────────────

export interface CalculationReportInput {
  project_name: string;
  project_code?: string;
  customer?: string;
  object_address?: string;
  inputs_summary?: Record<string, unknown>;
  hydraulics?: Record<string, unknown>;
  electrical?: Record<string, unknown>;
  fire_water?: Record<string, unknown>;
  water_supply?: Record<string, unknown>;
  climate?: Record<string, unknown>;
  structural?: Record<string, unknown>;
  los?: Record<string, unknown>;
  bom?: Array<Record<string, unknown>>;
  references?: Array<Record<string, string>>;
}

/** Скачивание PDF файла напрямую (без JSON parsing). */
export async function downloadCalculationPdf(
  input: CalculationReportInput,
): Promise<Blob> {
  const res = await fetch(`${API_PREFIX}/reports/calculation-pdf`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`Backend error ${res.status}: ${text}`);
  }
  return res.blob();
}

// ─── BOM (Phase 30) — экспорт в CSV ─────────────────────────────────

export interface BOMItem {
  section: string;
  position_no?: number;
  name: string;
  article?: string;
  manufacturer?: string;
  quantity?: number;
  units?: string;
  price_rub_2026?: number;
  lead_time_days?: number;
  supplier?: string;
  source_url?: string;
  note?: string;
}

export interface BOMSpecification {
  project_code?: string;
  project_name?: string;
  items: BOMItem[];
}

export async function downloadBomCsv(spec: BOMSpecification): Promise<Blob> {
  const res = await fetch(`${API_PREFIX}/bom/export-csv`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(spec),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`Backend error ${res.status}: ${text}`);
  }
  return res.blob();
}

// ─── Regulations (Phase 22) ─────────────────────────────────────────

export interface Regulation {
  code: string;
  title: string;
  edition: string;
  in_force_from: string;
  superseded_by: string | null;
  url_official: string;
  scope: string;
  category: string;
}

export const regulationsApi = {
  list: (category?: string) =>
    getJSON<{ count: number; regulations: Regulation[] }>(
      `/regulations${category ? `?category=${category}` : ""}`,
    ),
  get: (code: string) => getJSON<Regulation>(`/regulations/${code}`),
};
